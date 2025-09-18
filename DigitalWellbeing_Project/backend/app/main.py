from fastapi import FastAPI
from backend.app.main import app

app = FastAPI()

@app.get("/")
def hello_world():
    return {"message": "Hello, World!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
