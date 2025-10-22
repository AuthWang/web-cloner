"""
线程管理模块 - 负责异步任务和线程池的管理监控
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from colorama import Fore, Style

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    name: str
    status: str  # 'running', 'completed', 'failed', 'cancelled'
    start_time: float
    end_time: Optional[float] = None
    error: Optional[Exception] = None


class ThreadManager:
    """线程管理器 - 负责异步任务和线程池的监控管理"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        self.tasks: Dict[str, TaskInfo] = {}
        self.active_tasks: Dict[str, Future] = {}
        self.async_tasks: Dict[str, asyncio.Task] = {}
        self._lock = threading.Lock()
        self._shutdown = False

        logger.info(f"{Fore.CYAN}[ThreadManager] 初始化线程管理器，最大工作线程数: {max_workers}{Style.RESET_ALL}")

    def start(self):
        """启动线程管理器"""
        if self.thread_pool is None:
            self.thread_pool = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="WebCloner-"
            )
            logger.info(f"{Fore.GREEN}[ThreadManager] 线程池已启动{Style.RESET_ALL}")

    def stop(self, timeout: float = 30.0):
        """停止线程管理器"""
        logger.info(f"{Fore.YELLOW}[ThreadManager] 正在停止线程管理器...{Style.RESET_ALL}")

        self._shutdown = True

        # 取消所有异步任务
        self.cancel_all_async_tasks()

        # 关闭线程池
        if self.thread_pool:
            # Python 3.13 兼容：使用 threading.Event 实现超时控制
            try:
                # 创建一个线程来执行 shutdown，以便我们可以实现超时
                shutdown_complete = threading.Event()

                def do_shutdown():
                    try:
                        self.thread_pool.shutdown(wait=True)
                        shutdown_complete.set()
                    except Exception as e:
                        logger.warning(f"{Fore.YELLOW}[ThreadManager] 线程池关闭异常: {e}{Style.RESET_ALL}")
                        shutdown_complete.set()

                shutdown_thread = threading.Thread(target=do_shutdown, daemon=True)
                shutdown_thread.start()

                # 等待关闭完成或超时
                if shutdown_complete.wait(timeout=timeout):
                    logger.info(f"{Fore.GREEN}[ThreadManager] 线程池已正常关闭{Style.RESET_ALL}")
                else:
                    logger.warning(f"{Fore.YELLOW}[ThreadManager] 线程池关闭超时（{timeout}秒），继续执行...{Style.RESET_ALL}")
                    # 注意：在 Python 3.13 中，我们不能强制关闭，只能等待或继续

            except Exception as e:
                logger.warning(f"{Fore.YELLOW}[ThreadManager] 线程池关闭失败: {e}{Style.RESET_ALL}")

        # 清理任务记录
        with self._lock:
            self.tasks.clear()
            self.active_tasks.clear()
            self.async_tasks.clear()

        logger.info(f"{Fore.GREEN}[ThreadManager] 线程管理器已停止{Style.RESET_ALL}")

    def submit_thread_task(self, task_id: str, name: str, func: Callable, *args, **kwargs) -> Future:
        """提交线程任务"""
        if self._shutdown:
            raise RuntimeError("ThreadManager is shutdown")

        if not self.thread_pool:
            self.start()

        with self._lock:
            if task_id in self.active_tasks:
                raise ValueError(f"Task {task_id} already exists")

            # 记录任务信息
            task_info = TaskInfo(
                task_id=task_id,
                name=name,
                status='running',
                start_time=time.time()
            )
            self.tasks[task_id] = task_info

            # 提交任务
            future = self.thread_pool.submit(self._wrap_thread_task, task_id, func, *args, **kwargs)
            self.active_tasks[task_id] = future

        logger.info(f"{Fore.CYAN}[ThreadManager] 提交线程任务: {name} (ID: {task_id}){Style.RESET_ALL}")
        return future

    def submit_async_task(self, task_id: str, name: str, coro) -> asyncio.Task:
        """提交异步任务"""
        if self._shutdown:
            raise RuntimeError("ThreadManager is shutdown")

        with self._lock:
            if task_id in self.async_tasks:
                raise ValueError(f"Async task {task_id} already exists")

            # 记录任务信息
            task_info = TaskInfo(
                task_id=task_id,
                name=name,
                status='running',
                start_time=time.time()
            )
            self.tasks[task_id] = task_info

            # 创建异步任务
            task = asyncio.create_task(self._wrap_async_task(task_id, coro))
            self.async_tasks[task_id] = task

        logger.info(f"{Fore.CYAN}[ThreadManager] 提交异步任务: {name} (ID: {task_id}){Style.RESET_ALL}")
        return task

    def _wrap_thread_task(self, task_id: str, func: Callable, *args, **kwargs):
        """包装线程任务，添加状态跟踪"""
        try:
            result = func(*args, **kwargs)
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = 'completed'
                    self.tasks[task_id].end_time = time.time()
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

            logger.debug(f"{Fore.GREEN}[ThreadManager] 线程任务完成: {task_id}{Style.RESET_ALL}")
            return result

        except Exception as e:
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = 'failed'
                    self.tasks[task_id].end_time = time.time()
                    self.tasks[task_id].error = e
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

            logger.error(f"{Fore.RED}[ThreadManager] 线程任务失败: {task_id}, 错误: {e}{Style.RESET_ALL}")
            raise

    async def _wrap_async_task(self, task_id: str, coro):
        """包装异步任务，添加状态跟踪"""
        try:
            result = await coro
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = 'completed'
                    self.tasks[task_id].end_time = time.time()
                if task_id in self.async_tasks:
                    del self.async_tasks[task_id]

            logger.debug(f"{Fore.GREEN}[ThreadManager] 异步任务完成: {task_id}{Style.RESET_ALL}")
            return result

        except asyncio.CancelledError:
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = 'cancelled'
                    self.tasks[task_id].end_time = time.time()
                if task_id in self.async_tasks:
                    del self.async_tasks[task_id]

            logger.info(f"{Fore.YELLOW}[ThreadManager] 异步任务被取消: {task_id}{Style.RESET_ALL}")
            raise

        except Exception as e:
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = 'failed'
                    self.tasks[task_id].end_time = time.time()
                    self.tasks[task_id].error = e
                if task_id in self.async_tasks:
                    del self.async_tasks[task_id]

            logger.error(f"{Fore.RED}[ThreadManager] 异步任务失败: {task_id}, 错误: {e}{Style.RESET_ALL}")
            raise

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        cancelled = False

        # 取消线程任务
        with self._lock:
            if task_id in self.active_tasks:
                future = self.active_tasks[task_id]
                cancelled = future.cancel()
                if cancelled:
                    self.tasks[task_id].status = 'cancelled'
                    self.tasks[task_id].end_time = time.time()
                    del self.active_tasks[task_id]

        # 取消异步任务
        with self._lock:
            if task_id in self.async_tasks:
                task = self.async_tasks[task_id]
                cancelled = task.cancel()
                if cancelled:
                    self.tasks[task_id].status = 'cancelled'
                    self.tasks[task_id].end_time = time.time()
                    del self.async_tasks[task_id]

        if cancelled:
            logger.info(f"{Fore.YELLOW}[ThreadManager] 任务已取消: {task_id}{Style.RESET_ALL}")

        return cancelled

    def cancel_all_async_tasks(self):
        """取消所有异步任务"""
        with self._lock:
            task_ids = list(self.async_tasks.keys())

        for task_id in task_ids:
            self.cancel_task(task_id)

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """等待任务完成"""
        with self._lock:
            if task_id in self.active_tasks:
                future = self.active_tasks[task_id]
            elif task_id in self.async_tasks:
                raise ValueError("Use await for async tasks")
            else:
                raise ValueError(f"Task {task_id} not found")

        try:
            return future.result(timeout=timeout)
        except Exception as e:
            logger.error(f"{Fore.RED}[ThreadManager] 等待任务失败: {task_id}, 错误: {e}{Style.RESET_ALL}")
            raise

    async def wait_for_async_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """等待异步任务完成"""
        with self._lock:
            if task_id in self.async_tasks:
                task = self.async_tasks[task_id]
            else:
                raise ValueError(f"Async task {task_id} not found")

        try:
            if timeout:
                return await asyncio.wait_for(task, timeout=timeout)
            else:
                return await task
        except Exception as e:
            logger.error(f"{Fore.RED}[ThreadManager] 等待异步任务失败: {task_id}, 错误: {e}{Style.RESET_ALL}")
            raise

    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务状态"""
        with self._lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[TaskInfo]:
        """获取所有任务信息"""
        with self._lock:
            return list(self.tasks.values())

    def get_active_tasks_count(self) -> int:
        """获取活跃任务数量"""
        with self._lock:
            return len(self.active_tasks) + len(self.async_tasks)

    def print_status(self):
        """打印当前状态"""
        tasks = self.get_all_tasks()
        active_count = self.get_active_tasks_count()

        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[ThreadManager] 线程管理器状态{Style.RESET_ALL}")
        print(f"  活跃任务数: {Fore.YELLOW}{active_count}{Style.RESET_ALL}")
        print(f"  总任务数: {Fore.GREEN}{len(tasks)}{Style.RESET_ALL}")

        # 按状态分类统计
        status_count = {}
        for task in tasks:
            status_count[task.status] = status_count.get(task.status, 0) + 1

        print(f"  任务状态:")
        for status, count in status_count.items():
            color = {
                'running': Fore.YELLOW,
                'completed': Fore.GREEN,
                'failed': Fore.RED,
                'cancelled': Fore.CYAN
            }.get(status, Fore.WHITE)
            print(f"    {color}{status}: {count}{Style.RESET_ALL}")

        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")


# 全局线程管理器实例
_global_thread_manager: Optional[ThreadManager] = None


def get_thread_manager() -> ThreadManager:
    """获取全局线程管理器实例"""
    global _global_thread_manager
    if _global_thread_manager is None:
        _global_thread_manager = ThreadManager()
    return _global_thread_manager


def shutdown_thread_manager():
    """关闭全局线程管理器"""
    global _global_thread_manager
    if _global_thread_manager is not None:
        _global_thread_manager.stop()
        _global_thread_manager = None