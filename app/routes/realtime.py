from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas import AreaWS
from app.services.connection_manager import gerenciador

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def websocket_mapa(ws: WebSocket):
    if not await gerenciador.conectar(ws):
        return
    try:
        while True:
            try:
                dados = await ws.receive_json()
                area = AreaWS.model_validate(dados)
            except ValueError:  # JSON quebrado ou área fora dos limites
                await ws.send_json({"event": "error", "detail": "Área inválida"})
                continue
            gerenciador.definir_area(ws, area)
            await ws.send_json({"event": "area_set"})
    except WebSocketDisconnect:
        gerenciador.desconectar(ws)