import os
import uuid
from dotenv import load_dotenv
import re
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

BUCKET = "UrbInclusiva"
TIPOS_PERMITIDOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5 MB
PREFIXO_URL = f"{os.getenv('SUPABASE_URL').rstrip('/')}/storage/v1/object/public/{BUCKET}/"
PADRAO_ARQUIVO = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpg|png|webp)$"
)


def chave_da_url(url: str) -> str:
    if not url.startswith(PREFIXO_URL):
        raise ValueError("URL da foto inválida")
    chave = url.removeprefix(PREFIXO_URL).split("?")[0]
    if not PADRAO_ARQUIVO.match(chave):
        raise ValueError("URL da foto inválida")
    return chave


def url_da_chave(chave: str) -> str:
    return PREFIXO_URL + chave


def upload_foto(conteudo: bytes, content_type: str) -> str:
    if content_type not in TIPOS_PERMITIDOS:
        raise ValueError("Formato de imagem não permitido")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ValueError("Imagem maior que 5 MB")

    nome = f"{uuid.uuid4()}.{TIPOS_PERMITIDOS[content_type]}"

    supabase.storage.from_(BUCKET).upload(
        path=nome,
        file=conteudo,
        file_options={"content-type": content_type},
    )

    return supabase.storage.from_(BUCKET).get_public_url(nome)