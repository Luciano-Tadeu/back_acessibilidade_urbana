from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import dispositivo_atual, get_db
from app.schemas import ValidacaoCreate, ValidacaoOut
from app.services import validacao_service
from app.services.validacao_service import AutorNaoPodeValidar, OcorrenciaNaoEncontrada
from app.services.connection_manager import gerenciador

router = APIRouter(prefix="/ocorrencias", tags=["validacoes"])


@router.post("/{ocorrencia_id}/validacoes", response_model=ValidacaoOut)
async def validar_ocorrencia(
    ocorrencia_id: UUID,
    dados: ValidacaoCreate,
    background: BackgroundTasks,
    device_hash: str = Depends(dispositivo_atual),
    sessao: AsyncSession = Depends(get_db),
):
    try:
        resultado = await validacao_service.registrar_validacao(
            sessao, ocorrencia_id, device_hash, dados.still_exists
        )
    except OcorrenciaNaoEncontrada:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    except AutorNaoPodeValidar:
        raise HTTPException(status_code=403, detail="O autor não pode validar o próprio pino")

    if not resultado.ativa:
        background.add_task(
            gerenciador.transmitir_removida, ocorrencia_id, resultado.latitude, resultado.longitude
        )

    return ValidacaoOut(
        ocorrencia_id=ocorrencia_id,
        still_exists=dados.still_exists,
        ocorrencia_ativa=resultado.ativa,
    )