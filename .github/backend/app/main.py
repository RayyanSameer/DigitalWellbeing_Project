from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    # Runs the FastAPI app with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)
