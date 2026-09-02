from typing import List, Optional
from sqlmodel import SQLModel
from sqlmodel import Field, Relationship
from datetime import datetime, timezone
from enum import Enum

class PostType(str, Enum):
    news = "новость"
    article = "статья"

def post_type_to_title(post_type):
    return {
        PostType.news: "Новости",
        PostType.article: "Статьи"
    }.get(post_type)

def post_type_to_action(post_type):
    return {
            PostType.news: "Новость",
            PostType.article: "Статью"
        }.get(post_type)

class Status(str, Enum):
    draft = "черновик"
    moderation = "на модерации"
    published = "опубликован"

def utc_now():
    return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True)
    password_hash: str
    verified: bool = False
    is_admin: bool = False
    email_notifications_enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: PostType = Field(default=PostType.news)
    status: Status = Field(default=Status.draft)
    title: Optional[str] = Field(unique=True, index=True)
    summary: Optional[str] = ""
    content: Optional[str] = ""
    preview_url: Optional[str]
    created_at: datetime = Field(default_factory=utc_now)
    num_comments: int = Field(default=0)
    pinned: bool = Field(default=False)

    user_id: Optional[int] = Field(foreign_key="user.id")
    user: User = Relationship()
    comments: List["Comment"] = Relationship()

class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    status: Status = Field(default=Status.draft)
    title: str = Field(unique=True, index=True)
    description: str = ""
    preview_url: str
    bin_path: str
    votes: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)
    num_comments: int = Field(default=0)

    user_id: Optional[int] = Field(foreign_key="user.id")
    user: User = Relationship()
    comments: List["Comment"] = Relationship()

class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    created_at: datetime = Field(default_factory=utc_now)

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship()
    post_id: Optional[int] = Field(default=None, foreign_key="post.id")
    game_id: Optional[int] = Field(default=None, foreign_key="game.id")

class Vote(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    game_id: int = Field(foreign_key="game.id", primary_key=True)
    created_at: datetime = Field(default_factory=utc_now)
