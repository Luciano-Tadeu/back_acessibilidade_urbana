import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.models import Usuario, Ocorrencia
from app.database import db

SessionLocal = sessionmaker(bind=db)

LIMITE_ENVIOS_POR_HORA = 3


def get_db():
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()


def dispositivo_atual(
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    sessao: Session = Depends(get_db),
) -> str:
    if x_device_id is None:
        raise HTTPException(status_code=401, detail="Identificação do aparelho ausente")

    id_limpo = x_device_id.strip()
    if not 8 <= len(id_limpo) <= 128:
        raise HTTPException(status_code=401, detail="Identificação do aparelho inválida")

    device_hash = hashlib.sha256(id_limpo.encode()).hexdigest()

    # cria o usuário se ainda não existir (sem erro se já existir)
    sessao.execute(insert(Usuario).values(device_hash=device_hash).on_conflict_do_nothing())
    sessao.commit()

    return device_hash


def limitar_envios(
    device_hash: str = Depends(dispositivo_atual),
    sessao: Session = Depends(get_db),
) -> str:
    desde = datetime.now(timezone.utc) - timedelta(hours=1)
    total = sessao.scalar(
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