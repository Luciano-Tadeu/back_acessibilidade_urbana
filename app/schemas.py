from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RAIO_MAXIMO_M = 8000  # teto do raio de busca (o app pode ser adulterado)


# ---------- Fotos ----------

class FotoOut(BaseModel):
    url: str


# ---------- Ocorrências ----------

class OcorrenciaCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "category": "rampa_ausente",
                    "latitude": -15.6014,
                    "longitude": -56.0979,
                    "photo_url": "https://seu-projeto.supabase.co/storage/v1/object/public/fotos/arquivo.jpg",
                }
            ]
        },
    )

    category: str = Field(min_length=1, max_length=40)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    photo_url: str = Field(min_length=1, max_length=500)


class OcorrenciaOut(BaseModel):
    id: UUID
    category: str
    latitude: float
    longitude: float
    photo_url: str
    device_hash: UUID
    created_at: datetime


class OcorrenciaRemovida(BaseModel):
    id: UUID


class BuscaOcorrencias(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    raio_m: float = Field(gt=0, le=RAIO_MAXIMO_M)
    categorias: str | None = None  # slugs separados por vírgula

    @property
    def slugs(self) -> list[str]:
        if not self.categorias:
            return []
        return [s.strip() for s in self.categorias.split(",") if s.strip()]


# ---------- Validações ("Ainda está aí?") ----------

class ValidacaoCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"still_exists": False}]},
    )

    still_exists: bool


class ValidacaoOut(BaseModel):
    ocorrencia_id: UUID
    still_exists: bool
    ocorrencia_ativa: bool  # False se este voto removeu o pino do mapa

class ValidacaoSearch(BaseModel):
    ocorrencia_id: UUID


# ---------- WebSocket ----------

class AreaWS(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_m: float = Field(gt=0, le=RAIO_MAXIMO_M)


class EventoOcorrenciaCriada(BaseModel):
    event: Literal["occurrence_created"] = "occurrence_created"
    data: OcorrenciaOut


class EventoOcorrenciaRemovida(BaseModel):
    event: Literal["occurrence_removed"] = "occurrence_removed"
    data: OcorrenciaRemovida


# ---------- Saúde ----------

class SaudeBancoOut(BaseModel):
    banco: str
    postgis: bool