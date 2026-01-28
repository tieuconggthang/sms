import logging
import os

def setup_logging(level: str = "INFO", log_file: str = "logs/app.log") -> None:
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    lvl = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s %(levelname)-5s [%(threadName)s] [%(name)s] %(message)s"

    root = logging.getLogger()
    root.setLevel(lvl)
    root.handlers.clear()

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(fmt))
    root.addHandler(sh)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt))
    root.addHandler(fh)
