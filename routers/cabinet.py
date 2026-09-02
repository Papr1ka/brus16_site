from fastapi import APIRouter, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from crud import (
    get_all_posts,
    get_all_games,
    get_all_posts_from_user,
    get_all_games_from_user,
    update_instance,
    get_user_by_email
)
from models import Status
from forms import ChangeEnableNotificationsForm
from config import Config

router = APIRouter(prefix="/cabinet")
templates = Jinja2Templates(directory=Config.TEMPLATES_ROOT)


@router.get("/", name="get_cabinet")
async def get_cabinet(request: Request):
    user = request.state.user
    if not user:
        return RedirectResponse(request.url_for("login"), status_code=status.HTTP_301_MOVED_PERMANENTLY)

    if user.is_admin:
        pending_posts = get_all_posts(Status.moderation)
        pending_games = get_all_games(Status.moderation)
    else:
        pending_posts = get_all_posts_from_user(user.id, status=Status.moderation)
        pending_games = get_all_games_from_user(user.id, status=Status.moderation)

    return templates.TemplateResponse(request=request, name="cabinet.html", context={
        "pending_posts": pending_posts,
        "pending_games": pending_games,
        "form": ChangeEnableNotificationsForm(data={"enable_notifications": user.email_notifications_enabled})
    })


@router.post("/change_enable_notifications", name="change_enable_notifications")
async def change_enable_notifications(request: Request):
    user = request.state.user
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    form_data = await request.form()
    form = ChangeEnableNotificationsForm(form_data)
    if not form.validate():
        return templates.TemplateResponse(request=request, name="cabinet.html", context={
            "form": form
        })
    user.email_notifications_enabled = form.enable_notifications.data
    update_instance(user)
    return RedirectResponse(request.url_for("get_cabinet"), status.HTTP_301_MOVED_PERMANENTLY)

