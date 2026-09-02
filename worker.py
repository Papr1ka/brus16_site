import subprocess
import tempfile
import os
import shutil
import logging
import base64
import json

from redis import Redis
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMP_FILES = Config.TOOLS_PATH

redis = Redis.from_url(Config.REDIS_URL)
COMPILATION_TIMEOUT = Config.WAIT_FOR_COMPILATION_TIMEOUT


def compile_game(code: str, channel_id: str) -> dict:
    task_result = {}
    try:
        with tempfile.TemporaryDirectory(delete=False) as temp_dir:
            logger.info(f"Created temp dir: {temp_dir}")
            code_folder_path = os.path.join(temp_dir, "game")
            tools_folder_path = os.path.join(temp_dir, "tools")
            code_path = os.path.join(code_folder_path, "game.py")
            bin_path = os.path.join(temp_dir, "game.bin")
            asm_path = os.path.join(temp_dir, "asm.txt")

            os.mkdir(code_folder_path)
            os.mkdir(tools_folder_path)

            with open(code_path, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info(f"Saved code at: {code_path}")

            shutil.copytree(COMP_FILES, tools_folder_path, dirs_exist_ok=True, ignore=lambda path, names: ['brus16.py'])
            shutil.copy(os.path.join(COMP_FILES, "brus16.py"), code_folder_path)
            logger.info(f"Copied tools to: {temp_dir}")

            os.chdir(temp_dir)

            cmd = [
                "nsjail",
                "-Mo",
                "--chroot", "/",
                "--user", "nobody",
                "--group", "nogroup",
                "--time_limit", str(COMPILATION_TIMEOUT),
                "--rlimit_as", "128",
                "--disable_clone_newnet",
                "-B", f"{temp_dir}:/input",
                "--",
                "/bin/sh", "-c", 'chdir /input && python3 game/game.py',
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=COMPILATION_TIMEOUT
            )
            
            logger.info(f"Process end up with {result.returncode}")
            logger.info(result.stdout)
            logger.info(result.stderr)

            if result.returncode:
                task_result = {"status": "error", "message": f"Ошибка компиляции:\n{result.stderr}"}
                logger.info(f"Compilation failed\n{result.stderr}")
            elif (not os.path.exists(bin_path)) or (not os.path.exists(asm_path)):
                task_result = {"status": "error", "message": f"Ошибка компиляции:\nИспользуйте save_game('game.bin', code)"}
                logger.info(f"Compilation failed, save_game not called")
            else:
                with open(bin_path, 'rb') as file:
                    binary_data = file.read()

                with open(asm_path, 'r') as file:
                    asm = file.read()

                logger.info("Compilation end up")
                task_result = {
                    "status": "success",
                    "binary": base64.b64encode(binary_data).decode('utf-8'),
                    "asm": asm,
                    "message": result.stdout
                }

    except subprocess.TimeoutExpired:
        logger.error("Compilation timeout")
        task_result = {"status": "error", "message": "Исчерпано время компиляции"}
    except Exception as e:
        logger.error(f"Error: {e}")
        task_result = {"status": "error", "message": f"Произошла непредвиденная ошибка: {e}"}

    redis.publish(f"job:{channel_id}", json.dumps(task_result))
    return task_result
