from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

from app.dependencies import limitar_envios
from app.database import db 

router = APIRouter(prefix="/saude", tags=["saude"])


@router.get("/banco")
def testar_banco():
    try:
        with Session(db) as sessao:
            sessao.execute(text("SELECT 1"))
            postgis = sessao.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            ).scalar()
    except Exception as erro:
        print("Falha ao conectar no banco:", erro)  # o detalhe fica só no terminal
        raise HTTPException(status_code=503, detail="Banco indisponível")

    return {"banco": "ok", "postgis": postgis is not None}

@router.get("/dispositivo")
def testar_dispositivo(device_hash: str = Depends(limitar_envios)):
    return {"device_hash": device_hash}