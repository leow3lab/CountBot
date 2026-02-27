"""EverMemOS HTTP 客户端

提供与 EverMemOS 记忆系统交互的异步 HTTP 客户端，支持：
- 写入对话记忆（POST /api/v1/memories）
- 语义检索记忆（GET /api/v1/memories/search）
- 获取记忆列表（GET /api/v1/memories）
- 服务健康检查（GET /api/v1/health）

容错设计：所有方法在 EverMemOS 不可用时静默降级，不影响主流程。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from loguru import logger


class EverMemOSClient:
    """EverMemOS HTTP 异步客户端"""

    def __init__(
        self,
        api_base_url: str = "http://localhost:1995",
        timeout: int = 10,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout

    def _now_iso(self) -> str:
        """返回当前 UTC 时间的 ISO 8601 字符串"""
        return datetime.now(timezone.utc).isoformat()

    async def health_check(self) -> bool:
        """检查 EverMemOS 服务是否可用

        Returns:
            True 表示服务可用，False 表示不可用
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.api_base_url}/api/v1/health")
                return resp.status_code < 500
        except Exception as e:
            logger.debug(f"[EverMemOS] 健康检查失败: {e}")
            return False

    async def memorize(
        self,
        user_id: str,
        role: str,
        content: str,
        group_id: Optional[str] = None,
        message_id: Optional[str] = None,
        create_time: Optional[str] = None,
        sender_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """写入单条消息到 EverMemOS 记忆系统

        Args:
            user_id: 发送方用户 ID
            role: 角色，"user" 或 "assistant"
            content: 消息内容
            group_id: 群组/空间 ID（可选）
            message_id: 消息 ID（可选，不传则自动生成）
            create_time: 消息创建时间 ISO 8601（可选，不传则使用当前时间）
            sender_name: 发送方显示名称（可选）

        Returns:
            EverMemOS 响应字典，失败时返回 {"success": False, "error": ...}
        """
        payload: dict[str, Any] = {
            "message_id": message_id or str(uuid.uuid4()),
            "create_time": create_time or self._now_iso(),
            "sender": user_id,
            "role": role,
            "content": content,
        }
        if group_id:
            payload["group_id"] = group_id
        if sender_name:
            payload["sender_name"] = sender_name

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_base_url}/api/v1/memories",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code in (200, 202):
                    return {"success": True, "data": resp.json()}
                else:
                    logger.warning(
                        f"[EverMemOS] memorize 失败 status={resp.status_code}: {resp.text[:200]}"
                    )
                    return {"success": False, "error": resp.text[:200]}
        except httpx.TimeoutException:
            logger.warning(f"[EverMemOS] memorize 请求超时 (user_id={user_id})")
            return {"success": False, "error": "timeout"}
        except Exception as e:
            logger.warning(f"[EverMemOS] memorize 请求异常: {e}")
            return {"success": False, "error": str(e)}

    async def search(
        self,
        user_id: str,
        query: str,
        group_id: Optional[str] = None,
        limit: int = 5,
        retrieve_method: str = "agentic",
    ) -> list[dict[str, Any]]:
        """语义检索 EverMemOS 记忆

        Args:
            user_id: 用户 ID
            query: 检索查询文本
            group_id: 群组/空间 ID（可选）
            limit: 返回记忆条数上限
            retrieve_method: 检索方式，agentic/hybrid/vector/keyword

        Returns:
            记忆列表，每条包含 content、memory_type、created_at 等字段；
            失败时返回空列表。
        """
        params: dict[str, Any] = {
            "user_id": user_id,
            "query": query,
            "top_k": limit,
            "retrieve_method": retrieve_method,
            "memory_types": ["episodic_memory", "event_log"],
            "include_metadata": True,
        }
        if group_id:
            params["group_id"] = group_id

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.api_base_url}/api/v1/memories/search",
                    params={
                        "user_id": user_id,
                        "query": query,
                        "top_k": limit,
                        "retrieve_method": retrieve_method,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # 提取记忆条目列表
                    return self._extract_memory_items(data)
                else:
                    logger.warning(
                        f"[EverMemOS] search 失败 status={resp.status_code}: {resp.text[:200]}"
                    )
                    return []
        except httpx.TimeoutException:
            logger.warning(f"[EverMemOS] search 请求超时 (user_id={user_id})")
            return []
        except Exception as e:
            logger.warning(f"[EverMemOS] search 请求异常: {e}")
            return []

    async def get_memories(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        memory_type: str = "episodic_memory",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """获取用户记忆列表（按时间排序）

        Args:
            user_id: 用户 ID
            group_id: 群组/空间 ID（可选）
            memory_type: 记忆类型
            limit: 返回条数上限

        Returns:
            记忆列表，失败时返回空列表
        """
        params: dict[str, Any] = {
            "user_id": user_id,
            "memory_type": memory_type,
            "limit": limit,
        }
        if group_id:
            params["group_id"] = group_id

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.api_base_url}/api/v1/memories",
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return self._extract_memory_items(data)
                else:
                    logger.warning(
                        f"[EverMemOS] get_memories 失败 status={resp.status_code}"
                    )
                    return []
        except Exception as e:
            logger.warning(f"[EverMemOS] get_memories 请求异常: {e}")
            return []

    def _extract_memory_items(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """从 EverMemOS 响应中提取记忆条目列表

        EverMemOS 实际响应结构:
          {"status": "ok", "result": {"memories": [...], ...}}
        也兼容:
          {"status": "success", "data": {"memories": [...], ...}}
        """
        try:
            # 优先取 "result"，再取 "data"，最后回退到整个 data
            inner = data.get("result") or data.get("data") or data
            if isinstance(inner, dict):
                memories = (
                    inner.get("memories")
                    or inner.get("results")
                    or inner.get("items")
                    or []
                )
                if isinstance(memories, list):
                    return memories
            if isinstance(inner, list):
                return inner
        except Exception:
            pass
        return []

    def format_memories_for_context(
        self,
        memories: list[dict[str, Any]],
        title: str = "EverMemOS 语义记忆",
    ) -> str:
        """将记忆列表格式化为系统提示词文本

        Args:
            memories: 记忆列表
            title: 段落标题

        Returns:
            格式化后的文本，为空时返回空字符串
        """
        if not memories:
            return ""

        items = []
        for i, mem in enumerate(memories, 1):
            content = (
                mem.get("content")
                or mem.get("summary")
                or mem.get("text")
                or str(mem)
            )
            if not isinstance(content, str):
                content = str(content)
            content = content.strip()
            if content:
                items.append(f"{i}. {content}")

        if not items:
            return ""

        joined = "\n".join(items)
        return f"## {title}\n\n以下是与本次对话相关的历史记忆（来自 EverMemOS）：\n\n{joined}"
