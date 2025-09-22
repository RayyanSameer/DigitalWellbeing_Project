from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
import os

# Load .env file automatically (works for local dev)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Just to confirm
print("Using database:", DATABASE_URL)


app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    # Runs the FastAPI app with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
