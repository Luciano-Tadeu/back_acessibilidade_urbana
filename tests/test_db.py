import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()  # carrega as variáveis do .env

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(url, connect_args={"connect_timeout": 5})

with engine.connect() as conn:
    print(conn.execute(text("SELECT version()")).scalar())
    try:
        print("PostGIS:", conn.execute(text("SELECT postgis_version()")).scalar())
    except Exception:
        print("PostGIS NÃO está habilitado neste banco")