from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi import Path as PathParam
import redis.exceptions

from crud import (
    get_post_by_id,
    get_game_by_id,
    create_comment,
    update_instance
)
from config import Config
from mail import send
from db import mail_queue

router = APIRouter(prefix="/comments")
templates = Jinja2Templates(directory=Config.TEMPLATES_ROOT)


@router.post("/{type}/{id}", name="upload_comment")
async def upload_comment(request: Request, type: Annotated[str, PathParam()], id: Annotated[int, PathParam()]):
    user = request.state.user
    if not user:
        return RedirectResponse(request.url_for("login"), status.HTTP_301_MOVED_PERMANENTLY)

    if not type in ("game", "post"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    object = None
    if type == "game":
        object = get_game_by_id(id)
    elif type == "post":
        object = get_post_by_id(id)

    if not object:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    form_data = await request.form()
    content = form_data.get("content")
    if not content or content == "":
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    create_comment(
        content=content,
        user_id=user.id,
        game_id=(id if type == "game" else None),
        post_id=(id if type == "post" else None)
    )

    object.num_comments = object.num_comments + 1
    update_instance(object)

    if user.id != object.user.id and object.user.email_notifications_enabled:
        subject = "Новый комментарий"
        if type == "post":
            comments_url = request.url_for("post", post_id=object.id)
        else:
            comments_url = request.url_for("game", game_id=object.id)
        comments_url = str(comments_url) + "#comments"

        body = f"""
        <p>Здравствуйте, <strong>{object.user.username}!</strong></p>
        <p>Под {"вашей игрой" if type == "game" else "вашей статьей"} оставлен новый комментарий:</p>
        <p><a href="{comments_url}">{object.title}</a></p>"""
        template = templates.get_template("mail/mail_base.html")
        mail = template.render({
            'title': subject,
            'body': body
        })
        try:
            mail_queue.enqueue(send, object.user.email, subject, mail)
        except redis.exceptions.ConnectionError:
            pass

    if type == "game":
        return RedirectResponse(request.url_for("game", game_id=id), status.HTTP_301_MOVED_PERMANENTLY)
    else:
        return RedirectResponse(request.url_for("post", post_id=id), status.HTTP_301_MOVED_PERMANENTLY)
    
