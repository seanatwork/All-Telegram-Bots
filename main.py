import importlib.util
import logging
import os
import sys
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))

BOTS = [
    ("austin311bot",    "austin311_bot.py",   "austin311_bot"),
    ("film_bot",        "film_bot.py",         "film_bot"),
    ("gotwaterbot",     "gotwater.py",          "gotwater"),
    ("unitconverterbot","uc.py",               "uc"),
    ("wshnationalsbot", "wshnationalsbot.py",  "wshnationalsbot"),
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


def run_bot(name, main_fn):
    logger.info(f"Starting {name}")
    try:
        main_fn()
    except Exception:
        logger.exception(f"{name} crashed")


if __name__ == "__main__":
    modules = [(modname, load_bot(folder, filename, modname)) for folder, filename, modname in BOTS]

    threads = [
        threading.Thread(target=run_bot, args=(modname, mod.main), name=modname, daemon=True)
        for modname, mod in modules
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()
