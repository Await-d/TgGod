"""启动管线工具

提供统一的启动阶段调度与回滚支持，确保各阶段职责清晰、日志一致。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional


Runner = Callable[[], Awaitable[None]] | Callable[[], None]
Rollback = Callable[[], Awaitable[None]] | Callable[[], None]


async def _maybe_await(func: Runner) -> None:
    """执行支持同步/异步的函数"""
    result = func()
    if asyncio.iscoroutine(result):
        await result


@dataclass
class StartupStage:
    """启动阶段定义"""

    name: str
    runner: Runner
    rollback: Optional[Rollback] = None
    description: Optional[str] = None


@dataclass
class StartupPipeline:
    """启动管线执行器"""

    stages: List[StartupStage]
    logger: Optional[object] = None
    _completed: List[StartupStage] = field(default_factory=list, init=False)

    async def run(self) -> None:
        """按顺序执行全部阶段"""
        self._completed.clear()

        for stage in self.stages:
            self._log("info", f"➡️ 启动阶段: {stage.name}")
            if stage.description:
                self._log("debug", stage.description)
            try:
                await _maybe_await(stage.runner)
                self._completed.append(stage)
                self._log("info", f"✅ 阶段完成: {stage.name}")
            except Exception as exc:  # noqa: BLE001
                self._log("error", f"❌ 阶段失败 {stage.name}: {exc}")
                await self._rollback()
                raise

    async def _rollback(self) -> None:
        """逆序执行已完成阶段的回滚"""
        for stage in reversed(self._completed):
            if not stage.rollback:
                continue
            try:
                self._log("warning", f"🔄 回滚阶段: {stage.name}")
                await _maybe_await(stage.rollback)
            except Exception as exc:  # noqa: BLE001
                self._log("error", f"⚠️ 回滚失败 {stage.name}: {exc}")

    def _log(self, level: str, message: str) -> None:
        if not self.logger:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message)
