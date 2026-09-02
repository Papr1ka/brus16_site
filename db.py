from sqlmodel import SQLModel, create_engine
from models import *
from config import Config
from redis import Redis
import redis.asyncio as aioredis
from rq import Queue

engine = create_engine(Config.DATABASE_URL, echo=Config.DEBUG)
redis = Redis.from_url(Config.REDIS_URL)
redis_async = aioredis.Redis.from_url(Config.REDIS_URL)
mail_queue = Queue(Config.REDIS_QUEUE_MAIL, connection=redis)
compile_queue = Queue(Config.REDIS_COMPILE_QUEUE, connection=redis)

def init_db():
    SQLModel.metadata.create_all(engine)

init_db()
