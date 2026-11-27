from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, events

app = FastAPI(title="Кинопятница API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(events.router)


@app.get("/health")
def health():
    return {"status": "ok"}