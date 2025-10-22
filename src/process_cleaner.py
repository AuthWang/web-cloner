"""
进程清理模块 - 负责跨平台进程清理和浏览器进程管理
"""

import os
import platform
import subprocess
import time
import signal
import logging
import psutil
from typing import List, Dict, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from colorama import Fore, Style

logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """进程信息"""
    pid: int
    name: str
    cmdline: List[str]
    status: str
    create_time: float
    cpu_percent: float
    memory_mb: float


class ProcessCleaner:
    """进程清理器 - 负责跨平台进程清理和浏览器进程管理"""

    def __init__(self):
        self.system = platform.system()
        self.cleaned_processes: Set[int] = set()
        self.managed_pids: Set[int] = set()  # PID 白名单：只清理我们启动的进程
        self.browser_process_names = self._get_browser_process_names()

        logger.info(f"{Fore.CYAN}[ProcessCleaner] 初始化进程清理器，系统: {self.system}{Style.RESET_ALL}")

    def register_process(self, pid: int, description: str = ""):
        """注册进程 PID 到白名单"""
        self.managed_pids.add(pid)
        logger.info(f"{Fore.GREEN}[ProcessCleaner] 注册进程 PID {pid}: {description}{Style.RESET_ALL}")

    def unregister_process(self, pid: int):
        """从白名单中移除进程 PID"""
        if pid in self.managed_pids:
            self.managed_pids.remove(pid)
            logger.info(f"{Fore.CYAN}[ProcessCleaner] 注销进程 PID {pid}{Style.RESET_ALL}")

    def is_managed_process(self, pid: int) -> bool:
        """检查进程是否在白名单中"""
        return pid in self.managed_pids

    def _get_browser_process_names(self) -> List[str]:
        """获取浏览器进程名称列表"""
        names = []
        if self.system == "Windows":
            names.extend(['chrome.exe', 'msedge.exe', 'chromium.exe'])
        elif self.system == "Darwin":  # macOS
            names.extend(['Google Chrome', 'Microsoft Edge', 'Chromium'])
        else:  # Linux
            names.extend(['chrome', 'google-chrome', 'msedge', 'chromium', 'chromium-browser'])
        return names

    def get_browser_processes(self) -> List[ProcessInfo]:
        """获取所有浏览器进程"""
        processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'create_time', 'cpu_percent', 'memory_info']):
                try:
                    process_info = proc.info
                    process_name = process_info['name']

                    # 检查是否是浏览器进程
                    if any(browser_name.lower() in process_name.lower() for browser_name in self.browser_process_names):
                        memory_mb = process_info['memory_info'].rss / 1024 / 1024 if process_info['memory_info'] else 0

                        proc_info = ProcessInfo(
                            pid=process_info['pid'],
                            name=process_name,
                            cmdline=process_info['cmdline'] or [],
                            status=process_info['status'],
                            create_time=process_info['create_time'],
                            cpu_percent=process_info['cpu_percent'] or 0,
                            memory_mb=memory_mb
                        )
                        processes.append(proc_info)

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        except Exception as e:
            logger.error(f"{Fore.RED}[ProcessCleaner] 获取进程列表失败: {e}{Style.RESET_ALL}")

        return processes

    def get_playwright_processes(self) -> List[ProcessInfo]:
        """获取 Playwright 相关进程"""
        processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'create_time']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('playwright' in str(cmd).lower() for cmd in cmdline):
                        proc_info = ProcessInfo(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            cmdline=cmdline,
                            status=proc.info['status'],
                            create_time=proc.info['create_time'],
                            cpu_percent=0,
                            memory_mb=0
                        )
                        processes.append(proc_info)

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        except Exception as e:
            logger.error(f"{Fore.RED}[ProcessCleaner] 获取 Playwright 进程失败: {e}{Style.RESET_ALL}")

        return processes

    def is_process_running(self, pid: int) -> bool:
        """检查进程是否正在运行"""
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False

    def terminate_process_gracefully(self, pid: int, timeout: float = 10.0) -> bool:
        """优雅地终止进程"""
        try:
            if not psutil.pid_exists(pid):
                logger.debug(f"{Fore.YELLOW}[ProcessCleaner] 进程 {pid} 不存在{Style.RESET_ALL}")
                return True

            process = psutil.Process(pid)
            process_name = process.name()

            logger.info(f"{Fore.CYAN}[ProcessCleaner] 正在优雅终止进程: {process_name} (PID: {pid}){Style.RESET_ALL}")

            # 首先尝试 SIGTERM
            process.terminate()

            # 等待进程结束
            try:
                process.wait(timeout=timeout)
                logger.info(f"{Fore.GREEN}[ProcessCleaner] 进程已优雅终止: {process_name} (PID: {pid}){Style.RESET_ALL}")
                self.cleaned_processes.add(pid)
                return True
            except psutil.TimeoutExpired:
                logger.warning(f"{Fore.YELLOW}[ProcessCleaner] 进程优雅终止超时，将强制终止: {process_name} (PID: {pid}){Style.RESET_ALL}")
                return self.terminate_process_forcefully(pid)

        except psutil.NoSuchProcess:
            logger.debug(f"{Fore.YELLOW}[ProcessCleaner] 进程 {pid} 已终止{Style.RESET_ALL}")
            return True
        except psutil.AccessDenied:
            logger.error(f"{Fore.RED}[ProcessCleaner] 没有权限终止进程 {pid}{Style.RESET_ALL}")
            return False
        except Exception as e:
            logger.error(f"{Fore.RED}[ProcessCleaner] 终止进程失败 {pid}: {e}{Style.RESET_ALL}")
            return False

    def terminate_process_forcefully(self, pid: int) -> bool:
        """强制终止进程"""
        try:
            if not psutil.pid_exists(pid):
                return True

            process = psutil.Process(pid)
            process_name = process.name()

            logger.info(f"{Fore.YELLOW}[ProcessCleaner] 正在强制终止进程: {process_name} (PID: {pid}){Style.RESET_ALL}")

            # 使用 SIGKILL
            if self.system == "Windows":
                process.kill()
            else:
                process.send_signal(signal.SIGKILL)

            # 等待进程结束
            try:
                process.wait(timeout=5)
                logger.info(f"{Fore.GREEN}[ProcessCleaner] 进程已强制终止: {process_name} (PID: {pid}){Style.RESET_ALL}")
                self.cleaned_processes.add(pid)
                return True
            except psutil.TimeoutExpired:
                logger.error(f"{Fore.RED}[ProcessCleaner] 强制终止进程失败: {process_name} (PID: {pid}){Style.RESET_ALL}")
                return False

        except psutil.NoSuchProcess:
            return True
        except psutil.AccessDenied:
            logger.error(f"{Fore.RED}[ProcessCleaner] 没有权限强制终止进程 {pid}{Style.RESET_ALL}")
            return False
        except Exception as e:
            logger.error(f"{Fore.RED}[ProcessCleaner] 强制终止进程失败 {pid}: {e}{Style.RESET_ALL}")
            return False

    def terminate_browser_processes(self, force: bool = False, only_managed: bool = True) -> Dict[str, int]:
        """终止浏览器进程

        Args:
            force: 是否强制终止
            only_managed: 是否只清理白名单中的进程（默认 True，更安全）
        """
        browser_processes = self.get_browser_processes()
        terminated_count = 0
        forced_count = 0
        skipped_count = 0

        logger.info(f"{Fore.CYAN}[ProcessCleaner] 发现 {len(browser_processes)} 个浏览器进程{Style.RESET_ALL}")

        for proc_info in browser_processes:
            if proc_info.pid in self.cleaned_processes:
                continue

            # 安全检查：只清理白名单中的进程
            if only_managed and not self.is_managed_process(proc_info.pid):
                logger.debug(f"{Fore.YELLOW}[ProcessCleaner] 跳过非托管进程: {proc_info.name} (PID: {proc_info.pid}){Style.RESET_ALL}")
                skipped_count += 1
                continue

            if force:
                if self.terminate_process_forcefully(proc_info.pid):
                    forced_count += 1
            else:
                if self.terminate_process_gracefully(proc_info.pid):
                    terminated_count += 1

        result = {
            'total': len(browser_processes),
            'terminated': terminated_count,
            'forced': forced_count,
            'skipped': skipped_count
        }

        if only_managed:
            logger.info(f"{Fore.GREEN}[ProcessCleaner] 浏览器进程安全清理完成: 终止 {terminated_count} 个, 跳过 {skipped_count} 个非托管进程{Style.RESET_ALL}")
        else:
            logger.warning(f"{Fore.YELLOW}[ProcessCleaner] 浏览器进程全部清理: 终止 {terminated_count} 个{Style.RESET_ALL}")

        return result

    def terminate_playwright_processes(self, force: bool = False) -> Dict[str, int]:
        """终止所有 Playwright 相关进程"""
        playwright_processes = self.get_playwright_processes()
        terminated_count = 0
        forced_count = 0

        logger.info(f"{Fore.CYAN}[ProcessCleaner] 发现 {len(playwright_processes)} 个 Playwright 进程{Style.RESET_ALL}")

        for proc_info in playwright_processes:
            if proc_info.pid in self.cleaned_processes:
                continue

            if force:
                if self.terminate_process_forcefully(proc_info.pid):
                    forced_count += 1
            else:
                if self.terminate_process_gracefully(proc_info.pid):
                    terminated_count += 1

        result = {
            'total': len(playwright_processes),
            'terminated': terminated_count,
            'forced': forced_count
        }

        logger.info(f"{Fore.GREEN}[ProcessCleaner] Playwright 进程清理完成: 终止 {terminated_count} 个, 强制 {forced_count} 个{Style.RESET_ALL}")
        return result

    def cleanup_temp_files(self, temp_dirs: Optional[List[Path]] = None) -> Dict[str, int]:
        """清理临时文件"""
        if temp_dirs is None:
            temp_dirs = [
                Path.home() / '.playwright' / 'user-data',
                Path.home() / '.cache' / 'ms-playwright',
                Path.cwd() / 'browser-data',
                Path.cwd() / '.temp'
            ]

        cleaned_files = 0
        cleaned_dirs = 0

        for temp_dir in temp_dirs:
            if not temp_dir.exists():
                continue

            try:
                # 清理文件
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            cleaned_files += 1
                        except (PermissionError, OSError):
                            continue

                # 清理空目录
                for dir_path in sorted(temp_dir.rglob('*'), reverse=True):
                    if dir_path.is_dir():
                        try:
                            if not any(dir_path.iterdir()):
                                dir_path.rmdir()
                                cleaned_dirs += 1
                        except (PermissionError, OSError):
                            continue

                # 尝试删除根目录
                try:
                    if not any(temp_dir.iterdir()):
                        temp_dir.rmdir()
                        cleaned_dirs += 1
                except (PermissionError, OSError):
                    pass

            except Exception as e:
                logger.warning(f"{Fore.YELLOW}[ProcessCleaner] 清理临时目录失败 {temp_dir}: {e}{Style.RESET_ALL}")

        result = {
            'files': cleaned_files,
            'dirs': cleaned_dirs
        }

        logger.info(f"{Fore.GREEN}[ProcessCleaner] 临时文件清理完成: {cleaned_files} 个文件, {cleaned_dirs} 个目录{Style.RESET_ALL}")
        return result

    def cleanup_all(self, force: bool = False) -> Dict[str, any]:
        """执行完整的清理操作"""
        logger.info(f"{Fore.CYAN}[ProcessCleaner] 开始执行完整清理...{Style.RESET_ALL}")

        results = {
            'browser_processes': self.terminate_browser_processes(force=force),
            'playwright_processes': self.terminate_playwright_processes(force=force),
            'temp_files': self.cleanup_temp_files()
        }

        total_processes = results['browser_processes']['total'] + results['playwright_processes']['total']
        total_terminated = results['browser_processes']['terminated'] + results['playwright_processes']['terminated']
        total_forced = results['browser_processes']['forced'] + results['playwright_processes']['forced']

        logger.info(f"{Fore.GREEN}[ProcessCleaner] 完整清理完成: {total_processes} 个进程, {total_terminated} 个终止, {total_forced} 个强制{Style.RESET_ALL}")

        return results

    def print_process_status(self):
        """打印进程状态"""
        browser_processes = self.get_browser_processes()
        playwright_processes = self.get_playwright_processes()

        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[ProcessCleaner] 进程状态{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}浏览器进程 ({len(browser_processes)} 个):{Style.RESET_ALL}")
        if browser_processes:
            for proc in browser_processes:
                print(f"  PID: {Fore.GREEN}{proc.pid}{Style.RESET_ALL} | "
                      f"名称: {proc.name} | "
                      f"内存: {Fore.YELLOW}{proc.memory_mb:.1f}MB{Style.RESET_ALL} | "
                      f"状态: {Fore.CYAN}{proc.status}{Style.RESET_ALL}")
        else:
            print(f"  {Fore.GREEN}无浏览器进程{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}Playwright 进程 ({len(playwright_processes)} 个):{Style.RESET_ALL}")
        if playwright_processes:
            for proc in playwright_processes:
                cmdline_str = ' '.join(proc.cmdline[:3]) + ('...' if len(proc.cmdline) > 3 else '')
                print(f"  PID: {Fore.GREEN}{proc.pid}{Style.RESET_ALL} | "
                      f"名称: {proc.name} | "
                      f"命令: {cmdline_str}")
        else:
            print(f"  {Fore.GREEN}无 Playwright 进程{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}已清理进程: {len(self.cleaned_processes)} 个{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

    def __del__(self):
        """析构函数"""
        if hasattr(self, 'cleaned_processes'):
            self.cleaned_processes.clear()


# 全局进程清理器实例
_global_process_cleaner: Optional[ProcessCleaner] = None


def get_process_cleaner() -> ProcessCleaner:
    """获取全局进程清理器实例"""
    global _global_process_cleaner
    if _global_process_cleaner is None:
        _global_process_cleaner = ProcessCleaner()
    return _global_process_cleaner


def cleanup_all_processes(force: bool = False) -> Dict[str, any]:
    """便捷函数：清理所有进程"""
    cleaner = get_process_cleaner()
    return cleaner.cleanup_all(force=force)