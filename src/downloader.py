"""
静态资源下载模块 - 使用 Playwright 渲染和下载网站资源
"""

import asyncio
import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional, Set, Dict, List
from urllib.parse import urlparse, urljoin
import logging
import atexit
import signal
import sys

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
import requests
from tqdm import tqdm
from colorama import Fore, Style

from .utils import (
    sanitize_filename, get_domain_from_url, url_to_filename,
    is_same_domain, normalize_url, save_json, format_bytes
)

# 导入新的管理模块
from .thread_manager import get_thread_manager, shutdown_thread_manager
from .process_cleaner import get_process_cleaner, cleanup_all_processes
from .memory_manager import get_memory_manager, start_memory_monitoring, stop_memory_monitoring
from .operation_middleware import (
    get_middleware, operation, async_operation, operation_context, OperationStatus
)


logger = logging.getLogger(__name__)


class WebsiteDownloader:
    """网站下载器 - 完整复刻网站资源"""

    def __init__(
        self,
        url: str,
        output_dir: Path,
        config: Optional[Dict] = None
    ):
        self.start_url = url
        self.base_domain = get_domain_from_url(url)
        self.output_dir = output_dir
        self.config = config or {}

        # 下载统计
        self.visited_urls: Set[str] = set()
        self.downloaded_files: Set[str] = set()
        self.failed_downloads: List[Dict] = []
        self.stats = {
            'pages': 0,
            'css': 0,
            'js': 0,
            'images': 0,
            'fonts': 0,
            'other': 0,
            'total_size': 0
        }

        # 资源映射 (URL -> 本地路径)
        self.resource_map: Dict[str, Path] = {}

        # 初始化管理器
        self._init_managers()

        # 注册清理函数
        self._register_cleanup_handlers()

        logger.info(f"{Fore.GREEN}[WebsiteDownloader] 初始化完成: {url}{Style.RESET_ALL}")

    def _init_managers(self):
        """初始化所有管理器"""
        # 获取管理器实例
        self.thread_manager = get_thread_manager()
        self.process_cleaner = get_process_cleaner()
        self.memory_manager = get_memory_manager()
        self.middleware = get_middleware()

        # 从配置中获取参数
        thread_config = self.config.get('thread', {})
        memory_config = self.config.get('memory', {})
        process_config = self.config.get('process_cleanup', {})

        # 启动线程管理器
        if thread_config.get('enable_monitoring', True):
            self.thread_manager.max_workers = thread_config.get('max_workers', 4)
            self.thread_manager.start()

        # 启动内存监控
        if memory_config.get('enable_monitoring', True):
            self.memory_manager.check_interval = memory_config.get('check_interval', 30.0)
            start_memory_monitoring()

            # 添加内存警告回调
            if memory_config.get('auto_gc', True):
                self.memory_manager.add_warning_callback(self._on_memory_warning)
                self.memory_manager.add_critical_callback(self._on_memory_critical)

            # 添加清理回调
            if memory_config.get('cache_cleanup', True):
                self.memory_manager.add_cleanup_callback(self._cleanup_resources)

        # 配置中间件
        middleware_config = self.config.get('middleware', {})
        self.middleware.show_progress = middleware_config.get('show_progress', True)
        self.middleware.show_details = middleware_config.get('show_details', True)
        self.middleware.color_output = middleware_config.get('color_output', True)

        logger.info(f"{Fore.CYAN}[WebsiteDownloader] 管理器初始化完成{Style.RESET_ALL}")

    def _register_cleanup_handlers(self):
        """注册清理处理函数"""
        # 注册退出处理函数
        atexit.register(self._cleanup_on_exit)

        # 注册信号处理函数
        if hasattr(signal, 'SIGINT'):  # Unix-like systems
            signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):  # Unix-like systems
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _on_memory_warning(self, memory_info: Dict[str, float]):
        """内存警告回调"""
        logger.warning(f"{Fore.YELLOW}[WebsiteDownloader] 内存使用警告: {memory_info.get('percent', 0):.1f}%{Style.RESET_ALL}")
        # 触发垃圾回收
        self.memory_manager.trigger_garbage_collection()

    def _on_memory_critical(self, memory_info: Dict[str, float]):
        """内存危险回调"""
        logger.error(f"{Fore.RED}[WebsiteDownloader] 内存使用危险: {memory_info.get('percent', 0):.1f}%{Style.RESET_ALL}")
        # 强制垃圾回收
        self.memory_manager.force_garbage_collection()
        # 清理所有缓存
        self.memory_manager.cleanup_all_caches()

    def _cleanup_resources(self) -> int:
        """清理资源回调"""
        cleaned_count = 0

        # 清理下载历史中的临时数据
        if len(self.visited_urls) > 1000:
            # 保留最近的1000个URL
            urls_to_remove = list(self.visited_urls)[:len(self.visited_urls) - 1000]
            self.visited_urls -= set(urls_to_remove)
            cleaned_count += len(urls_to_remove)

        # 清理资源映射中的无效条目
        invalid_resources = []
        for url, path in self.resource_map.items():
            if not path.exists():
                invalid_resources.append(url)

        for url in invalid_resources:
            del self.resource_map[url]
            cleaned_count += 1

        logger.debug(f"{Fore.CYAN}[WebsiteDownloader] 资源清理完成: {cleaned_count} 项{Style.RESET_ALL}")
        return cleaned_count

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"{Fore.YELLOW}[WebsiteDownloader] 接收到信号 {signum}，开始清理...{Style.RESET_ALL}")
        self._cleanup_on_exit()
        sys.exit(0)

    def _cleanup_on_exit(self):
        """退出时的清理函数"""
        try:
            logger.info(f"{Fore.CYAN}[WebsiteDownloader] 执行退出清理...{Style.RESET_ALL}")

            process_config = self.config.get('process_cleanup', {})

            # 安全的进程清理：只清理 Playwright 进程，不触及用户浏览器
            if process_config.get('cleanup_on_exit', False):
                # 只清理 Playwright 相关进程（不包括浏览器）
                if process_config.get('cleanup_playwright_processes', True):
                    try:
                        result = self.process_cleaner.terminate_playwright_processes(
                            force=process_config.get('force_cleanup_timeout', 10) > 0
                        )
                        logger.info(f"{Fore.GREEN}[WebsiteDownloader] Playwright 进程清理完成: {result}{Style.RESET_ALL}")
                    except Exception as e:
                        logger.warning(f"{Fore.YELLOW}[WebsiteDownloader] Playwright 进程清理失败: {e}{Style.RESET_ALL}")

                # ⚠️ 不再清理浏览器进程，避免误杀用户浏览器
                # 之前的 cleanup_all_processes() 会杀死所有 Chrome 进程，非常危险

            # 清理临时文件
            if process_config.get('cleanup_temp_files', False):
                temp_dirs = [self.output_dir / '.temp']
                try:
                    self.process_cleaner.cleanup_temp_files(temp_dirs)
                except Exception as e:
                    logger.warning(f"{Fore.YELLOW}[WebsiteDownloader] 临时文件清理失败: {e}{Style.RESET_ALL}")

            # 停止管理器
            try:
                stop_memory_monitoring()
                shutdown_thread_manager()
            except Exception as e:
                logger.warning(f"{Fore.YELLOW}[WebsiteDownloader] 管理器停止失败: {e}{Style.RESET_ALL}")

            logger.info(f"{Fore.GREEN}[WebsiteDownloader] 退出清理完成{Style.RESET_ALL}")

        except Exception as e:
            logger.error(f"{Fore.RED}[WebsiteDownloader] 退出清理失败: {e}{Style.RESET_ALL}")

    def _is_chrome_running(self) -> bool:
        """检测 Chrome/Edge 浏览器是否正在运行"""
        system = platform.system()

        try:
            if system == "Windows":
                # Windows: 使用 tasklist
                result = subprocess.run(
                    ['tasklist'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                output = result.stdout.lower()
                return 'chrome.exe' in output or 'msedge.exe' in output

            elif system == "Darwin":  # macOS
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True
                )
                output = result.stdout.lower()
                return 'google chrome' in output or 'microsoft edge' in output

            else:  # Linux
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True
                )
                output = result.stdout.lower()
                return 'chrome' in output or 'chromium' in output

        except Exception as e:
            logger.warning(f"无法检测浏览器进程: {e}")
            return False

    def _has_valid_browser_data(self, data_dir: Path) -> bool:
        """
        检查目录是否包含有效的浏览器数据

        Args:
            data_dir: 要检查的数据目录路径

        Returns:
            bool: True表示目录包含有效数据，False表示目录为空或无效
        """
        if not data_dir.exists():
            return False

        # 检查Default目录
        default_dir = data_dir / 'Default'
        if not default_dir.exists():
            return False

        # 检查关键文件是否存在（至少要有其中一个）
        key_files = [
            'Cookies',           # 网站的登录状态和会话
            'Preferences',       # 浏览器设置和扩展
            'Web Data',          # 表单数据和网站数据
            'Local Storage',     # 本地存储
            'Network/Cookies',   # 网络Cookie
        ]

        has_key_files = False
        for key_file in key_files:
            if (default_dir / key_file).exists():
                has_key_files = True
                break

        # 检查是否有基本的目录结构
        key_dirs = ['Local Storage', 'Network']
        has_key_dirs = any((default_dir / dir_name).exists() for dir_name in key_dirs)

        return has_key_files or has_key_dirs

    def _get_chrome_user_data_dir(self, mode: str = 'playwright') -> str:
        """
        获取 Chrome 用户数据目录

        Args:
            mode: 'system' = 使用系统完整数据目录 (需关闭Chrome)
                  'playwright' = 使用项目本地 Playwright Profile (项目文件夹)
        """
        system = platform.system()

        if mode == 'system':
            # 获取系统 Chrome 基础路径
            if system == "Windows":
                base_path = Path(os.getenv('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data'
            elif system == "Darwin":  # macOS
                base_path = Path.home() / 'Library' / 'Application Support' / 'Google' / 'Chrome'
            else:  # Linux
                base_path = Path.home() / '.config' / 'google-chrome'

            # 使用完整的系统数据目录
            if base_path.exists():
                logger.info(f"[OK] 使用系统 Chrome 完整数据: {base_path}")
                return str(base_path)
            else:
                logger.warning(f"[WARN] 未找到系统 Chrome 数据, 将使用项目本地数据")

        if mode == 'playwright':
            # 使用项目根目录的 Playwright Profile
            project_root = Path(__file__).parent.parent
            playwright_data_dir = project_root / 'browser-data'

            # 先检查是否已有有效的浏览器数据
            if self._has_valid_browser_data(playwright_data_dir):
                logger.info(f"{Fore.GREEN}[OK] 使用现有的项目浏览器数据: {playwright_data_dir}{Style.RESET_ALL}")
                return str(playwright_data_dir)
            else:
                # 没有有效数据，创建新目录
                playwright_data_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"{Fore.CYAN}[INFO] 创建新的项目浏览器数据: {playwright_data_dir}{Style.RESET_ALL}")
                return str(playwright_data_dir)

    async def _wait_for_user_confirmation(self, url: str) -> bool:
        """等待用户确认页面是否正确"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[INFO] 请检查浏览器中的页面...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}URL: {url}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        # 检查是否启用了浏览器数据保存
        if self.config.get('use_system_chrome', False) and self.config.get('chrome_mode') == 'playwright':
            print(f"{Fore.GREEN}[SAVE] 当前 playwright 模式会自动保存登录状态和Cookies{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[INFO] 本次登录的数据将保存到 ./browser-data/ 目录{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[INFO] 下次运行时会自动使用保存的登录状态{Style.RESET_ALL}\n")
        elif self.config.get('use_system_chrome', False):
            print(f"{Fore.GREEN}[SAVE] 当前模式会使用和保存浏览器数据{Style.RESET_ALL}\n")
        else:
            print(f"{Fore.YELLOW}[WARN] 当前独立浏览器模式不会保存登录状态{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}[OK] 如果页面正确（已登录、内容完整），请输入 'y' 继续{Style.RESET_ALL}")
        print(f"{Fore.RED}[X] 如果页面有问题，请输入 'n' 取消{Style.RESET_ALL}")

        while True:
            choice = input(f"\n请确认 (y/n): ").strip().lower()
            if choice == 'y':
                logger.info(f"{Fore.GREEN}[OK] 用户确认页面正确，开始下载...{Style.RESET_ALL}\n")
                return True
            elif choice == 'n':
                logger.warning(f"{Fore.YELLOW}[X] 用户取消操作{Style.RESET_ALL}")
                return False
            else:
                print("请输入 'y' 或 'n'")

    async def _is_page_stable(self, page: Page, timeout: Optional[int] = None) -> bool:
        """检查页面是否稳定（不再进行导航和大量资源加载）

        Args:
            page: Playwright Page 对象
            timeout: 检查超时时间（毫秒），None 时使用配置值

        Returns:
            bool: 页面是否稳定
        """
        try:
            # 获取配置参数
            dynamic_config = self.config.get('dynamic_page_handling', {})
            if not dynamic_config.get('enabled', False):
                # 如果没有启用动态页面处理，直接返回 True
                return True

            stability_timeout = timeout or dynamic_config.get('page_stability_timeout', 5000)
            network_idle_timeout = dynamic_config.get('network_idle_timeout', 3000)
            stability_delay = dynamic_config.get('stability_check_delay', 1000)

            # 等待页面基本加载完成
            await page.wait_for_load_state('domcontentloaded', timeout=stability_timeout)

            # 检查是否有正在进行中的导航
            is_navigating = await page.evaluate('''
                () => {
                    // 检查页面是否正在导航
                    return performance.navigation && performance.navigation.type === 1;
                }
            ''')

            if is_navigating:
                await asyncio.sleep(0.5)  # 等待导航完成
                return False

            # 检查网络请求是否基本完成
            try:
                await page.wait_for_load_state('networkidle', timeout=network_idle_timeout)
            except:
                # networkidle 超时不是致命错误，继续执行
                pass

            # 最后检查页面是否仍然稳定
            current_url = page.url
            await asyncio.sleep(stability_delay / 1000)  # 等待配置的时间后再次检查

            if current_url != page.url:
                # URL 发生了变化，说明页面在进行导航
                return False

            return True

        except Exception as e:
            logger.debug(f"页面稳定性检查失败: {e}")
            return False

    async def _get_page_content_with_retry(self, page: Page, max_retries: Optional[int] = None) -> Optional[str]:
        """带重试机制的页面内容获取

        Args:
            page: Playwright Page 对象
            max_retries: 最大重试次数，None 时使用配置值

        Returns:
            Optional[str]: 页面 HTML 内容，获取失败返回 None
        """
        # 获取配置参数
        dynamic_config = self.config.get('dynamic_page_handling', {})
        retry_attempts = max_retries or dynamic_config.get('content_retry_attempts', 3)
        retry_delay = dynamic_config.get('content_retry_delay', 1000)

        for attempt in range(retry_attempts):
            try:
                # 在获取内容前先检查页面是否稳定
                if await self._is_page_stable(page):
                    html = await page.content()
                    if html and html.strip():
                        return html
                    else:
                        logger.warning("获取到的页面内容为空")
                else:
                    logger.warning(f"页面不稳定，尝试 {attempt + 1}/{retry_attempts}")

            except Exception as e:
                error_msg = str(e)
                if "navigating" in error_msg.lower():
                    logger.warning(f"页面正在导航，尝试 {attempt + 1}/{retry_attempts}: {e}")
                else:
                    logger.warning(f"获取页面内容失败，尝试 {attempt + 1}/{retry_attempts}: {e}")

            # 如果不是最后一次尝试，等待一段时间再重试
            if attempt < retry_attempts - 1:
                await asyncio.sleep(retry_delay / 1000)

        logger.error(f"获取页面内容失败，已重试 {retry_attempts} 次")
        return None

    @async_operation("网站下载", progress_total=100)
    async def download(self) -> Dict:
        """开始下载网站"""

        with operation_context("网站下载", progress_total=100) as operation_id:
            try:
                logger.info(f"开始下载网站: {self.start_url}")
                self.middleware.log_step(operation_id, "初始化下载任务", "INFO", f"目标URL: {self.start_url}")

                async with async_playwright() as p:
                    # 获取配置
                    headless = self.config.get('headless', False)
                    use_system_chrome = self.config.get('use_system_chrome', True)
                    chrome_data_dir = self.config.get('chrome_data_dir')
                    chrome_mode = self.config.get('chrome_mode', 'playwright')  # system/playwright
                    wait_for_confirmation = self.config.get('wait_for_confirmation', True)

                    context = None
                    browser = None

                    self.middleware.log_step(operation_id, "检查浏览器配置", "INFO",
                                           f"模式: {chrome_mode}, 无头模式: {headless}")

                    # 记录启动前的浏览器进程（用于 PID 跟踪）
                    browser_pids_before = set()
                    try:
                        browser_processes_before = self.process_cleaner.get_browser_processes()
                        browser_pids_before = {proc.pid for proc in browser_processes_before}
                        logger.debug(f"启动前浏览器进程: {len(browser_pids_before)} 个")
                    except Exception as e:
                        logger.warning(f"获取启动前进程列表失败: {e}")

                    # 如果使用系统 Chrome 数据
                    if use_system_chrome:
                        # 检测 Chrome 是否正在运行
                        is_chrome_running = self._is_chrome_running()

                        # 如果是 system 模式且 Chrome 正在运行，给出警告
                        if chrome_mode == 'system' and is_chrome_running:
                            print(f"\n{Fore.YELLOW}[WARN] 警告: 检测到 Chrome 浏览器正在运行{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}使用 system 模式���要关闭所有 Chrome 窗口{Style.RESET_ALL}")
                            print(f"{Fore.GREEN}提示: 推荐使用 playwright 模式（默认），无需关闭 Chrome{Style.RESET_ALL}\n")

                            choice = input("是否继续尝试启动? (y/N): ").strip().lower()
                            if choice != 'y':
                                logger.info("用户取消操作")
                                self.middleware.update_operation(operation_id, OperationStatus.CANCELLED, "用户取消操作")
                                return {}

                        # 获取 Chrome 数据目录
                        if not chrome_data_dir:
                            chrome_data_dir = self._get_chrome_user_data_dir(mode=chrome_mode)

                        self.middleware.log_step(operation_id, "启动浏览器上下文", "PROGRESS",
                                               f"数据目录: {chrome_data_dir}")

                        # 尝试使用持久化上下文
                        try:
                            context = await p.chromium.launch_persistent_context(
                                user_data_dir=chrome_data_dir,
                                headless=headless,
                                viewport=self.config.get('viewport', {'width': 1920, 'height': 1080}),
                                accept_downloads=True
                            )
                            logger.info(f"{Fore.GREEN}[OK] 成功启动浏览器 (模式: {chrome_mode}){Style.RESET_ALL}")
                            self.middleware.log_step(operation_id, "浏览器启动成功", "SUCCESS",
                                                   f"模式: {chrome_mode}")

                        except Exception as e:
                            logger.error(f"{Fore.RED}[X] 持久化上下文启动失败: {e}{Style.RESET_ALL}")

                            # 自动回退到独立模式
                            print(f"\n{Fore.YELLOW}[WARN] 正在回退到独立浏览器模式...{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}提示: 您可能需要在浏览器中重新登录{Style.RESET_ALL}\n")

                            use_system_chrome = False  # 标记为不使用系统 Chrome
                            context = None

                    # 如果不使用系统 Chrome 或回退失败，使用独立模式
                    if not use_system_chrome or context is None:
                        self.middleware.log_step(operation_id, "启动独立浏览器", "PROGRESS")

                        # 使用普通模式（独立浏览器实例）
                        browser = await p.chromium.launch(headless=headless)
                        context = await browser.new_context(
                            viewport=self.config.get('viewport', {'width': 1920, 'height': 1080})
                        )
                        logger.info(f"{Fore.GREEN}[OK] 成功启动独立浏览器{Style.RESET_ALL}")
                        self.middleware.log_step(operation_id, "独立浏览器启动成功", "SUCCESS")

                    # 注册新启动的浏览器进程 PID（用于安全清理）
                    try:
                        import asyncio
                        await asyncio.sleep(1)  # 等待浏览器进程完全启动

                        browser_processes_after = self.process_cleaner.get_browser_processes()
                        browser_pids_after = {proc.pid for proc in browser_processes_after}

                        new_pids = browser_pids_after - browser_pids_before
                        for pid in new_pids:
                            self.process_cleaner.register_process(pid, f"Playwright浏览器进程")
                            logger.info(f"{Fore.GREEN}[PID跟踪] 注册浏览器进程: {pid}{Style.RESET_ALL}")

                        if new_pids:
                            self.middleware.log_step(operation_id, "注册浏览器进程PID", "SUCCESS",
                                                   f"已注册 {len(new_pids)} 个进程")
                        else:
                            logger.debug("未检测到新的浏览器进程（可能使用了持久化上下文）")

                    except Exception as e:
                        logger.warning(f"{Fore.YELLOW}[PID跟踪] 注册浏览器进程失败: {e}{Style.RESET_ALL}")

                    try:
                        self.middleware.log_step(operation_id, "准备下载页面", "INFO")

                        # 如果启用用户确认，先打开页面让用户检查
                        confirmed_page = None
                        if wait_for_confirmation:
                            self.middleware.log_step(operation_id, "打开页面等待用户确认", "INFO")

                            # 打开第一个页面
                            page = context.pages[0] if context.pages else await context.new_page()
                            await page.goto(self.start_url, wait_until='networkidle', timeout=60000)

                            # 等待用户确认
                            if not await self._wait_for_user_confirmation(self.start_url):
                                logger.info("用户取消下载")
                                self.middleware.update_operation(operation_id, OperationStatus.CANCELLED, "用户取消下载")
                                return {}

                            # 保存已确认的页面，供下载函数复用
                            confirmed_page = page
                            self.middleware.log_step(operation_id, "用户确认完成", "SUCCESS")

                        # 用户确认后（或不需要确认时），创建输出目录
                        self.output_dir.mkdir(parents=True, exist_ok=True)
                        self.middleware.log_step(operation_id, "开始下载网站内容", "PROGRESS")

                        # 下载主页和所有资源（复用已确认的页面）
                        await self._download_recursive_with_context(
                            context, self.start_url, depth=0, existing_page=confirmed_page,
                            operation_id=operation_id
                        )

                        self.middleware.log_step(operation_id, "生成下载报告", "PROGRESS")

                        # 保存下载报告
                        report = self._generate_report()
                        save_json(report, self.output_dir / 'download_report.json')

                        self.middleware.log_step(operation_id, "下载完成", "SUCCESS",
                                               f"页面: {self.stats['pages']}, CSS: {self.stats['css']}, 图片: {self.stats['images']}")

                        # 添加统计信息到操作结果
                        self.middleware.update_operation(operation_id, OperationStatus.SUCCESS,
                                                      message=f"下载完成! 共 {self.stats['pages']} 个页面",
                                                      details={
                                                          'pages': self.stats['pages'],
                                                          'css': self.stats['css'],
                                                          'js': self.stats['js'],
                                                          'images': self.stats['images'],
                                                          'fonts': self.stats['fonts'],
                                                          'total_size': format_bytes(self.stats['total_size'])
                                                      })

                        logger.info(f"下载完成! 共 {self.stats['pages']} 个页面")
                        return report

                    finally:
                        self.middleware.log_step(operation_id, "清理浏览器资源", "INFO")

                        await context.close()
                        if browser:
                            await browser.close()

                        self.middleware.log_step(operation_id, "浏览器资源已释放", "SUCCESS")

            except Exception as e:
                self.middleware.update_operation(operation_id, OperationStatus.FAILED,
                                              message=f"下载失败: {str(e)}",
                                              error=e)
                logger.error(f"下载过程中发生错误: {e}")
                raise

    async def _download_recursive_with_context(
        self,
        context: BrowserContext,
        url: str,
        depth: int,
        existing_page: Optional[Page] = None,
        operation_id: Optional[str] = None
    ) -> None:
        """递归下载页面及其资源（使用 BrowserContext）

        Args:
            context: 浏览器上下文
            url: 要下载的URL
            depth: 当前深度
            existing_page: 已存在的页面（用于复用已确认的页面，避免重新打开）
            operation_id: 操作ID，用于进度追踪
        """
        # 检查深度限制
        max_depth = self.config.get('max_depth', 3)
        if depth > max_depth:
            return

        # 检查是否已访问
        if url in self.visited_urls:
            return

        # 检查页面数量限制
        max_pages = self.config.get('max_pages', 50)
        if len(self.visited_urls) >= max_pages:
            return

        # 检查是否为同一域名
        if not self.config.get('follow_external_links', False):
            if not is_same_domain(url, self.start_url):
                return

        self.visited_urls.add(url)
        logger.info(f"正在下载 [{depth}]: {url}")

        # 输出下载进度日志（如果有操作ID）
        if operation_id:
            self.middleware.log_step(operation_id, f"下载页面 ({len(self.visited_urls)}/{max_pages})", "PROGRESS",
                                   f"URL: {url[:80]}...")

        try:
            # 复用已存在的页面，或创建新页面
            if existing_page:
                page = existing_page
                logger.info(f"��用已确认的页面: {url}")
            else:
                page = await context.new_page()

            # 监听网络请求,捕获所有资源
            resources = []

            async def handle_response(response):
                resources.append({
                    'url': response.url,
                    'status': response.status,
                    'type': response.request.resource_type
                })

            page.on('response', handle_response)

            # 如果是新创建的页面，需要访问URL
            if not existing_page:
                # 访问页面
                await page.goto(url, timeout=self.config.get('timeout', 30000))

                # 等待页面加载完成
                await page.wait_for_load_state('networkidle')

            # 获取页面HTML（使用重试机制）
            html = await self._get_page_content_with_retry(page)
            if html is None:
                logger.error(f"无法获取页面内容: {url}")
                return

            # 保存 HTML 文件
            html_path = self._save_html(url, html)
            self.stats['pages'] += 1

            # 直接下载页面资源
            await self._download_page_resources(page, url, html, resources)

            # 查找并下载链接的页面
            links = await self._extract_links(page, url)
            for link in links:
                await self._download_recursive_with_context(
                    context, link, depth + 1, existing_page=None, operation_id=operation_id
                )

            # 只关闭新创建的页面，不关闭复用的页面
            if not existing_page:
                await page.close()

        except Exception as e:
            # 区分不同类型的错误，避免误导性提示
            error_msg = str(e)
            if 'Incoming markup is of an invalid type' in error_msg:
                # 这是代码逻辑问题，但通常不影响结果（降为debug）
                logger.debug(f"页面处理警告 {url}: BeautifulSoup类型错误（可忽略）")
            else:
                # 其他真正的下载错误
                logger.error(f"下载失败 {url}: {e}")

            self.failed_downloads.append({
                'url': url,
                'error': str(e),
                'severity': 'info' if 'Incoming markup' in error_msg else 'error'
            })

    async def _download_recursive(
        self,
        browser: Browser,
        url: str,
        depth: int
    ) -> None:
        """递归下载页面及其资源（使用 Browser，兼容旧代码）"""
        # 检查深度限制
        max_depth = self.config.get('max_depth', 3)
        if depth > max_depth:
            return

        # 检查是否已访问
        if url in self.visited_urls:
            return

        # 检查页面数量限制
        max_pages = self.config.get('max_pages', 50)
        if len(self.visited_urls) >= max_pages:
            return

        # 检查是否为同一域名
        if not self.config.get('follow_external_links', False):
            if not is_same_domain(url, self.start_url):
                return

        self.visited_urls.add(url)
        logger.info(f"正在下载 [{depth}]: {url}")

        try:
            # 创建新页面
            page = await browser.new_page(
                viewport=self.config.get('viewport', {'width': 1920, 'height': 1080})
            )

            # 监听网络请求,捕获所有资源
            resources = []

            async def handle_response(response):
                resources.append({
                    'url': response.url,
                    'status': response.status,
                    'type': response.request.resource_type
                })

            page.on('response', handle_response)

            # 访问页面
            await page.goto(url, timeout=self.config.get('timeout', 30000))

            # 等待页面加载完成
            await page.wait_for_load_state('networkidle', timeout=10000)

            # 获取渲染后的 HTML
            html = await page.content()

            # 保存 HTML 文件
            html_path = self._save_html(url, html)
            self.stats['pages'] += 1

            # 提取并下载所有资源
            await self._download_page_resources(page, url, html, resources)

            # 提取链接并递归下载
            links = self._extract_links(html, url)
            for link in links:
                await self._download_recursive(browser, link, depth + 1)

            await page.close()

        except Exception as e:
            # 区分不同类型的错误，避免误导性提示
            error_msg = str(e)
            if 'Incoming markup is of an invalid type' in error_msg:
                # 这是代码逻辑问题，但通常不影响结果（降为debug）
                logger.debug(f"页面处理警告 {url}: BeautifulSoup类型错误（可忽略）")
            else:
                # 其他真正的下载错误
                logger.error(f"下载失败 {url}: {e}")

            self.failed_downloads.append({
                'url': url,
                'error': str(e),
                'severity': 'info' if 'Incoming markup' in error_msg else 'error'
            })

    async def _download_page_resources(
        self,
        page: Page,
        page_url: str,
        html: str,
        network_resources: List[Dict]
    ) -> None:
        """并发下载页面的所有资源"""
        soup = BeautifulSoup(html, 'html.parser')

        # 收集所有需要下载的资源
        download_tasks = []

        # 收集 CSS 文件
        if self.config.get('download_css', True):
            for tag in soup.find_all('link', rel='stylesheet'):
                if tag.get('href'):
                    css_url = normalize_url(tag['href'], page_url)
                    download_tasks.append((css_url, 'css', page_url))

        # 收集 JavaScript 文件
        if self.config.get('download_js', True):
            for tag in soup.find_all('script', src=True):
                js_url = normalize_url(tag['src'], page_url)
                download_tasks.append((js_url, 'js', page_url))

        # 收集图片
        if self.config.get('download_images', True):
            for tag in soup.find_all('img', src=True):
                img_url = normalize_url(tag['src'], page_url)
                download_tasks.append((img_url, 'images', page_url))

            # srcset 属性中的图片
            for tag in soup.find_all('img', srcset=True):
                srcset = tag['srcset']
                for src in srcset.split(','):
                    img_url = src.strip().split()[0]
                    img_url = normalize_url(img_url, page_url)
                    download_tasks.append((img_url, 'images', page_url))

        # 收集字体
        if self.config.get('download_fonts', True):
            # 从网络资源中提取字体
            for resource in network_resources:
                if resource['type'] == 'font':
                    download_tasks.append((resource['url'], 'fonts', page_url))

        # 收集内联样式中的资源
        if self.config.get('download_images', True):
            for tag in soup.find_all(True):  # 查找所有标签
                style_attr = tag.get('style')
                if style_attr:
                    # 提取内联样式中的URL
                    urls = self._parse_css_urls(style_attr, page_url)
                    for url in urls:
                        # 根据文件扩展名判断资源类型
                        ext = url.lower().split('?')[0].split('.')[-1]
                        if ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico']:
                            download_tasks.append((url, 'images', page_url))
                        elif ext in ['woff', 'woff2', 'ttf', 'eot', 'otf']:
                            download_tasks.append((url, 'fonts', page_url))

        # 收集 <style> 标签中的资源
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                css_content = str(style_tag.string)
                # 提取 <style> 标签中的所有 URL
                urls = self._parse_css_urls(css_content, page_url)
                for url in urls:
                    # 根据文件扩展名判断资源类型
                    ext = url.lower().split('?')[0].split('.')[-1]

                    if ext in ['woff', 'woff2', 'ttf', 'eot', 'otf']:
                        resource_type = 'fonts'
                    elif ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico']:
                        resource_type = 'images'
                    else:
                        resource_type = 'other'

                    download_tasks.append((url, resource_type, page_url))

        # 并发下载所有资源（使用 Semaphore 限制并发数）
        if download_tasks:
            performance_config = self.config.get('performance', {})
            max_concurrent = performance_config.get('parallel_resource_downloads', 5)
            semaphore = asyncio.Semaphore(max_concurrent)

            async def download_with_limit(url: str, resource_type: str, base_url: Optional[str]):
                """带并发限制的下载"""
                async with semaphore:
                    try:
                        await self._download_resource(url, resource_type, base_url)
                    except Exception as e:
                        # 单个资源失败不影响其他资源
                        logger.debug(f"资源下载失败 {url}: {e}")

            logger.info(f"{Fore.CYAN}[并发下载] 准备下载 {len(download_tasks)} 个资源（并发数: {max_concurrent}）{Style.RESET_ALL}")

            # 如果在操作上下文中，输出日志
            # 注意：这里没有 operation_id，所以用全局中间件
            from .operation_middleware import get_middleware
            middleware = get_middleware()

            # 统计资源类型
            type_counts = {}
            for _, rtype, _ in download_tasks:
                type_counts[rtype] = type_counts.get(rtype, 0) + 1

            details = ", ".join([f"{t}: {c}" for t, c in type_counts.items()])
            middleware.log_step("download", f"并发下载 {len(download_tasks)} 个资源", "PROGRESS",
                              f"并发数: {max_concurrent}\n{details}")

            # 使用 asyncio.gather 并发执行，return_exceptions=True 避免单个失败影响全局
            await asyncio.gather(*[
                download_with_limit(url, rtype, base_url)
                for url, rtype, base_url in download_tasks
            ], return_exceptions=True)

            middleware.log_step("download", f"资源下载完成", "SUCCESS",
                              f"成功下载 {len(download_tasks)} 个资源")

    async def _download_resource(self, url: str, resource_type: str, base_url: Optional[str] = None) -> None:
        """下载单个资源文件（支持并发）"""
        if url in self.downloaded_files:
            return

        self.downloaded_files.add(url)

        try:
            # 处理 data URI (如 data:image/svg+xml;base64,...)
            if url.startswith('data:'):
                await self._download_data_uri(url, resource_type)
                return

            # 使用 asyncio.to_thread 在线程池中执行同步 HTTP 请求
            # 这样可以真正并发下载，不阻塞事件循环
            response = await asyncio.to_thread(
                requests.get, url, timeout=30, stream=True
            )
            response.raise_for_status()

            # 保存文件
            file_path = url_to_filename(url, self.output_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 更新统计
            file_size = file_path.stat().st_size
            self.stats[resource_type] += 1
            self.stats['total_size'] += file_size
            self.resource_map[url] = file_path

            logger.debug(f"已下载 {resource_type}: {url}")

            # 如果是CSS文件，解析并下载其中引用的资源
            if resource_type == 'css' and base_url:
                await self._process_css_resources(file_path, url)

        except requests.exceptions.HTTPError as e:
            # 区分404和其他HTTP错误
            if '404' in str(e):
                # 404错误很常见（失效链接），降为debug级别
                logger.debug(f"资源不存在 (404) {url[:80]}")
                self.failed_downloads.append({
                    'url': url,
                    'type': resource_type,
                    'error': '404 Not Found',
                    'severity': 'info'  # 标记为信息级别
                })
            else:
                # 其他HTTP错误（403、500等）是真正的问题
                logger.warning(f"资源下载失败 {url[:80]}: {e}")
                self.failed_downloads.append({
                    'url': url,
                    'type': resource_type,
                    'error': str(e),
                    'severity': 'warning'
                })
        except requests.exceptions.RequestException as e:
            # 网络错误（超时、连接失败等）
            logger.warning(f"网络错误 {url[:80]}: {e}")
            self.failed_downloads.append({
                'url': url,
                'type': resource_type,
                'error': str(e),
                'severity': 'warning'
            })
        except Exception as e:
            # 其他未预期的错误
            logger.warning(f"资源下载失败 {url[:80]}: {e}")
            self.failed_downloads.append({
                'url': url,
                'type': resource_type,
                'error': str(e),
                'severity': 'warning'
            })

    async def _process_css_resources(self, css_file_path: Path, css_url: str) -> None:
        """并发处理CSS文件中引用的资源（图片、字体等）"""
        try:
            # 读取CSS文件内容
            with open(css_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                css_content = f.read()

            # 提取所有url()引用
            urls = self._parse_css_urls(css_content, css_url)

            if not urls:
                return

            logger.info(f"从CSS提取到 {len(urls)} 个资源: {css_url}")

            # 收集下载任务
            download_tasks = []
            for url in urls:
                # 根据文件扩展名判断资源类型
                ext = url.lower().split('?')[0].split('.')[-1]

                if ext in ['woff', 'woff2', 'ttf', 'eot', 'otf']:
                    resource_type = 'fonts'
                elif ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico']:
                    resource_type = 'images'
                else:
                    resource_type = 'other'

                download_tasks.append((url, resource_type))

            # 并发下载CSS中的所有资源（注意：不传递base_url避免递归处理）
            performance_config = self.config.get('performance', {})
            max_concurrent = performance_config.get('parallel_resource_downloads', 5)
            semaphore = asyncio.Semaphore(max_concurrent)

            async def download_css_resource(url: str, resource_type: str):
                """带并发限制的CSS资源下载"""
                async with semaphore:
                    try:
                        await self._download_resource(url, resource_type, base_url=None)
                    except Exception as e:
                        logger.debug(f"CSS资源下载失败 {url}: {e}")

            # 并发执行
            await asyncio.gather(*[
                download_css_resource(url, rtype)
                for url, rtype in download_tasks
            ], return_exceptions=True)

        except Exception as e:
            logger.warning(f"处理CSS资源失败 {css_url}: {e}")

    def _parse_css_urls(self, css_content: str, base_url: str) -> List[str]:
        """从CSS内容中提取所有url()引用"""
        import re
        urls = []

        # 匹配 url() 中的所有 URL
        # 支持格式: url(xxx), url('xxx'), url("xxx")
        pattern = r'url\s*\(\s*["\']?([^)"\'\s]+)["\']?\s*\)'
        matches = re.findall(pattern, css_content, re.IGNORECASE)

        for match in matches:
            # 跳过 data URI
            if match.startswith('data:'):
                continue

            # 标准化URL
            try:
                full_url = normalize_url(match, base_url)
                urls.append(full_url)
                logger.debug(f"从CSS提取URL: {match} -> {full_url}")
            except Exception as e:
                logger.warning(f"解析CSS URL失败: {match}, 错误: {e}")

        return urls

    async def _download_data_uri(self, data_uri: str, resource_type: str) -> None:
        """下载 data URI 格式的资源"""
        import base64
        import hashlib
        import re

        try:
            # 解析 data URI: data:[<mediatype>][;base64],<data>
            match = re.match(r'data:([^;,]+)?(;base64)?,(.+)', data_uri)
            if not match:
                logger.warning(f"无效的 data URI 格式: {data_uri[:100]}")
                return

            mime_type = match.group(1) or 'application/octet-stream'
            is_base64 = match.group(2) is not None
            data = match.group(3)

            # 解码数据
            if is_base64:
                file_content = base64.b64decode(data)
            else:
                # URL 解码
                import urllib.parse
                file_content = urllib.parse.unquote(data).encode('utf-8')

            # 根据 MIME 类型确定文件扩展名
            ext_map = {
                'image/svg+xml': '.svg',
                'image/png': '.png',
                'image/jpeg': '.jpg',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'text/css': '.css',
                'text/javascript': '.js',
                'application/javascript': '.js',
            }
            ext = ext_map.get(mime_type, '.dat')

            # 使用内容的 hash 作为文件名
            file_hash = hashlib.md5(file_content).hexdigest()[:12]
            filename = f"data_uri_{file_hash}{ext}"

            # 保存文件
            file_path = self.output_dir / 'data-uris' / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(file_content)

            # 更新统计
            file_size = len(file_content)
            self.stats[resource_type] += 1
            self.stats['total_size'] += file_size
            self.resource_map[data_uri] = file_path

            logger.debug(f"已保存 data URI {resource_type}: {filename}")

        except Exception as e:
            logger.warning(f"保存 data URI 失败: {e}")
            self.failed_downloads.append({
                'url': 'data-uri',
                'type': resource_type,
                'error': str(e)
            })

    def _save_html(self, url: str, html: str) -> Path:
        """保存 HTML 文件"""
        file_path = url_to_filename(url, self.output_dir)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 处理HTML中的资源链接,转换为本地路径
        html = self._rewrite_html_links(html, url)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)

        self.resource_map[url] = file_path
        return file_path

    def _rewrite_html_links(self, html: str, base_url: str) -> str:
        """重写HTML中的链接为本地路径"""
        soup = BeautifulSoup(html, 'html.parser')

        # 处理CSS链接
        for tag in soup.find_all('link', href=True):
            original_url = normalize_url(tag['href'], base_url)
            if original_url in self.resource_map:
                tag['href'] = self._get_relative_path(base_url, original_url)

        # 处理JS链接
        for tag in soup.find_all('script', src=True):
            original_url = normalize_url(tag['src'], base_url)
            if original_url in self.resource_map:
                tag['src'] = self._get_relative_path(base_url, original_url)

        # 处理图片链接
        for tag in soup.find_all('img', src=True):
            original_url = normalize_url(tag['src'], base_url)
            if original_url in self.resource_map:
                tag['src'] = self._get_relative_path(base_url, original_url)

        # 处理a标签链接
        for tag in soup.find_all('a', href=True):
            original_url = normalize_url(tag['href'], base_url)
            if original_url in self.resource_map:
                tag['href'] = self._get_relative_path(base_url, original_url)

        return str(soup)

    def _get_relative_path(self, from_url: str, to_url: str) -> str:
        """计算相对路径"""
        from_path = url_to_filename(from_url, self.output_dir)
        to_path = url_to_filename(to_url, self.output_dir)

        try:
            rel_path = to_path.relative_to(from_path.parent)
            return str(rel_path).replace('\\', '/')
        except ValueError:
            # 如果无法计算相对路径,返回绝对路径
            return str(to_path).replace('\\', '/')

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """从HTML中提取所有链接"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []

        for tag in soup.find_all('a', href=True):
            url = normalize_url(tag['href'], base_url)

            # 过滤非HTTP链接
            if not url.startswith(('http://', 'https://')):
                continue

            # 只提取同域名的链接
            if not self.config.get('follow_external_links', False):
                if not is_same_domain(url, self.start_url):
                    continue

            if url not in self.visited_urls and url not in links:
                links.append(url)

        return links

    def _generate_report(self) -> Dict:
        """生成下载报告"""
        return {
            'start_url': self.start_url,
            'base_domain': self.base_domain,
            'statistics': {
                'pages_downloaded': self.stats['pages'],
                'css_files': self.stats['css'],
                'js_files': self.stats['js'],
                'images': self.stats['images'],
                'fonts': self.stats['fonts'],
                'other_files': self.stats['other'],
                'total_files': sum([
                    self.stats['css'],
                    self.stats['js'],
                    self.stats['images'],
                    self.stats['fonts'],
                    self.stats['other']
                ]),
                'total_size': format_bytes(self.stats['total_size']),
                'total_size_bytes': self.stats['total_size']
            },
            'visited_urls': list(self.visited_urls),
            'failed_downloads': self.failed_downloads,
            'output_directory': str(self.output_dir)
        }


async def download_website(url: str, output_dir: Path, config: Dict) -> Dict:
    """便捷函数: 下载网站"""
async def download_website(url: str, output_dir: Path, config: Dict) -> Dict:
    """Download website function"""
    downloader = WebsiteDownloader(url, output_dir, config)
    return await downloader.download()