import logging
import os
import sys
from typing import Optional

format = (
    "%(asctime)s | %(levelname)-7s | %(module)s.%(funcName)s:%(lineno)d | %(message)s"
)
logger: Optional[logging.Logger] = None


def get_lambda_logger() -> logging.Logger:
    global logger
    if not logger:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter(format))
        logger = logging.getLogger(
            os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "NoLambdaEnvironment")
        )
        logger.setLevel(logging.INFO)
        stdout_handler.setLevel(logging.INFO)
        logger.addHandler(stdout_handler)

    return logger
