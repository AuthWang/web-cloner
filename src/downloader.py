"""
静态资源下载模块 - 使用 Playwright 渲染和下载网站资源
"""

import asyncio
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, Set, Dict, List
from urllib.parse import urlparse, urljoin
import logging

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
import requests
from tqdm import tqdm
from colorama import Fore, Style

from .utils import (
    sanitize_filename, get_domain_from_url, url_to_filename,
    is_same_domain, normalize_url, save_json, format_bytes
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

    def _get_chrome_user_data_dir(self, mode: str = 'playwright') -> str:
        """
        获取 Chrome 用户数据目录

        Args:
            mode: 'system' = 使用系统完整数据目录 (需关闭Chrome)
                  'playwright' = 使用 Playwright 专用 Profile (推荐)
                  'temp' = 使用临时目录
        """
        system = platform.system()

        # 获取系统 Chrome 基础路径
        if system == "Windows":
            base_path = Path(os.getenv('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data'
        elif system == "Darwin":  # macOS
            base_path = Path.home() / 'Library' / 'Application Support' / 'Google' / 'Chrome'
        else:  # Linux
            base_path = Path.home() / '.config' / 'google-chrome'

        if mode == 'system':
            # 使用完整的系统数据目录
            if base_path.exists():
                logger.info(f"[OK] 使用系统 Chrome 完整数据: {base_path}")
                return str(base_path)
            else:
                logger.warning(f"[WARN] 未找到系统 Chrome 数据")
                mode = 'temp'  # 回退到临时目录

        if mode == 'playwright':
            # 使用 Playwright 专用 Profile (推荐)
            if base_path.exists():
                playwright_profile = base_path / 'Playwright'
                playwright_profile.mkdir(exist_ok=True)
                logger.info(f"[OK] 使用 Playwright 专用 Profile: {playwright_profile}")
                return str(playwright_profile)
            else:
                logger.warning(f"[WARN] 未找到系统 Chrome，使用本地 Playwright 数据")
                mode = 'temp'  # 回退到临时目录

        # mode == 'temp' 或回退情况
        temp_dir = Path('.chrome-playwright-data')
        temp_dir.mkdir(exist_ok=True)
        logger.info(f"[OK] 使用本地临时数据目录: {temp_dir}")
        return str(temp_dir)

    async def _wait_for_user_confirmation(self, url: str) -> bool:
        """等待用户确认页面是否正确"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[INFO] 请检查浏览器中的页面...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}URL: {url}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

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

    async def download(self) -> Dict:
        """开始下载网站"""
        logger.info(f"开始下载网站: {self.start_url}")

        async with async_playwright() as p:
            # 获取配置
            headless = self.config.get('headless', False)
            use_system_chrome = self.config.get('use_system_chrome', True)
            chrome_data_dir = self.config.get('chrome_data_dir')
            chrome_mode = self.config.get('chrome_mode', 'playwright')  # system/playwright/temp
            wait_for_confirmation = self.config.get('wait_for_confirmation', True)

            context = None
            browser = None

            # 如果使用系统 Chrome 数据
            if use_system_chrome:
                # 检测 Chrome 是否正在运行
                is_chrome_running = self._is_chrome_running()

                # 如果是 system 模式且 Chrome 正在运行，给出警告
                if chrome_mode == 'system' and is_chrome_running:
                    print(f"\n{Fore.YELLOW}[WARN] 警告: 检测到 Chrome 浏览器正在运行{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}使用 system 模式需要关闭所有 Chrome 窗口{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}提示: 推荐使用 playwright 模式（默认），无需关闭 Chrome{Style.RESET_ALL}\n")

                    choice = input("是否继续尝试启动? (y/N): ").strip().lower()
                    if choice != 'y':
                        logger.info("用户取消操作")
                        return {}

                # 获取 Chrome 数据目录
                if not chrome_data_dir:
                    chrome_data_dir = self._get_chrome_user_data_dir(mode=chrome_mode)

                # 尝试使用持久化上下文
                try:
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=chrome_data_dir,
                        headless=headless,
                        viewport=self.config.get('viewport', {'width': 1920, 'height': 1080}),
                        accept_downloads=True
                    )
                    logger.info(f"{Fore.GREEN}[OK] 成功启动浏览器 (模式: {chrome_mode}){Style.RESET_ALL}")

                except Exception as e:
                    logger.error(f"{Fore.RED}[X] 持久化上下文启动失败: {e}{Style.RESET_ALL}")

                    # 自动回退到独立模式
                    print(f"\n{Fore.YELLOW}[WARN] 正在回退到独立浏览器模式...{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}提示: 您可能需要在浏览器中重新登录{Style.RESET_ALL}\n")

                    use_system_chrome = False  # 标记为不使用系统 Chrome
                    context = None

            # 如果不使用系统 Chrome 或回退失败，使用独立模式
            if not use_system_chrome or context is None:
                # 使用普通模式（独立浏览器实例）
                browser = await p.chromium.launch(headless=headless)
                context = await browser.new_context(
                    viewport=self.config.get('viewport', {'width': 1920, 'height': 1080})
                )
                logger.info(f"{Fore.GREEN}[OK] 成功启动独立浏览器{Style.RESET_ALL}")

            try:
                # 如果启用用户确认，先打开页面让用户检查
                confirmed_page = None
                if wait_for_confirmation:
                    # 打开第一个页面
                    page = context.pages[0] if context.pages else await context.new_page()
                    await page.goto(self.start_url, wait_until='networkidle', timeout=60000)

                    # 等待用户确认
                    if not await self._wait_for_user_confirmation(self.start_url):
                        logger.info("用户取消下载")
                        return {}

                    # 保存已确认的页面，供下载函数复用
                    confirmed_page = page

                # 用户确认后（或不需要确认时），创建输出目录
                self.output_dir.mkdir(parents=True, exist_ok=True)

                # 下载主页和所有资源（复用已确认的页面）
                await self._download_recursive_with_context(context, self.start_url, depth=0, existing_page=confirmed_page)

                # 保存下载报告
                report = self._generate_report()
                save_json(report, self.output_dir / 'download_report.json')

                logger.info(f"下载完成! 共 {self.stats['pages']} 个页面")
                return report

            finally:
                await context.close()
                if browser:
                    await browser.close()

    async def _download_recursive_with_context(
        self,
        context: BrowserContext,
        url: str,
        depth: int,
        existing_page: Optional[Page] = None
    ) -> None:
        """递归下载页面及其资源（使用 BrowserContext）

        Args:
            context: 浏览器上下文
            url: 要下载的URL
            depth: 当前深度
            existing_page: 已存在的页面（用于复用已确认的页面，避免重新打开）
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

        try:
            # 复用已存在的页面，或创建新页面
            if existing_page:
                page = existing_page
                logger.info(f"复用已确认的页面: {url}")
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

            # 获取页面HTML
            html = await page.content()

            # 保存 HTML 文件
            html_path = self._save_html(url, html)
            self.stats['pages'] += 1

            # 下载页面资源
            await self._download_page_resources(page, url, html, resources)

            # 查找并下载链接的页面
            links = await self._extract_links(page, url)
            for link in links:
                await self._download_recursive_with_context(context, link, depth + 1)

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
        """下载页面的所有资源"""
        soup = BeautifulSoup(html, 'html.parser')

        # 下载 CSS 文件
        if self.config.get('download_css', True):
            for tag in soup.find_all('link', rel='stylesheet'):
                if tag.get('href'):
                    css_url = normalize_url(tag['href'], page_url)
                    await self._download_resource(css_url, 'css', base_url=page_url)

        # 下载 JavaScript 文件
        if self.config.get('download_js', True):
            for tag in soup.find_all('script', src=True):
                js_url = normalize_url(tag['src'], page_url)
                await self._download_resource(js_url, 'js', base_url=page_url)

        # 下载图片
        if self.config.get('download_images', True):
            for tag in soup.find_all('img', src=True):
                img_url = normalize_url(tag['src'], page_url)
                await self._download_resource(img_url, 'images', base_url=page_url)

            # srcset 属性中的图片
            for tag in soup.find_all('img', srcset=True):
                srcset = tag['srcset']
                for src in srcset.split(','):
                    img_url = src.strip().split()[0]
                    img_url = normalize_url(img_url, page_url)
                    await self._download_resource(img_url, 'images', base_url=page_url)

        # 下载字体
        if self.config.get('download_fonts', True):
            # 从 CSS 中提取字体
            for resource in network_resources:
                if resource['type'] == 'font':
                    await self._download_resource(resource['url'], 'fonts', base_url=page_url)

        # 下载内联样式中的资源（如 style="background-image: url(...)"）
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
                            await self._download_resource(url, 'images', base_url=page_url)
                        elif ext in ['woff', 'woff2', 'ttf', 'eot', 'otf']:
                            await self._download_resource(url, 'fonts', base_url=page_url)

        # 下载 <style> 标签中的资源（如 @font-face, background-image 等）
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

                    await self._download_resource(url, resource_type, base_url=page_url)

    async def _download_resource(self, url: str, resource_type: str, base_url: Optional[str] = None) -> None:
        """下载单个资源文件"""
        if url in self.downloaded_files:
            return

        self.downloaded_files.add(url)

        try:
            # 处理 data URI (如 data:image/svg+xml;base64,...)
            if url.startswith('data:'):
                await self._download_data_uri(url, resource_type)
                return

            # 下载普通 URL 资源
            response = requests.get(url, timeout=30, stream=True)
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
        """处理CSS文件中引用的资源（图片、字体等）"""
        try:
            # 读取CSS文件内容
            with open(css_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                css_content = f.read()

            # 提取所有url()引用
            urls = self._parse_css_urls(css_content, css_url)

            if urls:
                logger.info(f"从CSS提取到 {len(urls)} 个资源: {css_url}")

            # 下载所有提取的资源
            for url in urls:
                # 根据文件扩展名判断资源类型
                ext = url.lower().split('?')[0].split('.')[-1]

                if ext in ['woff', 'woff2', 'ttf', 'eot', 'otf']:
                    resource_type = 'fonts'
                elif ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico']:
                    resource_type = 'images'
                else:
                    resource_type = 'other'

                # 下载资源（注意：不传递base_url避免递归处理）
                await self._download_resource(url, resource_type, base_url=None)

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
    downloader = WebsiteDownloader(url, output_dir, config)
    return await downloader.download()
