from typing import Optional, List
from sqlmodel import Session, select, desc, and_, delete
from sqlalchemy.orm import selectinload

from db import engine
from models import User, Post, Game, Comment, Vote, PostType, Status

# General

def update_instance(instance):
    with Session(engine) as session:
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance

def delete_instance(instance):
    with Session(engine) as session:
        session.delete(instance)
        session.commit()

# Users

def get_user_by_id(user_id: int) -> Optional[User]:
    with Session(engine) as session:
        return session.get(User, user_id)

def get_user_by_email(email: str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()

def get_user_by_username(username: str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        return session.exec(statement).first()

def create_user(username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash, verified=False)
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


# posts

def get_post_by_title(title: str) -> Optional[User]:
    with Session(engine) as session:
        statement = (
            select(Post)
            .where(Post.title == title)
            .options(selectinload(Post.user))
        )
        return session.exec(statement).first()

def get_draft_post_by_user_id(user_id) -> Optional[Post]:
    with Session(engine) as session:
        statement = (
            select(Post)
            .where(Post.user_id == user_id)
            .where(Post.status == Status.draft)
            .options(selectinload(Post.user))
        )
        return session.exec(statement).first()

def get_post_by_id(post_id: int) -> Optional[Post]:
    with Session(engine) as session:
        statement = (
            select(Post).where(Post.id == post_id)
            .options(selectinload(Post.user))
        )
        return session.exec(statement).first()

def get_recent_posts(limit: int = 2, status: Status = Status.published) -> List[Post]:
    with Session(engine) as session:
        statement = (
            select(Post)
            .where(Post.status == status)
            .where(Post.type == PostType.news)
            .order_by(desc(Post.created_at))
            .limit(limit)
            .options(selectinload(Post.user))
        )
        return session.exec(statement).all()

def get_all_posts(status: Optional[Status] = None, type: Optional[PostType] = None, pinned = None) -> List[Post]:
    with Session(engine) as session:
        statement = select(Post)
        if status:
            statement = statement.where(Post.status == status)
        if type:
            statement = statement.where(Post.type == type)
        if pinned:
            statement = statement.where(Post.pinned == pinned)

        statement = statement.order_by(desc(Post.created_at)).options(selectinload(Post.user))
        return session.exec(statement).all()

def get_all_posts_from_user(user_id: int, status: Status = Status.published, type: Optional[PostType] = None) -> List[Post]:
    with Session(engine) as session:
        statement = (
            select(Post)
            .where(Post.user_id == user_id)
            .where(Post.status == status)
        )
        if type:
            statement = statement.where(Post.type == type)
        statement = statement.order_by(desc(Post.created_at)).options(selectinload(Post.user))
        return session.exec(statement).all()

def create_post(user_id) -> Post:
    post = Post(user_id=user_id, title=None)
    with Session(engine) as session:
        session.add(post)
        session.commit()
        session.refresh(post)
        return post

# Games

def get_game_by_title(title: str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(Game).where(Game.title == title)
        return session.exec(statement).first()

def get_game_by_id(game_id: int) -> Optional[Game]:
    with Session(engine) as session:
        statement = select(Game).where(Game.id == game_id).options(selectinload(Game.user))
        return session.exec(statement).first()

def get_hitparade(limit: int = 10) -> List[Game]:
    with Session(engine) as session:
        statement = (
            select(Game)
            .where(Game.status == Status.published)
            .order_by(desc(Game.votes))
            .limit(limit)
            .options(selectinload(Game.user))
        )
        return session.exec(statement).all()

def get_all_games(status: Status = None) -> List[Game]:
    with Session(engine) as session:
        statement = (
            select(Game)
            .where(Game.status == status)
            .order_by(desc(Game.created_at))
            .options(selectinload(Game.user))
        )
        return session.exec(statement).all()

def get_all_games_from_user(user_id: int, status: Status = None) -> List[Game]:
    with Session(engine) as session:
        statement = (
            select(Game)
            .where(Game.user_id == user_id)
            .where(Game.status == status)
            .order_by(desc(Game.created_at))
            .options(selectinload(Game.user))
        )
        return session.exec(statement).all()

# Votes

def toggle_vote(user_id: int, game_id: int) -> bool:
    with Session(engine) as session:
        statement = select(Vote).where(and_(Vote.user_id == user_id, Vote.game_id == game_id))
        existing = session.exec(statement).first()

        game = session.get(Game, game_id)
        if game:
            if not existing:
                vote = Vote(user_id=user_id, game_id=game_id)
                session.add(vote)
                game.votes += 1
            else:
                session.delete(existing)
                game.votes -= 1

            session.add(game)
            session.commit()
            return True
        
        return False

# Comments

def get_comments_for_post(post_id: int) -> List[Comment]:
    with Session(engine) as session:
        statement = (
            select(Comment)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at)
            .options(selectinload(Comment.user))
        )
        return session.exec(statement).all()

def get_comments_for_game(game_id: int) -> List[Comment]:
    with Session(engine) as session:
        statement = (
            select(Comment)
            .where(Comment.game_id == game_id)
            .order_by(Comment.created_at)
            .options(selectinload(Comment.user))
        )
        return session.exec(statement).all()

def create_comment(**kwargs) -> Comment:
    comment = Comment(**kwargs)
    with Session(engine) as session:
        session.add(comment)
        session.commit()
        session.refresh(comment)
        return comment

def delete_comments_for_post(post_id: int):
    with Session(engine) as session:
        statement = (
            delete(Comment)
            .where(Comment.post_id == post_id)
        )
        session.exec(statement)
        session.commit()

def delete_comments_for_game(game_id: int):
    with Session(engine) as session:
        statement = (
            delete(Comment)
            .where(Comment.game_id == game_id)
        )
        session.exec(statement)
        session.commit()
