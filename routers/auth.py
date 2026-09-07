from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
import jwt
import redis.exceptions

from crud import get_user_by_username, get_user_by_email, create_user, update_instance
from forms import LoginForm, RegisterForm, GenResetPasswordForm, ResetPasswordForm

from config import Config
from mail import send
from db import mail_queue, timezone
from models import User


AUTH_SECRET_KEY = Config.JWT_AUTH_SECRET
AUTH_TOKEN_EXPIRES = Config.JWT_AUTH_EXPIRES
RESET_SECRET_KEY = Config.JWT_RESET_SECRET
RESET_TOKEN_EXPIRES = Config.JWT_RESET_EXPIRES
ALGORITHM = Config.JWT_ALGORITHM


router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory=Config.TEMPLATES_ROOT)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
hash_utility = PasswordHash.recommended()


def verify_user(username, password) -> Optional[User]:
    user = get_user_by_username(username)
    if user and hash_utility.verify(password, user.password_hash):
        return user

def get_token_exp_time(exp_seconds: int) -> float:
    return (datetime.now(timezone.utc) + timedelta(seconds=exp_seconds)).timestamp()

def generate_jwt(username, key=AUTH_SECRET_KEY, expire=AUTH_TOKEN_EXPIRES) -> str:
    return jwt.encode({
        "sub": username,
        "exp": get_token_exp_time(expire),
    }, key=key, algorithm=ALGORITHM)

def decode_jwt(token, key=AUTH_SECRET_KEY) -> tuple[Optional[str], datetime]:
    data = jwt.decode(token, key, algorithms=[ALGORITHM])
    username = data.get("sub")
    exp = datetime.fromtimestamp(data.get("exp", 0))
    return username, exp

def finalize_auth(username: str) -> RedirectResponse:
    jwt = generate_jwt(username)
    resp = RedirectResponse(url="/", status_code=status.HTTP_301_MOVED_PERMANENTLY)
    resp.set_cookie("token", jwt, max_age=AUTH_TOKEN_EXPIRES, httponly=True, samesite='strict', secure=True)
    return resp

@router.get("/login", name='login')
async def get_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={
        "form": LoginForm()
    })

@router.post("/login")
async def post_login(request: Request):
    form = LoginForm(await request.form())
    template_name = "login.html"
    context = {"form": form}

    if not form.validate():
        return templates.TemplateResponse(request=request, name=template_name, context=context)

    user = verify_user(form.username.data, form.password.data)
    if not user:
        context.update({"errors": ["Неверное имя пользователя или пароль"]})
        return templates.TemplateResponse(request=request, name=template_name, context=context)

    return finalize_auth(user.username)


@router.get("/register", name='register')
async def get_register(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={
        "form": RegisterForm()
    })


@router.post("/register")
async def post_register(request: Request):
    form = RegisterForm(await request.form())
    template_name = "register.html"
    context = {"form": form}
    if not form.validate():
        return templates.TemplateResponse(request=request, name=template_name, context=context)

    user = get_user_by_username(form.username.data)
    if user:
        context.update({"errors": ["Такое имя пользователя уже занято"]})
        return templates.TemplateResponse(request=request, name=template_name, context=context)
    
    user = get_user_by_email(form.email.data)
    if user:
        context.update({"errors": ["Такая почта уже используется"]})
        return templates.TemplateResponse(request=request, name=template_name, context=context)

    user = create_user(form.username.data, form.email.data, hash_utility.hash(form.password.data))
    return finalize_auth(user.username)


@router.get("/logout", name="logout")
async def get_logout():
    resp = RedirectResponse(url="/", status_code=status.HTTP_301_MOVED_PERMANENTLY)
    resp.delete_cookie("token")
    return resp


@router.get("/gen_reset_password", name="gen_reset_password")
async def get_gen_reset_password(request: Request):
    return templates.TemplateResponse(request=request, name="gen_reset_password.html", context={
        "form": GenResetPasswordForm()
    })

@router.post("/gen_reset_password")
async def gen_reset_password(request: Request):
    form = GenResetPasswordForm(await request.form())
    template_name = "gen_reset_password.html"
    context = {"form": form}

    if not form.validate():
        return templates.TemplateResponse(request=request, name=template_name, context=context)

    user_with_email = get_user_by_email(form.email.data)
    if (not user_with_email) or (user_with_email.username != form.username.data):
        context.update({"errors": ["Пользователь не найден"]})
        return templates.TemplateResponse(request=request, name=template_name, context=context)

    token = generate_jwt(form.username.data, RESET_SECRET_KEY, RESET_TOKEN_EXPIRES)
    reset_link = request.url_for('reset_password', token=token)

    subject = f"Сброс пароля"
    template = templates.get_template("mail/mail_reset_password.html")
    mail = template.render({
        'request': request,
        'reset_link': reset_link,
    })

    try:
        mail_queue.enqueue(send, form.email.data, subject, mail)
    except redis.exceptions.ConnectionError:
        context.update({"errors": ["В данный момент почта недоступна"]})
        return templates.TemplateResponse(request=request, name="gen_reset_password.html", context=context)

    context.update({"email_sended": True})
    return templates.TemplateResponse(request=request, name="gen_reset_password.html", context=context)


async def reset_token_to_user(token):
    try:
        username, exp = decode_jwt(token, key=RESET_SECRET_KEY)
    except (jwt.DecodeError, jwt.ExpiredSignatureError):
        return None
    
    if exp.timestamp() < datetime.now(timezone.utc).timestamp():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return user


@router.get("/reset_password/{token}", name="reset_password")
async def get_reset_password(request: Request, token: str):
    return templates.TemplateResponse(request=request, name="reset_password.html", context={
        "form": ResetPasswordForm(),
        "token": token,
    })


@router.post("/reset_password/{token}")
async def reset_password(request: Request, token: str):
    user = await reset_token_to_user(token)
    form = ResetPasswordForm(await request.form())

    if not form.validate():
        return templates.TemplateResponse(request=request, name="reset_password.html", context={
            "form": form,
            "token": token,
        })

    user.password_hash = hash_utility.hash(form.password.data)
    update_instance(user)
    return RedirectResponse(request.url_for("login"), status.HTTP_301_MOVED_PERMANENTLY)


async def get_user_middleware(request: Request, call_next):
    request.state.user = None
    token = request.cookies.get("token")
    if token is not None:
        try:
            username, exp = decode_jwt(token)
        except (jwt.DecodeError, jwt.ExpiredSignatureError):
            pass
        else:
            if exp.timestamp() > datetime.now(timezone.utc).timestamp():
                user = get_user_by_username(username)
                request.state.user = user
    response = await call_next(request)
    return response
