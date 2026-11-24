import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import db_async
from app.models import Usuario, Ocorrencia

SessionAsync = async_sessionmaker(db_async, expire_on_commit=False)

LIMITE_ENVIOS_POR_HORA = 3


async def get_db():
    async with SessionAsync() as sessao:
        yield sessao


async def dispositivo_atual(
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    sessao: AsyncSession = Depends(get_db),
) -> str:
    if x_device_id is None:
        raise HTTPException(status_code=401, detail="Identificação do aparelho ausente")

    id_limpo = x_device_id.strip()
    if not 8 <= len(id_limpo) <= 128:
        raise HTTPException(status_code=401, detail="Identificação do aparelho inválida")

    device_hash = hashlib.sha256(id_limpo.encode()).hexdigest()

    # cria o usuário se ainda não existir (sem erro se já existir)
    await sessao.execute(insert(Usuario).values(device_hash=device_hash).on_conflict_do_nothing())
    await sessao.commit()

    return device_hash


async def limitar_envios(
    device_hash: str = Depends(dispositivo_atual),
    sessao: AsyncSession = Depends(get_db),
) -> str:
    desde = datetime.now(timezone.utc) - timedelta(hours=1)
    total = await sessao.scalar(
        select(func.count())
        .select_from(Ocorrencia)
        .where(Ocorrencia.device_hash == device_hash, Ocorrencia.criado_em > desde)
    )
    if total >= LIMITE_ENVIOS_POR_HORA:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {LIMITE_ENVIOS_POR_HORA} envios por hora atingido",
        )
    return device_hash