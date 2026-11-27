from geoalchemy2 import Geography, Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CategoriaObstaculo, Ocorrencia
from app.schemas import BuscaOcorrencias, OcorrenciaCreate, OcorrenciaOut
from app.services.storage import chave_da_url, url_da_chave

LIMITE_BUSCA = 300  # máximo de pinos por consulta


async def criar_ocorrencia(
    sessao: AsyncSession, device_hash: str, dados: OcorrenciaCreate
) -> Ocorrencia:
    categoria_id = await sessao.scalar(
        select(CategoriaObstaculo.id).where(CategoriaObstaculo.slug == dados.category)
    )
    if categoria_id is None:
        raise ValueError("Categoria inválida")

    foto_chave = chave_da_url(dados.photo_url)  # ValueError se a URL não for do nosso bucket

    ocorrencia = Ocorrencia(
        device_hash=device_hash,
        categoria_id=categoria_id,
        latitude=dados.latitude,
        longitude=dados.longitude,
        foto_chave=foto_chave,
    )
    sessao.add(ocorrencia)
    await sessao.commit()
    await sessao.refresh(ocorrencia)
    return ocorrencia


async def buscar_por_raio(sessao: AsyncSession, busca: BuscaOcorrencias) -> list[OcorrenciaOut]:
    # ponto central da busca (no PostGIS: LONGITUDE primeiro, depois LATITUDE)
    centro = cast(
        func.ST_SetSRID(func.ST_MakePoint(busca.lng, busca.lat), 4326),
        Geography,
    )

    consulta = (
        select(
            Ocorrencia.id,
            CategoriaObstaculo.slug,
            func.ST_Y(cast(Ocorrencia.localizacao, Geometry)).label("latitude"),
            func.ST_X(cast(Ocorrencia.localizacao, Geometry)).label("longitude"),
            Ocorrencia.foto_chave,
            Ocorrencia.device_hash,
            Ocorrencia.criado_em,
        )
        .join(CategoriaObstaculo, CategoriaObstaculo.id == Ocorrencia.categoria_id)
        .where(Ocorrencia.status == True)  # noqa: E712  (= true usa o índice parcial)
        .where(func.ST_DWithin(Ocorrencia.localizacao, centro, busca.raio_m))
        .order_by(Ocorrencia.localizacao.op("<->")(centro))
        .limit(LIMITE_BUSCA)
    )

    if busca.slugs:
        consulta = consulta.where(CategoriaObstaculo.slug.in_(busca.slugs))

    linhas = (await sessao.execute(consulta)).all()

    return [
        OcorrenciaOut(
            id=linha.id,
            category=linha.slug,
            latitude=linha.latitude,
            longitude=linha.longitude,
            photo_url=url_da_chave(linha.foto_chave),
            device_hash = linha.device_hash,
            created_at=linha.criado_em,
        )
        for linha in linhas
    ]