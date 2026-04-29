import asyncio
import importlib.util
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))

BOTS = [
    ("austin311bot",     "austin311_bot.py",  "austin311_bot", "create_application"),
    ("film_bot",         "film_bot.py",        "film_bot",      "build_app"),
    ("gotwaterbot",      "gotwater.py",         "gotwater",      "build_app"),
    ("unitconverterbot", "uc.py",              "uc",            "build_app"),
    ("wshnationalsbot",  "wshnationalsbot.py", "wshnationalsbot","build_app"),
]


def load_bot(folder, filename, module_name):
    bot_dir = os.path.join(BASE, folder)
    bot_path = os.path.join(bot_dir, filename)
    sys.path.insert(0, bot_dir)
    spec = importlib.util.spec_from_file_location(module_name, bot_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


async def run_app(name, app):
    logger.info(f"Starting {name}")
    try:
        async with app:
            await app.start()
            await app.updater.start_polling()
            await asyncio.Event().wait()
    except Exception:
        logger.exception(f"{name} crashed and will not restart")


async def main():
    apps = []
    for folder, filename, modname, build_fn in BOTS:
        mod = load_bot(folder, filename, modname)
        app = getattr(mod, build_fn)()
        apps.append((modname, app))

    async with asyncio.TaskGroup() as tg:
        for name, app in apps:
            tg.create_task(run_app(name, app))


if __name__ == "__main__":
    asyncio.run(main())
