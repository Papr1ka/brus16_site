from typing import Annotated
import uuid
import json

from fastapi import APIRouter, Request, Body
from fastapi.templating import Jinja2Templates
import asyncio

from worker import compile_game
from config import Config
from db import compile_queue, redis_async

from redis.exceptions import ConnectionError

router = APIRouter(prefix="/ide")
templates = Jinja2Templates(directory=Config.TEMPLATES_ROOT)
GET_MESSAGE_TIMEOUT = Config.WAIT_FOR_COMPILATION_TIMEOUT


@router.get("/", name="get_ide")
async def get_ide(request: Request):
    return templates.TemplateResponse(request=request, name="ide.html", context={})

@router.post("/compile", name="compile")
async def compile(request: Request, code: Annotated[str, Body(embed=True)]):
    channel_id = str(uuid.uuid4())
    pubsub = redis_async.pubsub()
    try:
        await pubsub.subscribe(f"job:{channel_id}")
    except ConnectionError:
        return {
            "status": "error",
            "message": "В данный момент сервис недоступен"
        }

    job = compile_queue.enqueue(compile_game, code, channel_id)

    try:
        while True:
            message = await asyncio.wait_for(
                pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=None
                ),
                timeout=GET_MESSAGE_TIMEOUT
            )
            if message is not None:
                return json.loads(message['data'])
    except asyncio.TimeoutError:
        return {
            "status": "error",
            "message": "Превышено время ожидания"
        }
    except Exception:
        return {
            "status": "error",
            "message": "Произошла непредвиденная ошибка"
        }
    finally:
        await pubsub.unsubscribe(channel_id)
        await pubsub.close()
