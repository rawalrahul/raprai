"""
helm/nemoclaw_log.py — NemoClaw's debug log (nemoclaw_debug.log in the data folder).

Both NemoClaw modules log every WSL command and its output here. One handler on
the "nemoclaw" logger, so the file is opened once, and it's capped at about
2 MB (1 MB plus one old copy).
"""

import logging
from logging.handlers import RotatingFileHandler


def nemoclaw_logger(name: str) -> logging.Logger:
    parent = logging.getLogger("nemoclaw")
    if not parent.handlers:
        parent.setLevel(logging.DEBUG)
        try:
            from helm.paths import user_data_dir
            fh = RotatingFileHandler(str(user_data_dir() / "nemoclaw_debug.log"),
                                     maxBytes=1_000_000, backupCount=1, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s"))
            parent.addHandler(fh)
        except OSError:
            parent.addHandler(logging.NullHandler())   # no data folder: just don't keep a log
    return logging.getLogger(f"nemoclaw.{name}")
