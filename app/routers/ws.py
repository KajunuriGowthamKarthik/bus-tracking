from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.realtime import manager


router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive; optionally handle client pings/filters
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


