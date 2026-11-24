# COMANDO EXECUTAR SERVER LOCAL: uvicorn main:app --reload

from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes.fotos import router as fotos_router
from app.routes.saude import router as saude_router
from app.routes.ocorrencias import router as ocorrencias_router
from app.routes.validacoes import router as validacoes_router
from app.routes.realtime import router as realtime_router

load_dotenv()

app = FastAPI()

app.include_router(fotos_router)
app.include_router(saude_router)
app.include_router(ocorrencias_router)
app.include_router(validacoes_router)
app.include_router(realtime_router)

@app.get("/")
async def root():
    return {"mensagem": "API rodando com sucesso!"}