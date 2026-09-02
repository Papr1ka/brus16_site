from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Request, UploadFile
from fastapi import Path as PathParam
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import redis.exceptions

from crud import (
    get_draft_post_by_user_id,
    create_post,
    get_post_by_id,
    update_instance,
    delete_instance,
    get_all_posts,
    get_post_by_title,
    get_hitparade,
    get_comments_for_post,
    delete_comments_for_post
)
from models import Status, PostType, post_type_to_action, post_type_to_title
from forms import PostForm, validate_image_extension
from media import save_post_preview, save_post_image, clear_unused_images, delete_post_media
from markdown import markdown, collect_images
from config import Config

from mail import send
from db import mail_queue


router = APIRouter(prefix="/posts")
templates = Jinja2Templates(directory=Config.TEMPLATES_ROOT)

async def edit_post_handler(request: Request, post_id = None):
    user = request.state.user
    if not user:
        return templates.TemplateResponse(request=request, name="edit_post.html", context={
            "form": PostForm(),
        })
    
    messages = []

    if post_id is None:
        # create draft
        post = get_draft_post_by_user_id(user.id)
        if not post:
            post = create_post(request.state.user.id)
            messages.append(("success", "Создан новый черновик"))
    else:
        # fetch existing post
        post = get_post_by_id(post_id)
        if not post:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пост с таким идентификатором не найден")
        if post.user.id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN)

    return templates.TemplateResponse(request=request, name="edit_post.html", context={
        "form": PostForm(obj=post, data={"preview": post.preview_url}),
        "post_id": post.id,
        "messages": messages,
        "status": post.status.value
    })


@router.get("/edit/{post_id}", name="edit_post_with_id")
async def edit_post_by_id(request: Request, post_id: Annotated[int, PathParam()]):
    return await edit_post_handler(request, post_id=post_id)


@router.get("/edit", name="edit_post")
async def edit_draft(request: Request):
    return await edit_post_handler(request, post_id=None)


@router.post("/edit/{post_id}", name="edit_post_with_id")
async def edit_draft(request: Request, post_id: Annotated[int, PathParam()], preview: UploadFile | None = None):
    user = request.state.user
    if not user:
        return templates.TemplateResponse(request=request, name="edit_post.html", context={
            "form": PostForm(),
        })
 
    form_data = await request.form()
    action = form_data.get("action")
    if action not in ("Опубликовать", "Сохранить черновик", "Сохранить", "Удалить"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пост с таким идентификатором не найден")

    if post.user.id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    form = PostForm(form_data)
    if not form.validate():
        form.preview.data = post.preview_url
        return templates.TemplateResponse(request=request, name="edit_post.html", context={
            "form": form,
            "post_id": post.id,
            "status": post.status.value
        })
    
    messages = []
    post_with_title = get_post_by_title(form.title.data)
    if post_with_title and post_with_title.id != post.id:
        messages.append(("danger", "Пост с таким названием уже существует"))
        form.preview.data = post.preview_url
        return templates.TemplateResponse(request=request, name="edit_post.html", context={
            "form": form,
            "post_id": post.id,
            "status": post.status.value,
            "messages": messages
        })

    if action == "Удалить":
        await delete_post_media(str(post.id))
        delete_instance(post)
        post = create_post(user.id)
        messages.append(("success", "Пост удалён, создан черновик"))
        return templates.TemplateResponse(request=request, name="edit_post.html", context={
            "form": PostForm(obj=post, data={"preview": post.preview_url}),
            "post_id": post.id,
            "status": post.status.value,
            "messages": messages
        })

    if action == "Опубликовать":
        if user.verified:
            post.status = Status.published
            messages.append(("success", "Опубликовано"))
            post.created_at = datetime.now()
        else:
            post.status = Status.moderation
            messages.append(("success", "На модерации"))
    elif action == "Сохранить черновик":
        messages.append(("success", "Черновик сохранен"))
    else:
        messages.append(("success", "Сохранено"))

    post.type = form.type.data
    post.title = form.title.data
    post.summary = form.summary.data
    post.content = form.content.data

    if preview.filename != "":
        url = await save_post_preview(str(post.id), preview)
        post.preview_url = url

    update_instance(post)
    used_images = collect_images(post.content)
    await clear_unused_images(str(post.id), used_images)

    form.preview.data = post.preview_url
    return templates.TemplateResponse(request=request, name="edit_post.html", context={
        "form": form,
        "messages": messages,
        "post_id": post.id,
        "status": post.status.value
    })


@router.get("/{post_id}", name='post')
async def get_post(request: Request, post_id: Annotated[int, PathParam()]):
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пост с таким идентификатором не найден")

    content = markdown(post.content)

    comments = get_comments_for_post(post_id)

    return templates.TemplateResponse(request=request, name="post.html", context={
        "post": post,
        "content": content,
        "comments": comments
    })


@router.post("/upload_image/{post_id}", name='post_upload_image')
async def upload_image(
    request: Request,
    post_id: int,
    image: UploadFile
):
    user = request.state.user
    post = get_post_by_id(post_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    if not post:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="post not found")
    if post.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    if not validate_image_extension(image.filename):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    path = await save_post_image(str(post.id), image)
    return {
        "data": {
            "filePath": path
        }
    }

@router.get("/", name="posts")
async def get_posts(request: Request, type: PostType = None):
    posts = get_all_posts(status=Status.published, type=type)
    games = get_hitparade()
    return templates.TemplateResponse(request=request, name="posts.html", context={
        "posts": posts,
        "top_games": games,
        "title": post_type_to_title(type),
        "action": post_type_to_action(type)
    })

@router.get("/approve_post/{post_id}", name="approve_post")
async def approve_post(request: Request, post_id: int):
    user = request.state.user
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if post.status == Status.moderation:
        post.status = Status.published
        post.user.verified = True
        delete_comments_for_post(post.id)
        post.num_comments = 0
        update_instance(post)

        if post.user.email_notifications_enabled:
            subject = "Статья опубликована"
            body = f"""
            <p>Здравствуйте, <strong>{post.user.username}!</strong></p>
            <p>Рады сообщить, что ваша статья
            <a href="{request.url_for("post", post_id=post.id)}">{post.title}</a>
            прошла модерацию и теперь опубликована на сайте.</p>
            <p>Также сообщаем, что в последующие разы вы сможете миновать этап модерации.</p>
            <p>Спасибо за вклад в сообщество и успехов!</p>"""
            template = templates.get_template("mail/mail_base.html")
            mail = template.render({
                'title': subject,
                'body': body
            })
            try:
                mail_queue.enqueue(send, post.user.email, subject, mail)
            except redis.exceptions.ConnectionError:
                pass

        return RedirectResponse(request.url_for("post", post_id=post.id), status.HTTP_301_MOVED_PERMANENTLY)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
