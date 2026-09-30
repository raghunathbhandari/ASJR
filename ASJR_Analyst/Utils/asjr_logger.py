import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")


class UKFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        stamp = datetime.fromtimestamp(record.created, UK)
        return stamp.strftime(datefmt or "%Y-%m-%d %H:%M:%S %Z")


def get_run_logger(log_path):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    name = f"ASJR_ANALYST_{log_path.resolve()}"
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = UKFormatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %Z",
    )

    file_handler = logging.FileHandler(
        log_path,
        mode="a",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def run_log_path(reports_dir):
    stamp = datetime.now(UK).strftime("%Y%m%d_%H%M%S_%Z")
    return Path(reports_dir) / f"asjr_pipeline_{stamp}.log"
