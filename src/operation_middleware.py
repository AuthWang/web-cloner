"""
操作中间件模块 - 提供统一的终端输出、操作追踪和状态管理
"""

import time
import logging
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading
from colorama import Fore, Style, Back
from tqdm import tqdm

logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """操作状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WARNING = "warning"


@dataclass
class OperationResult:
    """操作结果"""
    operation_id: str
    name: str
    status: OperationStatus
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    progress_current: int = 0
    progress_total: int = 0


class ProgressTracker:
    """进度追踪器"""

    def __init__(self, operation_id: str, name: str, total: int = 100):
        self.operation_id = operation_id
        self.name = name
        self.total = total
        self.current = 0
        self.pbar: Optional[tqdm] = None
        self.last_update_time = 0
        self.update_interval = 0.1  # 最小更新间隔（秒）

    def start(self):
        """开始进度追踪"""
        self.pbar = tqdm(
            total=self.total,
            desc=f"{Fore.CYAN}{self.name}{Style.RESET_ALL}",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )

    def update(self, n: int = 1, message: str = ""):
        """更新进度"""
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return

        self.current += n
        if self.pbar:
            self.pbar.update(n)
            if message:
                self.pbar.set_postfix_str(message)

        self.last_update_time = current_time

    def finish(self):
        """完成进度追踪"""
        if self.pbar:
            self.pbar.close()
            self.pbar = None


class OperationMiddleware:
    """操作中间件 - 提供统一的终端输出和操作监控"""

    def __init__(self):
        self.operations: Dict[str, OperationResult] = {}
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self.step_counters: Dict[str, int] = {}  # 步骤计数器
        self._lock = threading.Lock()

        # 统计信息
        self.stats = {
            'total_operations': 0,
            'successful': 0,
            'failed': 0,
            'cancelled': 0,
            'warnings': 0
        }

        # 配置
        self.show_progress = False  # 禁用进度条
        self.use_step_logging = True  # 启用步骤日志
        self.show_details = True
        self.color_output = True

    def operation(self,
                 name: str,
                 operation_id: Optional[str] = None,
                 show_progress: bool = True,
                 progress_total: int = 100,
                 catch_exceptions: bool = True) -> Callable:
        """操作装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                op_id = operation_id or f"{name}_{int(time.time() * 1000)}"

                with self.operation_context(op_id, name, show_progress, progress_total):
                    try:
                        # 执行函数
                        result = func(*args, **kwargs)

                        # 更新操作结果
                        self.update_operation(op_id, OperationStatus.SUCCESS,
                                            message=f"{name} 完成")

                        return result

                    except Exception as e:
                        if catch_exceptions:
                            # 捕获异常并记录
                            self.update_operation(op_id, OperationStatus.FAILED,
                                                message=f"{name} 失败: {str(e)}",
                                                error=e)
                            logger.error(f"操作失败: {name}, 错误: {e}")
                            raise
                        else:
                            # 重新抛出异常
                            self.update_operation(op_id, OperationStatus.FAILED,
                                                message=f"{name} 失败: {str(e)}",
                                                error=e)
                            raise

            return wrapper
        return decorator

    def async_operation(self,
                       name: str,
                       operation_id: Optional[str] = None,
                       show_progress: bool = True,
                       progress_total: int = 100,
                       catch_exceptions: bool = True) -> Callable:
        """异步操作装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                op_id = operation_id or f"{name}_{int(time.time() * 1000)}"

                with self.operation_context(op_id, name, show_progress, progress_total):
                    try:
                        # 执行异步函数
                        result = await func(*args, **kwargs)

                        # 更新操作结果
                        self.update_operation(op_id, OperationStatus.SUCCESS,
                                            message=f"{name} 完成")

                        return result

                    except Exception as e:
                        if catch_exceptions:
                            # 捕获异常并记录
                            self.update_operation(op_id, OperationStatus.FAILED,
                                                message=f"{name} 失败: {str(e)}",
                                                error=e)
                            logger.error(f"异步操作失败: {name}, 错误: {e}")
                            raise
                        else:
                            # 重新抛出异常
                            self.update_operation(op_id, OperationStatus.FAILED,
                                                message=f"{name} 失败: {str(e)}",
                                                error=e)
                            raise

            return wrapper
        return decorator

    @contextmanager
    def operation_context(self,
                         operation_id: str,
                         name: str,
                         show_progress: bool = True,
                         progress_total: int = 100):
        """操作上下文管理器"""
        # 开始操作
        self.start_operation(operation_id, name, show_progress, progress_total)

        try:
            yield operation_id
        except Exception as e:
            # 更新为失败状态
            self.update_operation(operation_id, OperationStatus.FAILED,
                                message=f"{name} 失败: {str(e)}",
                                error=e)
            raise
        finally:
            # 结束操作
            self.finish_operation(operation_id)

    def start_operation(self,
                       operation_id: str,
                       name: str,
                       show_progress: bool = True,
                       progress_total: int = 100):
        """开始操作"""
        with self._lock:
            # 创建操作记录
            operation = OperationResult(
                operation_id=operation_id,
                name=name,
                status=OperationStatus.RUNNING,
                start_time=time.time(),
                progress_total=progress_total
            )
            self.operations[operation_id] = operation

            # 创建进度追踪器
            if show_progress and self.show_progress:
                tracker = ProgressTracker(operation_id, name, progress_total)
                self.progress_trackers[operation_id] = tracker
                tracker.start()

            # 更新统计
            self.stats['total_operations'] += 1

        self._print_operation_start(operation)

    def update_operation(self,
                        operation_id: str,
                        status: OperationStatus,
                        message: str = "",
                        details: Optional[Dict[str, Any]] = None,
                        error: Optional[Exception] = None):
        """更新操作状态"""
        with self._lock:
            if operation_id not in self.operations:
                return

            operation = self.operations[operation_id]
            operation.status = status
            operation.message = message
            operation.error = error

            if details:
                operation.details.update(details)

            # 更新进度
            if status == OperationStatus.SUCCESS:
                operation.progress_current = operation.progress_total

            # 更新统计
            if status == OperationStatus.SUCCESS:
                self.stats['successful'] += 1
            elif status == OperationStatus.FAILED:
                self.stats['failed'] += 1
            elif status == OperationStatus.CANCELLED:
                self.stats['cancelled'] += 1
            elif status == OperationStatus.WARNING:
                self.stats['warnings'] += 1

        self._print_operation_update(operation)

    def update_progress(self, operation_id: str, current: int, message: str = ""):
        """更新操作进度（已弃用，建议使用 log_step）"""
        with self._lock:
            if operation_id in self.operations:
                self.operations[operation_id].progress_current = current

            # 如果启用步骤日志，转换为步骤日志
            if self.use_step_logging and message:
                self.log_step(operation_id, message, "INFO")
                return

            if operation_id in self.progress_trackers:
                tracker = self.progress_trackers[operation_id]
                progress = current - tracker.current
                if progress > 0:
                    tracker.update(progress, message)

    def log_step(self, operation_id: str, step: str, status: str = "INFO", details: str = "", emoji: str = ""):
        """输出操作步骤日志

        Args:
            operation_id: 操作ID
            step: 步骤描述
            status: 状态 (INFO, SUCCESS, WARNING, ERROR, PROGRESS)
            details: 详细信息
            emoji: 自定义emoji（可选）
        """
        # 步骤计数
        if operation_id not in self.step_counters:
            self.step_counters[operation_id] = 0

        self.step_counters[operation_id] += 1
        step_num = self.step_counters[operation_id]

        # 状态符号和颜色
        status_config = {
            'INFO': {'emoji': emoji or '→', 'color': Fore.CYAN},
            'SUCCESS': {'emoji': emoji or '✓', 'color': Fore.GREEN},
            'WARNING': {'emoji': emoji or '⚠', 'color': Fore.YELLOW},
            'ERROR': {'emoji': emoji or '✗', 'color': Fore.RED},
            'PROGRESS': {'emoji': emoji or '⋯', 'color': Fore.BLUE},
        }

        config = status_config.get(status, status_config['INFO'])
        emoji_symbol = config['emoji']
        color = config['color']

        # 输出步骤日志
        if not self.color_output:
            print(f"[{status}] {step}")
            if details:
                print(f"  {details}")
        else:
            # 步骤编号（可选）
            # step_prefix = f"{Fore.WHITE}[{step_num}]{Style.RESET_ALL} "

            print(f"{color}{emoji_symbol} {step}{Style.RESET_ALL}")

            if details:
                # 详细信息缩进显示
                for line in details.split('\n'):
                    if line.strip():
                        print(f"  {Fore.WHITE}{line}{Style.RESET_ALL}")

    def finish_operation(self, operation_id: str):
        """完成操作"""
        with self._lock:
            if operation_id not in self.operations:
                return

            operation = self.operations[operation_id]
            operation.end_time = time.time()
            operation.duration = operation.end_time - operation.start_time

            # 完成进度追踪
            if operation_id in self.progress_trackers:
                tracker = self.progress_trackers[operation_id]
                tracker.finish()
                del self.progress_trackers[operation_id]

        self._print_operation_finish(operation)

    def cancel_operation(self, operation_id: str, message: str = ""):
        """取消操作"""
        self.update_operation(operation_id, OperationStatus.CANCELLED, message)

    def get_operation(self, operation_id: str) -> Optional[OperationResult]:
        """获取操作信息"""
        with self._lock:
            return self.operations.get(operation_id)

    def get_all_operations(self) -> List[OperationResult]:
        """获取所有操作"""
        with self._lock:
            return list(self.operations.values())

    def get_running_operations(self) -> List[OperationResult]:
        """获取正在运行的操作"""
        with self._lock:
            return [op for op in self.operations.values() if op.status == OperationStatus.RUNNING]

    def clear_operations(self, older_than_seconds: Optional[float] = None):
        """清理操作记录"""
        current_time = time.time()

        with self._lock:
            if older_than_seconds is None:
                # 清理所有已完成的操作
                self.operations.clear()
            else:
                # 清理指定时间之前的操作
                to_remove = []
                for op_id, operation in self.operations.items():
                    if (operation.end_time and
                        current_time - operation.end_time > older_than_seconds):
                        to_remove.append(op_id)

                for op_id in to_remove:
                    del self.operations[op_id]

    def _print_operation_start(self, operation: OperationResult):
        """打印操作开始信息"""
        if not self.color_output:
            print(f"[��始] {operation.name}")
            return

        print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[开始] {operation.name}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")

    def _print_operation_update(self, operation: OperationResult):
        """打印操作更新信息"""
        if not operation.message:
            return

        if not self.color_output:
            print(f"[{operation.status.value.upper()}] {operation.message}")
            return

        status_colors = {
            OperationStatus.SUCCESS: Fore.GREEN,
            OperationStatus.FAILED: Fore.RED,
            OperationStatus.WARNING: Fore.YELLOW,
            OperationStatus.CANCELLED: Fore.CYAN,
            OperationStatus.RUNNING: Fore.BLUE,
        }

        color = status_colors.get(operation.status, Fore.WHITE)
        status_text = operation.status.value.upper()

        print(f"{color}[{status_text}] {operation.message}{Style.RESET_ALL}")

        if operation.error and self.show_details:
            print(f"{Fore.RED}  错误详情: {str(operation.error)}{Style.RESET_ALL}")

    def _print_operation_finish(self, operation: OperationResult):
        """打印操作完成信息"""
        if not self.color_output:
            if operation.duration:
                print(f"[完成] {operation.name} (耗时: {operation.duration:.2f}s)")
            else:
                print(f"[完成] {operation.name}")
            return

        status_colors = {
            OperationStatus.SUCCESS: Fore.GREEN,
            OperationStatus.FAILED: Fore.RED,
            OperationStatus.WARNING: Fore.YELLOW,
            OperationStatus.CANCELLED: Fore.CYAN,
        }

        color = status_colors.get(operation.status, Fore.WHITE)
        status_text = operation.status.value.upper()

        if operation.duration is not None:
            print(f"{color}[完成] {operation.name} (耗时: {operation.duration:.2f}s){Style.RESET_ALL}")
        else:
            print(f"{color}[完成] {operation.name}{Style.RESET_ALL}")

        # 显示详细信息
        if self.show_details and operation.details:
            print(f"{Fore.CYAN}  详细信息:{Style.RESET_ALL}")
            for key, value in operation.details.items():
                print(f"    {key}: {value}")

    def print_summary(self):
        """打印操作摘要"""
        with self._lock:
            running_count = len([op for op in self.operations.values() if op.status == OperationStatus.RUNNING])

        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[操作摘要]{Style.RESET_ALL}")
        print(f"  总操作数: {Fore.YELLOW}{self.stats['total_operations']}{Style.RESET_ALL}")
        print(f"  成功: {Fore.GREEN}{self.stats['successful']}{Style.RESET_ALL}")
        print(f"  失败: {Fore.RED}{self.stats['failed']}{Style.RESET_ALL}")
        print(f"  取消: {Fore.CYAN}{self.stats['cancelled']}{Style.RESET_ALL}")
        print(f"  警告: {Fore.YELLOW}{self.stats['warnings']}{Style.RESET_ALL}")
        print(f"  正在运行: {Fore.BLUE}{running_count}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    def print_running_operations(self):
        """打印正在运行的操作"""
        running_ops = self.get_running_operations()

        if not running_ops:
            return

        print(f"\n{Fore.CYAN}正在运行的操作:{Style.RESET_ALL}")
        for op in running_ops:
            elapsed = time.time() - op.start_time
            progress = f"{op.progress_current}/{op.progress_total}" if op.progress_total > 0 else "未知"
            print(f"  {Fore.YELLOW}{op.name}{Style.RESET_ALL} - 进度: {progress}, 耗时: {elapsed:.1f}s")


# 全局中间件实例
_global_middleware: Optional[OperationMiddleware] = None


def get_middleware() -> OperationMiddleware:
    """获取全局中间件实例"""
    global _global_middleware
    if _global_middleware is None:
        _global_middleware = OperationMiddleware()
    return _global_middleware


def operation(name: str, **kwargs) -> Callable:
    """便捷装饰器：操作"""
    middleware = get_middleware()
    return middleware.operation(name, **kwargs)


def async_operation(name: str, **kwargs) -> Callable:
    """便捷装饰器：异步操作"""
    middleware = get_middleware()
    return middleware.async_operation(name, **kwargs)


@contextmanager
def operation_context(name: str, **kwargs):
    """便捷上下文：操作"""
    middleware = get_middleware()
    operation_id = f"{name}_{int(time.time() * 1000)}"
    with middleware.operation_context(operation_id, name, **kwargs):
        yield operation_id