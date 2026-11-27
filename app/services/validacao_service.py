from datetime import datetime, timezone
from uuid import UUID
from dataclasses import dataclass
from geoalchemy2 import Geometry
from sqlalchemy import func, select, cast
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ValidacaoSearch
from app.models import Ocorrencia, Validacao

VOTOS_PARA_REMOVER = 2  # aparelhos diferentes dizendo "não está mais"


@dataclass
class ResultadoValidacao:
    ativa: bool
    latitude: float | None = None   # só preenchidos quando o pino é removido
    longitude: float | None = None

class OcorrenciaNaoEncontrada(Exception):
    pass


class AutorNaoPodeValidar(Exception):
    pass


async def registrar_validacao(
    sessao: AsyncSession, ocorrencia_id: UUID, device_hash: str, ainda_existe: bool
) -> bool:
    """Registra o voto e devolve True se a ocorrência continua ativa."""
    # trava a linha do pino: votos simultâneos esperam a vez e a contagem fica correta
    ocorrencia = await sessao.scalar(
        select(Ocorrencia)
        .where(Ocorrencia.id == ocorrencia_id, Ocorrencia.status == True)  # noqa: E712
        .with_for_update()
    )
    if ocorrencia is None:
        raise OcorrenciaNaoEncontrada()

    if ocorrencia.device_hash == device_hash:
        raise AutorNaoPodeValidar()

    # um voto por aparelho: se já votou, o voto é atualizado
    await sessao.execute(
        insert(Validacao)
        .values(
            ocorrencia_id=ocorrencia_id,
            device_hash=device_hash,
            ainda_existe=ainda_existe,
        )
        .on_conflict_do_update(
            index_elements=["ocorrencia_id", "device_hash"],
            set_={"ainda_existe": ainda_existe, "criado_em": func.now()},
        )
    )

    # como há um voto por aparelho, cada linha "não está mais" é um aparelho diferente
    nao_esta_mais = await sessao.scalar(
        select(func.count())
        .select_from(Validacao)
        .where(
            Validacao.ocorrencia_id == ocorrencia_id,
            Validacao.ainda_existe == False,  # noqa: E712
        )
    )

    resultado = ResultadoValidacao(ativa=True)
    if nao_esta_mais >= VOTOS_PARA_REMOVER:
        ocorrencia.status = False
        ocorrencia.removido_em = datetime.now(timezone.utc)
        latitude, longitude = (
            await sessao.execute(
                select(
                    func.ST_Y(cast(Ocorrencia.localizacao, Geometry)),
                    func.ST_X(cast(Ocorrencia.localizacao, Geometry)),
                ).where(Ocorrencia.id == ocorrencia_id)
            )
        ).one()
        resultado = ResultadoValidacao(ativa=False, latitude=latitude, longitude=longitude)

    await sessao.commit()
    return resultado

async def buscar_validacoes(device_hash: str, sessao: AsyncSession):
    stmt = select(Validacao).where(Validacao.device_hash == device_hash)
    resultado = await sessao.execute(stmt)
    linhas = resultado.scalars().all()

    return [
        ValidacaoSearch(ocorrencia_id=linha.ocorrencia_id) for linha in linhas
    ]

