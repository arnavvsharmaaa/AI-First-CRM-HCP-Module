import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.database import engine, Base
from models import hcp, interaction as models_interaction
from routers import interaction
import uvicorn

app = FastAPI(title="AI-First CRM HCP Module")

# Log all requests
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"=== INCOMING REQUEST: {request.method} {request.url.path} ===", flush=True)
    response = await call_next(request)
    print(f"=== RESPONSE: {response.status_code} ===", flush=True)
    return response

# CORS setup — comma-separated list, e.g. "https://my-app.vercel.app,http://localhost:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interaction.router)

@app.get("/")
async def root():
    return {"status": "server_running", "message": "Backend is up"}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
