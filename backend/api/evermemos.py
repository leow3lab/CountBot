"""EverMemOS 集成 API 端点

提供 EverMemOS 配置和代理操作的 HTTP 接口:
- GET  /api/evermemos/health   — 检查 EverMemOS 连通性
- GET  /api/evermemos/config   — 获取 EverMemOS 配置
- PUT  /api/evermemos/config   — 保存 EverMemOS 配置
- POST /api/evermemos/test     — 测试连接
- GET  /api/evermemos/memories — 检索记忆（预览用）
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional, List, Any

from backend.modules.config.loader import config_loader
from backend.modules.config.schema import EverMemOSConfig

router = APIRouter(prefix="/api/evermemos", tags=["evermemos"])


# ============================================================================
# Request / Response Models
# ============================================================================


class EverMemOSConfigResponse(BaseModel):
    """EverMemOS 配置响应"""
    enabled: bool
    api_base_url: str
    user_id: str
    group_id: str
    auto_memorize: bool
    inject_memories: bool
    retrieval_limit: int
    retrieval_mode: str
    timeout: int


class UpdateEverMemOSConfigRequest(BaseModel):
    """更新 EverMemOS 配置请求"""
    enabled: Optional[bool] = None
    api_base_url: Optional[str] = None
    user_id: Optional[str] = None
    group_id: Optional[str] = None
    auto_memorize: Optional[bool] = None
    inject_memories: Optional[bool] = None
    retrieval_limit: Optional[int] = Field(default=None, ge=1, le=20)
    retrieval_mode: Optional[str] = None
    timeout: Optional[int] = Field(default=None, ge=1, le=60)


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    connected: bool
    message: str
    api_base_url: str


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    api_base_url: str = Field(..., description="EverMemOS API 地址")
    timeout: int = Field(default=5, ge=1, le=30)


class TestConnectionResponse(BaseModel):
    """测试连接响应"""
    success: bool
    message: str


class MemoryPreviewItem(BaseModel):
    """记忆预览条目"""
    content: str
    memory_type: Optional[str] = None
    created_at: Optional[str] = None


class MemoriesPreviewResponse(BaseModel):
    """记忆预览响应"""
    success: bool
    memories: List[dict[str, Any]]
    total: int
    message: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health", response_model=HealthCheckResponse)
async def check_evermemos_health() -> HealthCheckResponse:
    """检查 EverMemOS 服务连通性"""
    config = config_loader.config
    evermemos_cfg = config.evermemos

    if not evermemos_cfg.enabled:
        return HealthCheckResponse(
            connected=False,
            message="EverMemOS 集成未启用",
            api_base_url=evermemos_cfg.api_base_url,
        )

    try:
        from backend.modules.evermemos.client import EverMemOSClient
        client = EverMemOSClient(
            api_base_url=evermemos_cfg.api_base_url,
            timeout=min(evermemos_cfg.timeout, 5),
        )
        ok = await client.health_check()
        return HealthCheckResponse(
            connected=ok,
            message="连接成功" if ok else "连接失败，请检查 EverMemOS 服务是否运行",
            api_base_url=evermemos_cfg.api_base_url,
        )
    except Exception as e:
        logger.warning(f"[EverMemOS] 健康检查异常: {e}")
        return HealthCheckResponse(
            connected=False,
            message=f"检查失败: {str(e)[:100]}",
            api_base_url=evermemos_cfg.api_base_url,
        )


@router.get("/config", response_model=EverMemOSConfigResponse)
async def get_evermemos_config() -> EverMemOSConfigResponse:
    """获取 EverMemOS 配置"""
    config = config_loader.config
    cfg = config.evermemos
    return EverMemOSConfigResponse(
        enabled=cfg.enabled,
        api_base_url=cfg.api_base_url,
        user_id=cfg.user_id,
        group_id=cfg.group_id,
        auto_memorize=cfg.auto_memorize,
        inject_memories=cfg.inject_memories,
        retrieval_limit=cfg.retrieval_limit,
        retrieval_mode=cfg.retrieval_mode,
        timeout=cfg.timeout,
    )


@router.put("/config", response_model=EverMemOSConfigResponse)
async def update_evermemos_config(
    request: UpdateEverMemOSConfigRequest,
) -> EverMemOSConfigResponse:
    """保存 EverMemOS 配置"""
    config = config_loader.config
    cfg = config.evermemos

    # 应用变更
    update_data = request.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(cfg, key, value)

    # 保存到数据库
    try:
        await config_loader.save_config(config)
        logger.info(f"[EverMemOS] 配置已保存: enabled={cfg.enabled}")
    except Exception as e:
        logger.exception(f"[EverMemOS] 保存配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")

    return EverMemOSConfigResponse(
        enabled=cfg.enabled,
        api_base_url=cfg.api_base_url,
        user_id=cfg.user_id,
        group_id=cfg.group_id,
        auto_memorize=cfg.auto_memorize,
        inject_memories=cfg.inject_memories,
        retrieval_limit=cfg.retrieval_limit,
        retrieval_mode=cfg.retrieval_mode,
        timeout=cfg.timeout,
    )


@router.post("/test", response_model=TestConnectionResponse)
async def test_evermemos_connection(
    request: TestConnectionRequest,
) -> TestConnectionResponse:
    """测试 EverMemOS 连接（使用指定的 URL，不需要已启用）"""
    try:
        from backend.modules.evermemos.client import EverMemOSClient
        client = EverMemOSClient(
            api_base_url=request.api_base_url,
            timeout=request.timeout,
        )
        ok = await client.health_check()
        return TestConnectionResponse(
            success=ok,
            message="连接成功" if ok else "无法连接到 EverMemOS 服务",
        )
    except Exception as e:
        logger.warning(f"[EverMemOS] 测试连接异常: {e}")
        return TestConnectionResponse(
            success=False,
            message=f"连接测试失败: {str(e)[:100]}",
        )


@router.get("/memories", response_model=MemoriesPreviewResponse)
async def preview_memories(
    query: Optional[str] = None,
    limit: int = 10,
) -> MemoriesPreviewResponse:
    """预览 EverMemOS 记忆（WebUI 展示用）"""
    config = config_loader.config
    cfg = config.evermemos

    if not cfg.enabled:
        return MemoriesPreviewResponse(
            success=False,
            memories=[],
            total=0,
            message="EverMemOS 集成未启用",
        )

    try:
        from backend.modules.evermemos.client import EverMemOSClient
        client = EverMemOSClient(
            api_base_url=cfg.api_base_url,
            timeout=cfg.timeout,
        )
        if query:
            memories = await client.search(
                user_id=cfg.user_id,
                query=query,
                group_id=cfg.group_id or None,
                limit=limit,
                retrieve_method=cfg.retrieval_mode,
            )
        else:
            memories = await client.get_memories(
                user_id=cfg.user_id,
                group_id=cfg.group_id or None,
                limit=limit,
            )
        return MemoriesPreviewResponse(
            success=True,
            memories=memories,
            total=len(memories),
        )
    except Exception as e:
        logger.warning(f"[EverMemOS] 预览记忆失败: {e}")
        return MemoriesPreviewResponse(
            success=False,
            memories=[],
            total=0,
            message=f"获取记忆失败: {str(e)[:100]}",
        )
