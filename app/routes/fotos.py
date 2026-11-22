from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.storage import upload_foto, TAMANHO_MAXIMO

router = APIRouter(prefix="/fotos", tags=["fotos"])


@router.post("")
def enviar_foto(foto: UploadFile = File(...)):
    # lê no máximo 5 MB + 1 byte: se vier mais que isso, o storage recusa
    conteudo = foto.file.read(TAMANHO_MAXIMO + 1)

    try:
        url = upload_foto(conteudo, foto.content_type)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))

    return {"url": url}