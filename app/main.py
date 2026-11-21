# COMANDO EXECUTAR SERVER LOCAL: uvicorn main:app --reload

from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes.routes import router
import os

load_dotenv()

app = FastAPI()

app.include_router(router)

@app.get("/")
async def root():
    return {"mensagem": "API rodando com sucesso!"}