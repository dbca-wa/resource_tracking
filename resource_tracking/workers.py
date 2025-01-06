from typing import Any, Dict

from uvicorn.workers import UvicornWorker as BaseUvicornWorker


class UvicornWorker(BaseUvicornWorker):
    # UvicornWorker doesn't support the lifespan protocol.
    # Reference: https://stackoverflow.com/a/75996092/14508
    CONFIG_KWARGS: Dict[str, Any] = {"loop": "auto", "http": "auto", "lifespan": "off", "timeout_keep_alive": 30}
