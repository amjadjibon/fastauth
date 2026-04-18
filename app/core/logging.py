import logging
import logging.config
from pathlib import Path

import yaml

_CONF = Path(__file__).resolve().parents[2] / "conf" / "log.yaml"


def setup_logging() -> None:
    with _CONF.open() as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
