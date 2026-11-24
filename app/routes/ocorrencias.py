from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.connection_manager import gerenciador
from app.dependencies import get_db, limitar_envios
from app.schemas import BuscaOcorrencias, OcorrenciaCreate, OcorrenciaOut
from app.services import ocorrencia_service
from app.services.storage import url_da_chave

router = APIRouter(prefix="/ocorrencias", tags=["ocorrencias"])


@router.post("", response_model=OcorrenciaOut, status_code=status.HTTP_201_CREATED)
async def criar_ocorrencia(
    dados: OcorrenciaCreate,
    background: BackgroundTasks,
    device_hash: str = Depends(limitar_envios),
    sessao: AsyncSession = Depends(get_db),
):
    try:
        ocorrencia = await ocorrencia_service.criar_ocorrencia(sessao, device_hash, dados)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))

    saida = OcorrenciaOut(
        id=ocorrencia.id,
        category=dados.category,
        latitude=dados.latitude,
        longitude=dados.longitude,
        photo_url=url_da_chave(ocorrencia.foto_chave),
        created_at=ocorrencia.criado_em,
    )
    background.add_task(gerenciador.transmitir_criada, saida)
    return saida


@router.get("", response_model=list[OcorrenciaOut])
async def listar_ocorrencias(
    busca: Annotated[BuscaOcorrencias, Query()],
    sessao: AsyncSession = Depends(get_db),
):
    return await ocorrencia_service.buscar_por_raio(sessao, busca)