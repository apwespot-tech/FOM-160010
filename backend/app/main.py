from fastapi import FastAPI

app = FastAPI(title="Книжный круговорот API")

@app.get("/")
def read_root():
    return {"message": "Книжный круговорот API работает"}

@app.get("/health")
def health_check():
    return {"status": "ok"}