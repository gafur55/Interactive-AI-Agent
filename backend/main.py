from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.get("/api/data")
def get_data():
    return {"items": ["hackathon", "fastapi", "react"]}
