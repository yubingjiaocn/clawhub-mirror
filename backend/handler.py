"""AWS Lambda handler using Mangum to wrap FastAPI."""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
