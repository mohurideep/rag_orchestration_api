import time
import uuid
from flask import Flask, request, g
from flask_restx import Api

from app.configs import load_config
from app.Logger.log_main import get_logger
from app.routes.health import ns as health_ns
from app.utils.errors import AppError

# configure logger once per process, duplicate handlers
logger = get_logger()

# app factory
def create_app() -> Flask:
    app = Flask(__name__)
    cfg = load_config()

    api = Api(app, version="1.0", title="RAG Orchestration API", doc="/docs")
    api.add_namespace(health_ns, path="/health")

    @app.before_request
    def before_request():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.start_time = time.time()
        g.cfg = cfg  # request-scoped config handle

    @app.after_request
    def after_request(resp):
        latency_ms = int((time.time() - g.start_time) * 1000)
        resp.headers["X-Request-ID"] = g.request_id
        logger.info("request_complete", extra={
            "request_id": g.request_id,
            "method": request.method,
            "path": request.path,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
        })
        return resp
    
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        logger.exception(
            "app_error",
            extra={"request_id": getattr(g, "request_id", None), "error_code": err.code},
        )
        return {"request_id": getattr(g, "request_id", None), "error": {"code": err.code, "message": err.message}}, err.http_status
    
    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        logger.exception(
            "unexpected_error",
            extra={"request_id": getattr(g, "request_id", None)},
        )
        return {"request_id": getattr(g, "request_id", None), "error": {"code": "UNHANDLED", "message": "An unexpected error occurred."}}, 500
    
    return app