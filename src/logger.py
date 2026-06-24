from loguru import logger

logger.add(
    "logs/etl.log",
    rotation="10 MB"
)

logger.info("Logger initialized")