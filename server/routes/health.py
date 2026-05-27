"""
健康检查路由
"""
from fastapi import APIRouter
from server.config import SERVER_NAME, SERVER_VERSION

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "name": SERVER_NAME, "version": SERVER_VERSION}
