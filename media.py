from pathlib import Path
import os


from fastapi import UploadFile
import aiofiles
import shutil
from config import Config

MEDIA_ROOT = Config.MEDIA_ROOT
MEDIA_URL = Config.MEDIA_URL


async def save_file(path, file: UploadFile):
    async with aiofiles.open(path, 'wb') as o_file:
        while content := await file.read(1024 * 100):
            await o_file.write(content)

async def save_post_preview(post_id: str, image: UploadFile):
    post_folder = os.path.join(MEDIA_ROOT, "posts", post_id)
    preview_path = os.path.join(post_folder, image.filename)
    os.makedirs(post_folder, exist_ok=True)

    for filename in os.listdir(post_folder):
        path = os.path.join(post_folder, filename)
        if os.path.isfile(path):
            os.remove(path)
    
    await save_file(preview_path, image)

    return f"{MEDIA_URL}/posts/{post_id}/{image.filename}"

async def save_post_image(post_id: str, image: UploadFile):
    post_images_folder = os.path.join(MEDIA_ROOT, "posts", post_id, "images")
    image_path = os.path.join(post_images_folder, image.filename)
    os.makedirs(post_images_folder, exist_ok=True)

    await save_file(image_path, image)
    return f"{MEDIA_URL}/posts/{post_id}/images/{image.filename}"

async def delete_post_media(post_id: str):
    post_folder = os.path.join(MEDIA_ROOT, "posts", post_id)
    if os.path.exists(post_folder):
        shutil.rmtree(post_folder)

async def clear_unused_images(post_id: str, used_images: set[str]):
    filtered_images = set()
    for image in used_images:
        if image != '':
            try:
                p = Path(image)
                filtered_images.add(p.name)
            except Exception:
                pass

    post_images_folder = os.path.join(MEDIA_ROOT, "posts", post_id, "images")
    if os.path.exists(post_images_folder):
        for filename in os.listdir(post_images_folder):
            if filename not in filtered_images:
                path = os.path.join(post_images_folder, filename)
                os.remove(path)

async def save_game(game_id: str, preview, binary):
    game_folder = os.path.join(MEDIA_ROOT, "games", game_id)
    image_path = os.path.join(game_folder, preview.filename)
    binary_path = os.path.join(game_folder, binary.filename)
    await delete_game_media(game_id)
    os.makedirs(game_folder, exist_ok=True)

    await save_file(image_path, preview)
    await save_file(binary_path, binary)
    
    return (
        f"{MEDIA_URL}/games/{game_id}/{preview.filename}",
        f"{MEDIA_URL}/games/{game_id}/{binary.filename}",
    )

async def delete_game_media(game_id: str):
    game_folder = os.path.join(MEDIA_ROOT, "games", game_id)
    if os.path.exists(game_folder):
        shutil.rmtree(game_folder)
