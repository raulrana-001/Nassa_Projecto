"""TerraWatch Angola — API. Executar: uvicorn main:app --reload --port 8000  (docs em /docs)"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import init_db
from routes import regioes, observacoes, analises, relatorios, nisar, processamento

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="TerraWatch Angola API", version="0.3.0", lifespan=lifespan)

extra = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=extra,
                   allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])

for r in (regioes, observacoes, analises, relatorios, nisar, processamento):
    app.include_router(r.router, prefix="/api")

@app.get("/api/saude", tags=["Sistema"])
def saude():
    return {"estado": "ok", "versao": app.version}
