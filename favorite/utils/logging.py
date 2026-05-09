import logging
import sys

_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def get_logger(name: str) -> logging.Logger:
  logger = logging.getLogger(name)
  if not logger.handlers:
      handler = logging.StreamHandler(sys.stderr)
      handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
      logger.addHandler(handler)
  logger.setLevel(logging.WARNING)
  return logger
