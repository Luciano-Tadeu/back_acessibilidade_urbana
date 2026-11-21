import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, CHAR, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Index, Identity, func, text,
)
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import URL
from geoalchemy2.elements import WKTElement

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
class Usuario(Base):
    __tablename__ = "usuario"

    device_hash = Column(CHAR(64), primary_key=True)  # SHA-256 do device_id

    def __init__(self, device_hash):
        self.device_hash = device_hash


class CategoriaObstaculo(Base):
    __tablename__ = "categoria_obstaculo"

    id = Column(Integer, Identity(always=True), primary_key=True)
    slug = Column(String(40), nullable=False, unique=True)  # valor que o app envia/recebe
    nome = Column(String(60), nullable=False, unique=True)  # texto mostrado ao usuário

    def __init__(self, slug, nome):
        self.slug = slug
        self.nome = nome


class Ocorrencia(Base):
    __tablename__ = "ocorrencia"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default=text("gen_random_uuid()"))
    device_hash = Column(
        CHAR(64),
        ForeignKey("usuario.device_hash", ondelete="CASCADE"),
        nullable=False,
    )
    categoria_id = Column(Integer, ForeignKey("categoria_obstaculo.id"), nullable=False)
    localizacao = Column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    foto_chave = Column(Text, nullable=False)
    status = Column(Boolean, nullable=False, server_default=text("true"))
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    removido_em = Column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "ocorrencia_localizacao_ativa_idx", "localizacao",
            postgresql_using="gist",
            postgresql_where=text("status = true"),
        ),
    )

    def __init__(self, device_hash, categoria_id, latitude, longitude, foto_chave):
        self.device_hash = device_hash
        self.categoria_id = categoria_id
        # POINT recebe LONGITUDE primeiro, depois LATITUDE
        self.localizacao = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
        self.foto_chave = foto_chave


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
    device_hash = Column(
        CHAR(64),
        ForeignKey("usuario.device_hash", ondelete="CASCADE"),
        nullable=False,
    )
    ainda_existe = Column(Boolean, nullable=False)  # resposta do "Ainda está aí?"
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("ocorrencia_id", "device_hash"),)

    def __init__(self, ocorrencia_id, device_hash, ainda_existe):
        self.ocorrencia_id = ocorrencia_id
        self.device_hash = device_hash
        self.ainda_existe = ainda_existe