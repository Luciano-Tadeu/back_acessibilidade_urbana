import asyncio
import math

from fastapi import WebSocket

from app.schemas import (
    AreaWS,
    EventoOcorrenciaCriada,
    EventoOcorrenciaRemovida,
    OcorrenciaOut,
    OcorrenciaRemovida,
)

RAIO_TERRA_M = 6_371_000
MAX_CONEXOES = 200  # teto de conexões simultâneas (a API está pública)


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em metros entre dois pontos GPS (fórmula de Haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_M * math.asin(math.sqrt(a))


class ConnectionManager:
    def __init__(self):
        # cada conexão aberta e a área que o aparelho está vendo (None até ele informar)
        self.conexoes: dict[WebSocket, AreaWS | None] = {}

    async def conectar(self, ws: WebSocket) -> bool:
        await ws.accept()
        if len(self.conexoes) >= MAX_CONEXOES:
            await ws.close(code=1013)  # 1013 = "tente de novo mais tarde"
            return False
        self.conexoes[ws] = None
        return True

    def desconectar(self, ws: WebSocket) -> None:
        self.conexoes.pop(ws, None)

    def definir_area(self, ws: WebSocket, area: AreaWS) -> None:
        self.conexoes[ws] = area

    async def _transmitir(self, latitude: float, longitude: float, mensagem: dict) -> None:
        # só quem tem o ponto dentro da área informada
        destinatarios = [
            ws
            for ws, area in list(self.conexoes.items())
            if area is not None
            and distancia_m(area.latitude, area.longitude, latitude, longitude) <= area.radius_m
        ]
        # envia a todos ao mesmo tempo, para um aparelho lento não atrasar os outros
        resultados = await asyncio.gather(
            *(ws.send_json(mensagem) for ws in destinatarios),
            return_exceptions=True,
        )
        for ws, resultado in zip(destinatarios, resultados):
            if isinstance(resultado, Exception):  # conexão morta: tira da lista
                self.desconectar(ws)

    async def transmitir_criada(self, ocorrencia: OcorrenciaOut) -> None:
        evento = EventoOcorrenciaCriada(data=ocorrencia)
        await self._transmitir(
            ocorrencia.latitude, ocorrencia.longitude, evento.model_dump(mode="json")
        )

    async def transmitir_removida(self, ocorrencia_id, latitude: float, longitude: float) -> None:
        evento = EventoOcorrenciaRemovida(data=OcorrenciaRemovida(id=ocorrencia_id))
        await self._transmitir(latitude, longitude, evento.model_dump(mode="json"))


gerenciador = ConnectionManager()