# COMANDO EXECUTAR SERVER LOCAL: uvicorn main:app --reload

from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes.fotos import router
from tests.saude import router as saude_router
import os

load_dotenv()

app = FastAPI()

app.include_router(router)
app.include_router(saude_router)

@app.get("/")
async def root():
    return {"mensagem": "API rodando com sucesso!"}