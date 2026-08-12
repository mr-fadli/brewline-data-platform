import logging
import sys
from brewline.config import LOG_DIR

LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger for the given layer (e.g. 'bronze', 'silver', 'gold').
    Every layer's logs land in one shared file, tagged by name, so a single
    end-to-end run can be read as one timeline instead of three separate files."""
    logger = logging.getLogger(name)

    if logger.handlers:  # already configured (e.g. called twice in one process) -- don't double up
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_DIR / "pipeline.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger