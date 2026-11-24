from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, limitar_envios

router = APIRouter(prefix="/saude", tags=["saude"])


@router.get("/banco")
async def testar_banco(sessao: AsyncSession = Depends(get_db)):
    try:
        await sessao.execute(text("SELECT 1"))
        postgis = await sessao.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
        )
    except Exception as erro:
        print("Falha ao conectar no banco:", erro)  # o detalhe fica só no terminal
        raise HTTPException(status_code=503, detail="Banco indisponível")

    return {"banco": "ok", "postgis": postgis is not None}

@router.get("/dispositivo")
def testar_dispositivo(device_hash: str = Depends(limitar_envios)):
    return {"device_hash": device_hash}