"""
内存管理模块 - 负责内存监控、垃圾回收和缓存清理
"""

import gc
import os
import time
import threading
import psutil
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
import weakref
from colorama import Fore, Style

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """内存快照"""
    timestamp: float
    rss_mb: float  # 物理内存
    vms_mb: float  # 虚拟内存
    percent: float  # 内存使用百分比
    gc_counts: tuple  # GC 回收计数
    objects_count: int  # Python 对象数量


@dataclass
class MemoryThreshold:
    """内存阈值配置"""
    warning_percent: float = 80.0
    critical_percent: float = 90.0
    max_objects_growth: int = 100000  # 对象增长阈值
    gc_threshold: float = 70.0  # 触发垃圾回收的内存百分比


class MemoryManager:
    """内存管理器 - 负责内存监控、垃圾回收和缓存清理"""

    def __init__(self, threshold: Optional[MemoryThreshold] = None, check_interval: float = 30.0):
        self.threshold = threshold or MemoryThreshold()
        self.check_interval = check_interval

        # 监控状态
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 内存历史记录
        self.snapshots: List[MemorySnapshot] = []
        self.max_snapshots = 100

        # 回调函数
        self.warning_callbacks: List[Callable] = []
        self.critical_callbacks: List[Callable] = []
        self.cleanup_callbacks: List[Callable] = []

        # 统计信息
        self.gc_stats = defaultdict(int)
        self.cleanup_stats = defaultdict(int)

        # 缓存管理
        self.caches: Dict[str, Any] = {}
        self.cache_limits: Dict[str, int] = {}

        # 弱引用追踪
        self.tracked_objects: Dict[str, List[weakref.ref]] = defaultdict(list)

        logger.info(f"{Fore.CYAN}[MemoryManager] 初始化内存管理器，检查间隔: {check_interval}s{Style.RESET_ALL}")

    def start_monitoring(self):
        """开始内存监控"""
        if self._monitoring:
            logger.warning(f"{Fore.YELLOW}[MemoryManager] 内存监控已在运行{Style.RESET_ALL}")
            return

        self._monitoring = True
        self._stop_event.clear()

        # 创建初始快照
        self._create_snapshot()

        # 启动监控线程
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="MemoryMonitor",
            daemon=True
        )
        self._monitor_thread.start()

        logger.info(f"{Fore.GREEN}[MemoryManager] 内存监控已启动{Style.RESET_ALL}")

    def stop_monitoring(self):
        """停止内存监控"""
        if not self._monitoring:
            return

        logger.info(f"{Fore.YELLOW}[MemoryManager] 正在停止内存监控...{Style.RESET_ALL}")

        self._monitoring = False
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=10)

        logger.info(f"{Fore.GREEN}[MemoryManager] 内存监控已停止{Style.RESET_ALL}")

    def _monitor_loop(self):
        """监控循环"""
        while not self._stop_event.wait(self.check_interval):
            try:
                self._check_memory()
                self._create_snapshot()

                # 清理过期快照
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots = self.snapshots[-self.max_snapshots:]

            except Exception as e:
                logger.error(f"{Fore.RED}[MemoryManager] 内存监控错误: {e}{Style.RESET_ALL}")

    def _create_snapshot(self):
        """创建内存快照"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=process.memory_percent(),
                gc_counts=gc.get_count() if hasattr(gc, 'get_count') else (0, 0, 0),
                objects_count=len(gc.get_objects()) if hasattr(gc, 'get_objects') else 0
            )

            self.snapshots.append(snapshot)

        except Exception as e:
            logger.warning(f"{Fore.YELLOW}[MemoryManager] 创建内存快照失败: {e}{Style.RESET_ALL}")

    def _check_memory(self):
        """检查内存状态"""
        if not self.snapshots:
            return

        current = self.snapshots[-1]
        memory_percent = current.percent

        # 检查内存阈值
        if memory_percent >= self.threshold.critical_percent:
            logger.error(f"{Fore.RED}[MemoryManager] 内存使用率危险: {memory_percent:.1f}%{Style.RESET_ALL}")
            self._trigger_critical_callbacks()

            # 强制垃圾回收
            self.force_garbage_collection()

            # 清理缓存
            self.cleanup_all_caches()

        elif memory_percent >= self.threshold.warning_percent:
            logger.warning(f"{Fore.YELLOW}[MemoryManager] 内存使用率警告: {memory_percent:.1f}%{Style.RESET_ALL}")
            self._trigger_warning_callbacks()

            # 触发垃圾回收
            if memory_percent >= self.threshold.gc_threshold:
                self.trigger_garbage_collection()

        # 检查对象增长
        if len(self.snapshots) >= 2:
            prev = self.snapshots[-2]
            objects_growth = current.objects_count - prev.objects_count

            if objects_growth > self.threshold.max_objects_growth:
                logger.warning(f"{Fore.YELLOW}[MemoryManager] 对象数量快速增长: +{objects_growth}{Style.RESET_ALL}")
                self.trigger_garbage_collection()

    def trigger_garbage_collection(self, generation: Optional[int] = None):
        """触发垃圾回收"""
        try:
            before_counts = gc.get_count() if hasattr(gc, 'get_count') else (0, 0, 0)

            if generation is not None:
                collected = gc.collect(generation)
            else:
                collected = gc.collect()

            after_counts = gc.get_count() if hasattr(gc, 'get_count') else (0, 0, 0)

            self.gc_stats['collections'] += 1
            self.gc_stats['objects_collected'] += collected

            logger.debug(f"{Fore.GREEN}[MemoryManager] 垃圾回收完成: 回收 {collected} 个对象{Style.RESET_ALL}")

            return collected

        except Exception as e:
            logger.error(f"{Fore.RED}[MemoryManager] 垃圾回收失败: {e}{Style.RESET_ALL}")
            return 0

    def force_garbage_collection(self):
        """强制完整的垃圾回收"""
        logger.info(f"{Fore.CYAN}[MemoryManager] 执行强制垃圾回收...{Style.RESET_ALL}")

        total_collected = 0
        for generation in range(3):
            collected = self.trigger_garbage_collection(generation)
            total_collected += collected

        logger.info(f"{Fore.GREEN}[MemoryManager] 强制垃圾回收完成: 总共回收 {total_collected} 个对象{Style.RESET_ALL}")
        return total_collected

    def add_cache(self, name: str, cache: Any, limit: Optional[int] = None):
        """添加缓存管理"""
        self.caches[name] = cache
        if limit is not None:
            self.cache_limits[name] = limit

        logger.debug(f"{Fore.CYAN}[MemoryManager] 添加缓存: {name}, 限制: {limit}{Style.RESET_ALL}")

    def cleanup_cache(self, name: str) -> int:
        """清理指定缓存"""
        if name not in self.caches:
            return 0

        cache = self.caches[name]
        cleaned_count = 0

        try:
            if hasattr(cache, 'clear'):
                # 字典或集合类型
                size_before = len(cache)
                cache.clear()
                cleaned_count = size_before

            elif hasattr(cache, '__len__') and hasattr(cache, '__delitem__'):
                # 列表或其他序列
                size_before = len(cache)
                if name in self.cache_limits and size_before > self.cache_limits[name]:
                    # 保留最近的一部分
                    keep_count = self.cache_limits[name] // 2
                    del cache[:-keep_count]
                    cleaned_count = size_before - len(cache)
                else:
                    cache.clear()
                    cleaned_count = size_before

            elif callable(cache):
                # 自定义清理函数
                cleaned_count = cache()

            self.cleanup_stats[f'cache_{name}'] += cleaned_count
            logger.debug(f"{Fore.GREEN}[MemoryManager] 缓存清理完成: {name}, 清理 {cleaned_count} 项{Style.RESET_ALL}")

        except Exception as e:
            logger.error(f"{Fore.RED}[MemoryManager] 缓存清理失败: {name}, 错误: {e}{Style.RESET_ALL}")

        return cleaned_count

    def cleanup_all_caches(self) -> int:
        """清理所有缓存"""
        total_cleaned = 0

        for name in list(self.caches.keys()):
            cleaned = self.cleanup_cache(name)
            total_cleaned += cleaned

        logger.info(f"{Fore.GREEN}[MemoryManager] 所有缓存清理完成: 总共清理 {total_cleaned} 项{Style.RESET_ALL}")
        return total_cleaned

    def track_object(self, name: str, obj: Any):
        """追踪对象（弱引用）"""
        def cleanup_callback(ref):
            if name in self.tracked_objects and ref in self.tracked_objects[name]:
                self.tracked_objects[name].remove(ref)

        weak_ref = weakref.ref(obj, cleanup_callback)
        self.tracked_objects[name].append(weak_ref)

        # 清理失效的弱引用
        self.tracked_objects[name] = [ref for ref in self.tracked_objects[name] if ref() is not None]

    def get_tracked_objects_count(self, name: str) -> int:
        """获取追踪对象数量"""
        if name not in self.tracked_objects:
            return 0
        return len([ref for ref in self.tracked_objects[name] if ref() is not None])

    def get_current_memory_info(self) -> Dict[str, float]:
        """获取当前内存信息"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"{Fore.RED}[MemoryManager] 获取内存信息失败: {e}{Style.RESET_ALL}")
            return {}

    def get_memory_trend(self, window_size: int = 10) -> Dict[str, float]:
        """获取内存使用趋势"""
        if len(self.snapshots) < 2:
            return {}

        recent_snapshots = self.snapshots[-window_size:]
        if len(recent_snapshots) < 2:
            return {}

        # 计算趋势
        time_span = recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp
        if time_span <= 0:
            return {}

        rss_change = recent_snapshots[-1].rss_mb - recent_snapshots[0].rss_mb
        objects_change = recent_snapshots[-1].objects_count - recent_snapshots[0].objects_count

        return {
            'rss_trend_mb_per_min': (rss_change / time_span) * 60,
            'objects_trend_per_min': (objects_change / time_span) * 60,
            'time_span_minutes': time_span / 60
        }

    def add_warning_callback(self, callback: Callable):
        """添加内存警告回调"""
        self.warning_callbacks.append(callback)

    def add_critical_callback(self, callback: Callable):
        """添加内存危险回调"""
        self.critical_callbacks.append(callback)

    def add_cleanup_callback(self, callback: Callable):
        """添加清理回调"""
        self.cleanup_callbacks.append(callback)

    def _trigger_warning_callbacks(self):
        """触发警告回调"""
        for callback in self.warning_callbacks:
            try:
                callback(self.get_current_memory_info())
            except Exception as e:
                logger.error(f"{Fore.RED}[MemoryManager] 警告回调执行失败: {e}{Style.RESET_ALL}")

    def _trigger_critical_callbacks(self):
        """触发危险回调"""
        for callback in self.critical_callbacks:
            try:
                callback(self.get_current_memory_info())
            except Exception as e:
                logger.error(f"{Fore.RED}[MemoryManager] 危险回调执行失败: {e}{Style.RESET_ALL}")

    def print_memory_status(self):
        """打印内存状态"""
        current_info = self.get_current_memory_info()
        trend = self.get_memory_trend()

        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[MemoryManager] 内存状态{Style.RESET_ALL}")

        if current_info:
            print(f"  物理内存: {Fore.GREEN}{current_info.get('rss_mb', 0):.1f}MB{Style.RESET_ALL}")
            print(f"  虚拟内存: {Fore.YELLOW}{current_info.get('vms_mb', 0):.1f}MB{Style.RESET_ALL}")
            print(f"  使用率: {Fore.CYAN}{current_info.get('percent', 0):.1f}%{Style.RESET_ALL}")
            print(f"  可用内存: {Fore.GREEN}{current_info.get('available_mb', 0):.1f}MB{Style.RESET_ALL}")

        if trend:
            print(f"  内存趋势: {Fore.CYAN}{trend.get('rss_trend_mb_per_min', 0):+.1f}MB/min{Style.RESET_ALL}")
            print(f"  对象趋势: {Fore.CYAN}{trend.get('objects_trend_per_min', 0):+.0f}个/min{Style.RESET_ALL}")

        print(f"  垃圾回收: {Fore.GREEN}{self.gc_stats.get('collections', 0)} 次{Style.RESET_ALL}")
        print(f"  回收对象: {Fore.GREEN}{self.gc_stats.get('objects_collected', 0)} 个{Style.RESET_ALL}")

        # 缓存状态
        if self.caches:
            print(f"  缓存数量: {Fore.YELLOW}{len(self.caches)} 个{Style.RESET_ALL}")
            for name, cache in self.caches.items():
                size = len(cache) if hasattr(cache, '__len__') else '?'
                limit = self.cache_limits.get(name, '∞')
                print(f"    {name}: {Fore.GREEN}{size}{Style.RESET_ALL}/{limit}")

        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

    def __del__(self):
        """析构函数"""
        try:
            self.stop_monitoring()
        except:
            pass


# 全局内存管理器实例
_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """获取全局内存管理器实例"""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager


def start_memory_monitoring():
    """启动内存监控"""
    manager = get_memory_manager()
    manager.start_monitoring()


def stop_memory_monitoring():
    """停止内存监控"""
    global _global_memory_manager
    if _global_memory_manager is not None:
        _global_memory_manager.stop_monitoring()