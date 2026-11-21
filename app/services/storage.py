import os
import uuid
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

BUCKET = "UrbInclusiva"
TIPOS_PERMITIDOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5 MB


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