import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, CHAR, Boolean, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, Index, Identity, func, text,
)
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import URL

load_dotenv()

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv("DB_NAME"),
)

# cria a conexão do seu banco
db = create_engine(url)

# cria a base do banco de dados
Base = declarative_base()

# criar as classes/tabelas do banco
class CategoriaObstaculo(Base):
    __tablename__ = "categoria_obstaculo"

    id = Column(Integer, Identity(always=True), primary_key=True)
    slug = Column(String(40), nullable=False, unique=True)  # valor que o app envia/recebe
    nome = Column(String(60), nullable=False, unique=True)  # texto mostrado ao usuário


class Ocorrencia(Base):
    __tablename__ = "ocorrencia"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default=text("gen_random_uuid()"))
    device_hash = Column(CHAR(64), nullable=False)  # SHA-256 do aparelho
    categoria_id = Column(Integer, ForeignKey("categoria_obstaculo.id"), nullable=False)
    localizacao = Column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    foto_chave = Column(Text, nullable=False)
    titulo = Column(String(100))
    status = Column(String(20), nullable=False, server_default="ativa")
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    removido_em = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status IN ('ativa', 'removida')", name="ocorrencia_status_check"),
        # índice espacial só das ocorrências ativas (busca por raio)
        Index(
            "ocorrencia_localizacao_ativa_idx", "localizacao",
            postgresql_using="gist",
            postgresql_where=text("status = 'ativa'"),
        ),
    )


# índice para o limite de envios por aparelho
Index("ocorrencia_device_criado_idx", Ocorrencia.device_hash, Ocorrencia.criado_em.desc())


class Validacao(Base):
    __tablename__ = "validacao"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default=text("gen_random_uuid()"))
    ocorrencia_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ocorrencia.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_hash = Column(CHAR(64), nullable=False)
    ainda_existe = Column(Boolean, nullable=False)  # resposta do "Ainda está aí?"
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # um voto por aparelho em cada ocorrência
    __table_args__ = (UniqueConstraint("ocorrencia_id", "device_hash"),)