import logging
import os
from wsgiref.simple_server import make_server

from prometheus_client import REGISTRY, make_wsgi_app
from prometheus_client.core import CollectorRegistry

from .collector import BOINCCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_app(registry: CollectorRegistry = REGISTRY) -> object:
    host = os.environ.get("BOINC_HOST", "localhost")
    port = int(os.environ.get("BOINC_PORT", "31416"))
    password = os.environ.get("BOINC_PASSWORD", "")
    registry.register(BOINCCollector(host, port, password))
    return make_wsgi_app(registry)


def main() -> None:
    listen_port = int(os.environ.get("EXPORTER_PORT", "9101"))
    app = build_app()
    logger.info("BOINC exporter listening on port %d", listen_port)
    with make_server("", listen_port, app) as httpd:
        httpd.serve_forever()
