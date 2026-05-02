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
    ("unobot",           "bot.py",             "unobot",        "build_app"),
]


def load_bot(folder, filename, module_name):
    bot_dir = os.path.join(BASE, folder)
    bot_path = os.path.join(bot_dir, filename)
    sys.path.insert(0, bot_dir)

    before = set(sys.modules.keys())

    spec = importlib.util.spec_from_file_location(module_name, bot_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)

    # Evict this bot's local modules from sys.modules so the next bot can
    # import its own modules by the same name without picking up these versions.
    # The bot object already holds all needed references, so this is safe.
    for key in set(sys.modules.keys()) - before - {module_name}:
        m = sys.modules[key]
        if getattr(m, '__file__', None) and bot_dir in m.__file__:
            del sys.modules[key]

    return mod


async def run_app(name, mod, build_fn):
    delay = 5
    while True:
        logger.info(f"Starting {name}")
        app = getattr(mod, build_fn)()
        try:
            async with app:
                await app.start()
                await app.updater.start_polling()
                await asyncio.Event().wait()
            return
        except Exception:
            logger.exception(f"{name} crashed, retrying in {delay}s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


async def main():
    bots = []
    for folder, filename, modname, build_fn in BOTS:
        if modname == "unobot" and not os.environ.get("UNO_BOT_TOKEN"):
            logger.warning("UNO_BOT_TOKEN not set — skipping Uno bot")
            continue
        mod = load_bot(folder, filename, modname)
        bots.append((modname, mod, build_fn))

    async with asyncio.TaskGroup() as tg:
        for name, mod, build_fn in bots:
            tg.create_task(run_app(name, mod, build_fn))


if __name__ == "__main__":
    asyncio.run(main())
