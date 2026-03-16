from fastapi import FastAPI

from app.routers import projects

app = FastAPI(title="Manager AI", version="0.1.0")

app.include_router(projects.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
