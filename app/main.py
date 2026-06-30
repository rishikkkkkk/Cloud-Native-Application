from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time
import os

app = FastAPI(title="DevOps Portfolio App", version="1.0.0")

REQUEST_COUNT = Counter("app_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "Request latency", ["endpoint"])

APP_ENV = os.getenv("APP_ENV", "dev")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(latency)
    return response


@app.get("/")
def root():
    return {
        "message": "DevOps Portfolio App is running!",
        "environment": APP_ENV,
        "version": APP_VERSION,
    }


@app.get("/health")
def health():
    return {"status": "healthy", "env": APP_ENV}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# test