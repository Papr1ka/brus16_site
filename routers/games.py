from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Request, UploadFile
from fastapi import Path as PathParam
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import redis.exceptions

from forms import GameForm
from media import save_game, delete_game_media
from models import Game, Status
from crud import (
    update_instance,
    get_game_by_title,
    get_game_by_id,
    get_all_games,
    get_hitparade,
    toggle_vote,
    delete_instance,
    get_comments_for_game,
    delete_comments_for_game
)
from markdown import markdown
from config import Config
from mail import send
from db import mail_queue


router = APIRouter(prefix="/games")
templates = Jinja2Templates(directory=Config.TEMPLATES_ROOT)


@router.get("/upload_game", name="upload_game")
async def get_upload_game(request: Request):
    return templates.TemplateResponse(request=request, name="edit_game.html", context={
        "form": GameForm(),
        "create": True
    })

@router.get("/edit/{game_id}", name="edit_game")
async def get_edit_game(request: Request, game_id: Annotated[int, PathParam()]):
    game = get_game_by_id(game_id)
    if not game:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Игра с таким идентификатором не найдена")

    print(game)
    form = GameForm(obj=game)
    form.preview.data = game.preview_url
    
    return templates.TemplateResponse(request=request, name="edit_game.html", context={
        "form": form,
        "game": game
    })


async def update_game_handler(request: Request, preview: UploadFile | None = None, binary: UploadFile | None = None, game_id: int = None):
    user = request.state.user
    if not user:
        return templates.TemplateResponse(request=request, name="edit_game.html", context={
            "form": GameForm(),
        })

    form_data = await request.form()

    action = form_data.get("action")
    if action not in ("Загрузить игру", "Сохранить", "Удалить"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    messages = []
    game = None

    if action != "Загрузить игру":
        game = get_game_by_id(game_id)
        if not game:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Игра с таким идентификатором не найдена")
        if game.user.id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN)

        if action == "Удалить":
            await delete_game_media(str(game.id))
            delete_instance(game)
            messages.append(("success", "Игра удалена"))
            return templates.TemplateResponse(request=request, name="edit_game.html", context={
                "form": GameForm(),
                "messages": messages
            })

    # create or update
    form = GameForm(form_data)
    if not form.validate():
        return templates.TemplateResponse(request=request, name="edit_game.html", context={
            "form": form,
            "create": action == "Загрузить игру",
            "game": game if action == "Сохранить" else None
        })

    game_with_title = get_game_by_title(form.title.data)
    if (
        game_with_title and action == "Загрузить игру") or (
        game_with_title and game_with_title.id != game.id and action == "Сохранить"
    ):
        messages.append(("danger", "Игра с таким названием уже существует"))
        return templates.TemplateResponse(request=request, name="edit_game.html", context={
            "form": form,
            "messages": messages,
            "create": action == "Загрузить игру",
            "game": game if action == "Сохранить" else None
        })

    if action == "Загрузить игру":
        game = Game(**form.data)
        game.preview_url = "tmp"
        game.bin_path = "tmp"
        game.user_id = user.id
        if (user.verified):
            game.status = Status.published
            game.created_at = datetime.now()
        else:
            game.status = Status.moderation
    else:
        game = Game.sqlmodel_update(game, form.data)

    game = update_instance(game)
    preview_path, binary_path = await save_game(str(game.id), preview, binary)
    game.preview_url = preview_path
    game.bin_path = binary_path
    game = update_instance(game)

    return RedirectResponse(request.url_for("game", game_id=game.id), status.HTTP_301_MOVED_PERMANENTLY)


@router.post("/upload_game")
async def upload_game(request: Request, preview: UploadFile | None = None, binary: UploadFile | None = None):
    return await update_game_handler(request, preview=preview, binary=binary, game_id=None)


@router.post("/edit/{game_id}", name="edit_game_with_id")
async def edit_game(request: Request, game_id: Annotated[int, PathParam()], preview: UploadFile | None = None, binary: UploadFile | None = None):
    return await update_game_handler(request, preview=preview, binary=binary, game_id=game_id)


@router.get("/{game_id}", name="game")
async def get_game(request: Request, game_id: Annotated[int, PathParam()]):
    game = get_game_by_id(game_id)
    if not game:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Игра с таким идентификатором не найдена")

    content = markdown(game.description)

    comments = get_comments_for_game(game_id)

    return templates.TemplateResponse(request=request, name="game.html", context={
        "game": game,
        "content": content,
        "comments": comments
    })


@router.get("/vote/{game_id}", name="vote_game")
async def vote_game(request: Request, game_id: Annotated[int, PathParam()]):
    user = request.state.user

    game = get_game_by_id(game_id)
    if not game:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Игра с таким идентификатором не найдена")

    content = markdown(game.description)
    messages = []
    if not user:
        messages.append(("danger", "Чтобы продвинуть игру, необходимо авторизоваться"))
        return templates.TemplateResponse(request=request, name="game.html", context={
                "game": game,
                "content": content,
                "messages": messages
            })
    else:
        toggle_vote(user.id, game.id)

    return RedirectResponse(request.url_for("game", game_id=game.id), status_code=status.HTTP_308_PERMANENT_REDIRECT)


@router.get("/", name="games")
async def get_games(request: Request):
    games = get_all_games(status=Status.published)
    top_games = get_hitparade()
    return templates.TemplateResponse(request=request, name="games.html", context={
        "games": games,
        "top_games": top_games
    })

@router.get("/approve_game/{game_id}", name="approve_game")
async def approve_post(request: Request, game_id: int):
    user = request.state.user
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    game = get_game_by_id(game_id)
    if not game:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if game.status == Status.moderation:
        game.status = Status.published
        game.user.verified = True
        delete_comments_for_game(game.id)
        game.num_comments = 0
        update_instance(game)

        if game.user.email_notifications_enabled:
            subject = "Игра опубликована"
            body = f"""
            Здравствуйте, <strong>{game.user.username}!</strong>
            <p>Рады сообщить, что ваша игра
            <a href="{request.url_for("game", game_id=game.id)}">{game.title}</a>
            прошла модерацию и теперь опубликована на сайте.</p>
            <p>Также сообщаем, что в последующие разы вы сможете миновать этап модерации.</p>
            <p>Спасибо за вклад в сообщество и успехов!</p>"""
            template = templates.get_template("mail/mail_base.html")
            mail = template.render({
                'title': subject,
                'body': body
            })

            try:
                mail_queue.enqueue(send, game.user.email, subject, mail)
            except redis.exceptions.ConnectionError:
                pass

        return RedirectResponse(request.url_for("game", game_id=game.id), status.HTTP_301_MOVED_PERMANENTLY)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
