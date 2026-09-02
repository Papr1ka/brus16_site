import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    _from_env = (
        'JWT_AUTH_SECRET',
        'JWT_RESET_SECRET',
        'SMTP_HOST',
        'SMTP_PORT',
        'SMTP_USER',
        'SMTP_PASSWORD',
    )
    DEBUG = False
    JWT_AUTH_EXPIRES = 4 * 60 * 60 # 4 hours
    JWT_AUTH_SECRET = os.environ.get("JWT_AUTH_SECRET")
    JWT_RESET_EXPIRES = 15 * 60 # 15 minutes
    JWT_RESET_SECRET = os.environ.get("JWT_RESET_SECRET")
    JWT_ALGORITHM = "HS256"

    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    REDIS_QUEUE_MAIL = "mail_queue"
    REDIS_COMPILE_QUEUE = "compilation_queue"
    WAIT_FOR_COMPILATION_TIMEOUT = 10 # 10 seconds

    DATABASE_FILE_NAME = "brus16.db"
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/brus16.db")
    
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 0))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

    TEMPLATES_ROOT = "templates"
    MEDIA_ROOT = os.path.abspath(os.path.relpath("media"))
    MEDIA_URL = "media"

    TOOLS_PATH = os.path.abspath(os.path.relpath("tools"))
