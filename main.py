from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models import Status
from routers.auth import router as auth_router
from routers.posts import router as posts_router
from routers.games import router as games_router
from routers.comments import router as comments_router
from routers.ide import router as ide_router
from routers.cabinet import router as cabinet_router

from routers.auth import get_user_middleware

from crud import get_all_posts, get_hitparade, get_recent_posts
from config import Config

if Config.DEBUG:
    app = FastAPI()
else:
    app = FastAPI(docs_url=None, redoc_url=None)

static_version = datetime.now().strftime("%Y%m%d%H%M%S")

app.mount(f"/static_{static_version}", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(games_router)
app.include_router(comments_router)
app.include_router(ide_router)
app.include_router(cabinet_router)

app.middleware("http")(get_user_middleware)


@app.get("/", name="home")
async def home(request: Request):
    posts = get_recent_posts()
    games = get_hitparade(3)
    pinned = get_all_posts(status=Status.published, pinned=True)

    return templates.TemplateResponse(request=request, name="home.html", context={
        "posts": posts,
        "games": games,
        "pinned": pinned
    })

@app.get("/terms_of_use", name="terms_of_use")
async def get_terms_of_use(request: Request):
    return templates.TemplateResponse(request=request, name="terms_of_use.html")

@app.get("/privacy_policy", name="privacy_policy")
async def get_privacy_policy(request: Request):
    return templates.TemplateResponse(request=request, name="privacy_policy.html")

