import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, CHAR, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Index, Identity, func, text,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine

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
db = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)   # síncrona: Alembic e /saude

db_async = create_async_engine(
    url.set(drivername="postgresql+asyncpg"),
    connect_args={"timeout": 5},
    pool_pre_ping=True,
)  # assíncrona: a sessão do dependencies.py usa esta

# cria a base do banco de dados
Base = declarative_base()
