"""
项目重构和生成模块 - 基于检测到的技术栈生成可运行的项目
"""

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .utils import create_directory_structure, save_json
import config

logger = logging.getLogger(__name__)


class ProjectReconstructor:
    """项目重构器 - 将下载的网站转换为可运行的项目"""

    def __init__(self, source_dir: Path, output_dir: Path, tech_report: Dict, force_static: bool = False):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.tech_report = tech_report
        self.detected_tech = tech_report.get('detected_technologies', {})
        self.force_static = force_static  # 强制生成静态项目

    def reconstruct(self) -> Dict:
        """重构项目"""
        logger.info("开始项目重构...")

        # 确定项目类型
        project_type = self._determine_project_type()
        logger.info(f"项目类型: {project_type}")

        # 创建项目结构
        if project_type == 'react':
            self._create_react_project()
        elif project_type == 'vue':
            self._create_vue_project()
        elif project_type == 'next':
            self._create_next_project()
        elif project_type == 'static':
            self._create_static_project()
        else:
            self._create_generic_project()

        # 生成报告
        report = {
            'project_type': project_type,
            'output_directory': str(self.output_dir),
            'structure_created': True,
            'next_steps': self._get_next_steps(project_type)
        }

        logger.info("项目重构完成!")
        return report

    def _determine_project_type(self) -> str:
        """确定项目类型"""
        # 如果用户强制要求静态项目
        if self.force_static:
            logger.info("用户指定 --static-only,将生成纯静态项目")
            return 'static'

        # 检查是否有完整的构建产物(已下载的完整网站)
        # 如果下载了 HTML 文件,优先生成静态项目
        html_files = list(self.source_dir.rglob('*.html'))
        js_files = list(self.source_dir.rglob('*.js'))

        # 如果有 HTML 文件,说明是完整下载的网站,生成静态项目
        if html_files:
            logger.info(f"检测到 {len(html_files)} 个 HTML 文件,将生成静态项目")
            return 'static'

        # 如果只有 JS/框架特征但没有 HTML,可能是源码项目
        frameworks = self.detected_tech.get('frameworks', [])

        if 'Next.js' in frameworks:
            return 'next'
        elif 'React' in frameworks:
            return 'react'
        elif 'Nuxt.js' in frameworks:
            return 'nuxt'
        elif 'Vue.js' in frameworks:
            return 'vue'
        elif 'Angular' in frameworks:
            return 'angular'
        elif frameworks:
            return 'generic'
        else:
            return 'static'

    def _create_react_project(self) -> None:
        """创建 React 项目结构"""
        logger.info("创建 React 项目结构...")

        # 创建目录结构
        structure = {
            'src': {
                'components': {},
                'pages': {},
                'assets': {
                    'css': {},
                    'images': {},
                    'fonts': {}
                },
                'App.jsx': self._generate_app_jsx(),
                'main.jsx': self._generate_main_jsx(),
                'index.css': ''
            },
            'public': {
                'index.html': self._generate_index_html()
            },
            'package.json': self._generate_package_json('react'),
            'vite.config.js': self._generate_vite_config(),
            '.gitignore': self._generate_gitignore(),
            '.npmrc': self._generate_npmrc(),
            'README.md': self._generate_readme('react')
        }

        create_directory_structure(self.output_dir, structure)

        # 复制静态资源
        self._copy_assets()

        # 复制 HTML 和提取组件
        self._extract_components_from_html()

    def _create_vue_project(self) -> None:
        """创建 Vue 项目结构"""
        logger.info("创建 Vue 项目结构...")

        structure = {
            'src': {
                'components': {},
                'views': {},
                'assets': {
                    'css': {},
                    'images': {},
                    'fonts': {}
                },
                'App.vue': self._generate_app_vue(),
                'main.js': self._generate_main_js_vue(),
            },
            'public': {
                'index.html': self._generate_index_html()
            },
            'package.json': self._generate_package_json('vue'),
            'vite.config.js': self._generate_vite_config_vue(),
            '.gitignore': self._generate_gitignore(),
            '.npmrc': self._generate_npmrc(),
            'README.md': self._generate_readme('vue')
        }

        create_directory_structure(self.output_dir, structure)
        self._copy_assets()

    def _create_next_project(self) -> None:
        """创建 Next.js 项目结构"""
        logger.info("创建 Next.js 项目结构...")

        structure = {
            'app': {
                'page.tsx': self._generate_next_page(),
                'layout.tsx': self._generate_next_layout(),
                'globals.css': ''
            },
            'components': {},
            'public': {
                'images': {},
                'fonts': {}
            },
            'package.json': self._generate_package_json('next'),
            'next.config.js': self._generate_next_config(),
            'tsconfig.json': self._generate_tsconfig(),
            '.gitignore': self._generate_gitignore(),
            '.npmrc': self._generate_npmrc(),
            'README.md': self._generate_readme('next')
        }

        create_directory_structure(self.output_dir, structure)
        self._copy_assets()

    def _create_static_project(self) -> None:
        """创建静态网站项目 - 只保留 HTML 和 CSS"""
        logger.info("创建纯静态网站项目(HTML + CSS)...")

        # 创建目录结构
        (self.output_dir / 'css').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'images').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'fonts').mkdir(parents=True, exist_ok=True)

        # 在保留UI交互模式下创建js目录
        if config.DOWNLOAD_CONFIG.get('keep_ui_interactions', False):
            (self.output_dir / 'js').mkdir(parents=True, exist_ok=True)

        # ===== 重要：先复制所有资源，再处理 HTML =====
        # 这样处理 HTML 时可以检查文件是否存在

        # 复制图片
        image_patterns = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.webp', '*.ico']
        for pattern in image_patterns:
            for img_file in self.source_dir.rglob(pattern):
                dest = self.output_dir / 'images' / img_file.name
                try:
                    shutil.copy2(img_file, dest)
                except Exception as e:
                    logger.warning(f"复制图片失败 {img_file}: {e}")

        # 复制字体文件
        font_patterns = ['*.woff', '*.woff2', '*.ttf', '*.eot', '*.otf']
        for pattern in font_patterns:
            for font_file in self.source_dir.rglob(pattern):
                dest = self.output_dir / 'fonts' / font_file.name
                try:
                    shutil.copy2(font_file, dest)
                except Exception as e:
                    logger.warning(f"复制字体失败 {font_file}: {e}")

        # 处理 CSS 文件（重写CDN引用）
        css_files = list(self.source_dir.rglob('*.css'))
        for css_file in css_files:
            dest = self.output_dir / 'css' / css_file.name
            self._process_css_file(css_file, dest)

        # 检查并复制那些扩展名是 .html 但内容是 CSS 的文件（如字体CSS）
        for html_file in self.source_dir.rglob('*.html'):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read(200)  # 只读前200字符检查
                # 如果文件以 @font-face 或其他CSS特征开头，当作CSS处理
                if content.strip().startswith(('@font-face', '@charset', '@import', '/*')):
                    # 生成CSS文件名（使用fonts-作为前缀避免冲突）
                    css_name = 'fonts-' + html_file.stem + '.css'
                    dest = self.output_dir / 'css' / css_name
                    shutil.copy2(html_file, dest)
                    logger.info(f"已复制CSS文件(来自.html): {css_name}")
            except Exception as e:
                logger.debug(f"检查HTML文件是否为CSS失败 {html_file}: {e}")

        # 最后处理 HTML 文件（此时所有资源已经复制完成）
        html_files = list(self.source_dir.rglob('*.html'))
        for html_file in html_files:
            self._copy_html_without_js(html_file)

        # 复制 JavaScript 文件（仅在 keep_ui_interactions 模式）
        if config.DOWNLOAD_CONFIG.get('keep_ui_interactions', False):
            js_files = list(self.source_dir.rglob('*.js'))
            js_count = 0
            for js_file in js_files:
                dest = self.output_dir / 'js' / js_file.name
                try:
                    shutil.copy2(js_file, dest)
                    js_count += 1
                    logger.debug(f"已复制 JS: {js_file.name}")
                except Exception as e:
                    logger.warning(f"复制 JS 失败 {js_file}: {e}")
            if js_count > 0:
                logger.info(f"已复制 {js_count} 个 JavaScript 文件")

        # 生成 README
        readme_path = self.output_dir / 'README.md'
        readme_path.write_text(self._generate_static_readme(), encoding='utf-8')

        logger.info("静态项目创建完成!")

    def _should_keep_script(self, script_tag, script_content: str = None) -> bool:
        """智能判断是否保留JavaScript脚本

        Args:
            script_tag: BeautifulSoup script标签对象
            script_content: 脚本内容字符串

        Returns:
            True保留, False移除
        """
        # 白名单：常见UI库
        ui_libraries = ['jquery', 'bootstrap', 'swiper', 'slick', 'owl.carousel',
                        'aos', 'gsap', 'anime', 'wow', 'scrollreveal', 'lightbox',
                        'fancybox', 'magnific-popup', 'photoswipe', 'slimselect',
                        'select2', 'choices', 'flatpickr', 'pikaday', 'moment',
                        'chart', 'echarts', 'd3', 'three', 'lottie']

        # 黑名单：追踪和业务
        blacklist = ['google-analytics', 'gtag', 'baidu', '_hmt', 'sentry',
                     'hotjar', 'mixpanel', 'amplitude', 'facebook.net', 'doubleclick',
                     'analytics', 'tracking', 'metrics', 'aplus_queue',
                     'umeng', 'cnzz', 'statcounter', 'segment.com', 'clarity.ms']

        # 检查src属性
        src = script_tag.get('src', '').lower()

        # 白名单匹配
        if src and any(lib in src for lib in ui_libraries):
            logger.debug(f"保留UI库脚本: {src[:100]}")
            return True

        # 特殊处理：Slardar/ByteDance前端监控（可能影响UI渲染）
        if src and ('slardar' in src or 'ibytedapm' in src):
            logger.debug(f"保留前端性能监控脚本: {src[:100]}")
            return True

        # 黑名单匹配
        if src and any(track in src for track in blacklist):
            logger.debug(f"移除追踪脚本: {src[:100]}")
            return False

        # 检查内联脚本内容
        if script_content:
            content_lower = script_content.lower()

            # 保留：UI组件初始化
            ui_patterns = ['new swiper', 'carousel(', 'modal(', 'dropdown(',
                           'tooltip(', 'popover(', 'tab(', 'collapse(',
                           'accordion(', 'slider(', 'gallery(', 'lightbox(',
                           'aos.init', 'wow.init']
            if any(pattern in content_lower for pattern in ui_patterns):
                logger.debug("保留UI初始化脚本")
                return True

            # 移除：API调用和追踪
            api_patterns = ['fetch(', 'axios.', '$.ajax', 'xmlhttprequest',
                            'sendevent', 'sendbeacon', 'track(', 'analytics',
                            'aplus_queue', 'gtag(', '_hmt.push']
            if any(pattern in content_lower for pattern in api_patterns):
                logger.debug("移除API/追踪脚本")
                return False

        # 默认策略：保留（保守）
        return True

    def _copy_html_without_js(self, html_file: Path) -> None:
        """复制 HTML 文件并移除所有 JavaScript 引用"""
        from bs4 import BeautifulSoup

        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 检查是否是真正的 HTML (包含 DOCTYPE 或 <html> 标签)
            if not ('<!DOCTYPE' in html_content or '<html' in html_content.lower()):
                logger.debug(f"跳过非 HTML 文件: {html_file}")
                return

            soup = BeautifulSoup(html_content, 'html.parser')

            # 进一步验证是否包含基本的 HTML 结构
            if not soup.find('html') and not soup.find('body'):
                logger.debug(f"跳过无效 HTML: {html_file}")
                return

            # 智能处理脚本
            keep_ui = config.DOWNLOAD_CONFIG.get('keep_ui_interactions', False)

            if keep_ui:
                # 智能过滤：保留UI库，移除追踪和业务逻辑
                scripts_to_remove = []
                for script in soup.find_all('script'):
                    script_content = script.string if script.string else ''
                    if not self._should_keep_script(script, script_content):
                        scripts_to_remove.append(script)

                for script in scripts_to_remove:
                    script.decompose()

                logger.info(f"智能过滤: 保留 {len(soup.find_all('script'))} 个UI脚本, 移除 {len(scripts_to_remove)} 个追踪/业务脚本")

                # 选择性保留UI事件处理器
                ui_events = ['onclick', 'onchange', 'onsubmit', 'oninput', 'onfocus', 'onblur']
                for tag in soup.find_all(True):
                    attrs_to_remove = []
                    for attr in tag.attrs:
                        if attr.startswith('on'):
                            # 保留UI事件，移除追踪事件
                            if attr not in ui_events:
                                attrs_to_remove.append(attr)
                    for attr in attrs_to_remove:
                        del tag[attr]
            else:
                # 传统模式：移除所有 <script> 标签
                for script in soup.find_all('script'):
                    script.decompose()

                # 移除内联事件处理器(onclick, onload 等)
                for tag in soup.find_all(True):
                    attrs_to_remove = [attr for attr in tag.attrs if attr.startswith('on')]
                    for attr in attrs_to_remove:
                        del tag[attr]

            # 修复资源路径
            # 修复 CSS 链接（包括CDN链接）
            for link in soup.find_all('link', rel='stylesheet'):
                if link.get('href'):
                    href = str(link.get('href', ''))

                    # 处理外部CDN链接
                    if href.startswith(('http://', 'https://')):
                        filename = href.split('/')[-1].split('?')[0]
                        if filename.endswith('.css'):
                            link['href'] = f'./css/{filename}'
                            logger.debug(f"本地化CSS: {href[:50]} -> ./css/{filename}")
                        else:
                            # 非CSS的外部链接（如字体CDN），直接移除避免CORS
                            link.decompose()
                            continue
                    # 处理协议相对URL (//example.com/...)
                    elif href.startswith('//'):
                        filename = href.split('/')[-1].split('?')[0]
                        if filename.endswith('.css'):
                            link['href'] = f'./css/{filename}'
                    # 处理那些指向 .html 但实际是 CSS 的链接
                    elif 'font' in href.lower() and href.endswith('index.html'):
                        # 字体CSS文件，使用我们复制时生成的新文件名
                        link['href'] = './css/fonts-index.css'
                    # 处理相对路径CSS
                    elif href.endswith('.css'):
                        filename = href.split('/')[-1].split('?')[0]
                        link['href'] = f'./css/{filename}'
                    # 如果href是Windows绝对路径，移除link标签
                    elif href.startswith(('E:', 'C:', 'D:')):
                        link.decompose()
                        continue

                # 移除crossorigin属性以避免file://协议下的CORS错误
                if link.get('crossorigin'):
                    del link['crossorigin']
                    logger.debug(f"已移除crossorigin属性: {link.get('href', '')[:50]}")

            # 移除所有预加载、预连接等可能引起CORS的link标签
            for link in soup.find_all('link'):
                rel = link.get('rel', [])
                if isinstance(rel, list):
                    rel = ' '.join(rel)
                rel = str(rel).lower()

                # 移除这些类型的链接：prefetch, preload, preconnect, dns-prefetch等
                if any(keyword in rel for keyword in ['prefetch', 'preload', 'preconnect', 'dns-prefetch', 'prerender']):
                    link.decompose()
                    logger.debug(f"已移除预加载链接: rel={rel}")
                # 移除favicon的CDN链接（如果有）
                elif 'icon' in rel and link.get('href', '').startswith('http'):
                    link.decompose()
                    logger.debug(f"已移除CDN favicon")

            # 修复图片路径（包括CDN图片）
            for img in soup.find_all('img'):
                if img.get('src'):
                    src = img['src']
                    # 跳过data URI
                    if src.startswith('data:'):
                        continue
                    # 处理所有其他图片（包括CDN）
                    filename = src.split('/')[-1].split('?')[0].split('#')[0]
                    if filename and '.' in filename:  # 确保有文件名和扩展名
                        img['src'] = f'./images/{filename}'
                        if src.startswith(('http://', 'https://')):
                            logger.debug(f"本地化图片: {src[:50]} -> ./images/{filename}")

            # 修复内联样式中的url()引用
            for tag in soup.find_all(True):
                if tag.get('style'):
                    style = tag['style']
                    original_style = style

                    # 找到所有url()中的图片URL并检查文件是否存在
                    def replace_inline_url(match):
                        filename = match.group(1)
                        # 检查文件是否在images目录中
                        img_path = self.output_dir / 'images' / filename
                        if img_path.exists():
                            return f'url(./images/{filename})'
                        else:
                            # 文件不存在，移除background-image避免404错误
                            logger.warning(f"内联样式图片不存在，移除引用: {filename}")
                            return 'none'

                    # 匹配 url(https://example.com/.../image.png) 格式
                    new_style = re.sub(
                        r'url\s*\(\s*["\']?https?://[^)]+?/([^/)"\']+\.(png|jpg|jpeg|gif|svg|webp|ico))["\']?\s*\)',
                        replace_inline_url,
                        style,
                        flags=re.IGNORECASE
                    )
                    if new_style != original_style:
                        tag['style'] = new_style
                        logger.debug(f"修复内联样式url()")

            # 修复<style>标签内的CDN URL（重要：处理@font-face等）
            for style_tag in soup.find_all('style'):
                if style_tag.string:
                    css_content = str(style_tag.string)
                    original_content = css_content

                    # 重写字体URL为本地路径
                    css_content = re.sub(
                        r'url\s*\(\s*["\']?https?://[^)]+?/([^/)"\']+\.(woff|woff2|ttf|eot|otf))["\']?\s*\)',
                        r'url(./fonts/\1)',
                        css_content,
                        flags=re.IGNORECASE
                    )

                    # 重写图片URL为本地路径
                    css_content = re.sub(
                        r'url\s*\(\s*["\']?https?://[^)]+?/([^/)"\']+\.(png|jpg|jpeg|gif|svg|webp|ico))["\']?\s*\)',
                        r'url(./images/\1)',
                        css_content,
                        flags=re.IGNORECASE
                    )

                    if css_content != original_content:
                        style_tag.string = css_content
                        logger.info(f"已重写<style>标签中的CDN URL")

            # 修复 JavaScript 路径（仅在保留UI交互模式）
            if keep_ui:
                for script in soup.find_all('script', src=True):
                    src = script['src']
                    # 处理外部CDN链接
                    if src.startswith(('http://', 'https://')):
                        filename = src.split('/')[-1].split('?')[0]
                        if filename.endswith('.js'):
                            script['src'] = f'./js/{filename}'
                            logger.debug(f"重写JS路径: {src[:50]} -> ./js/{filename}")
                    # 处理协议相对URL (//example.com/...)
                    elif src.startswith('//'):
                        filename = src.split('/')[-1].split('?')[0]
                        if filename.endswith('.js'):
                            script['src'] = f'./js/{filename}'
                    # 处理相对路径
                    elif not src.startswith('data:'):
                        filename = src.split('/')[-1].split('?')[0]
                        if filename.endswith('.js'):
                            script['src'] = f'./js/{filename}'

            # 修正内联脚本中的CDN配置（仅在保留UI交互模式）
            if keep_ui:
                for script in soup.find_all('script'):
                    if script.string and '__assetPrefix__' in script.string:
                        # 将CDN路径改为相对路径
                        original_content = script.string
                        new_content = re.sub(
                            r"__assetPrefix__\s*=\s*['\"]https?://[^'\"]+['\"]",
                            "__assetPrefix__ = '.'",
                            original_content
                        )
                        if new_content != original_content:
                            script.string = new_content
                            logger.info("已修正 __assetPrefix__ 配置为本地路径")

            # 移除CDN的preconnect链接（已无意义）
            for link in soup.find_all('link', rel='preconnect'):
                link.decompose()

            # 保存处理后的 HTML
            # 优先使用包含 'login' 的 HTML 作为主页 index.html
            html_path_str = str(html_file).lower()
            is_login_page = 'login' in html_path_str and 'auth' in html_path_str

            if is_login_page:
                # 登录页面：强制作为 index.html
                output_name = 'index.html'
                output_path = self.output_dir / output_name
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(str(soup.prettify()))
                logger.info(f"✓ 已设置登录页面为主页: {output_name} (已移除所有 JavaScript)")
            else:
                # 其他页面：仅在 index.html 不存在时才作为主页
                if not (self.output_dir / 'index.html').exists():
                    output_name = 'index.html'
                    output_path = self.output_dir / output_name
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(str(soup.prettify()))
                    logger.info(f"已处理 HTML: {output_name} (已移除所有 JavaScript)")
                else:
                    # index.html 已存在，跳过这个页面（避免覆盖登录页面）
                    logger.debug(f"跳过: {html_file} (index.html 已存在)")

        except Exception as e:
            logger.warning(f"处理 HTML 失败 {html_file}: {e}")

    def _process_css_file(self, css_file: Path, dest: Path) -> None:
        """处理CSS文件，重写CDN url()引用为本地路径"""
        try:
            # 读取CSS文件内容
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 重写图片URL: 检查文件是否存在
            def replace_css_image_url(match):
                filename = match.group(1)
                img_path = self.output_dir / 'images' / filename
                if img_path.exists():
                    return f'url(../images/{filename})'
                else:
                    # 文件不存在，保留data URI占位或注释掉
                    logger.warning(f"CSS中的图片不存在: {filename}")
                    return 'none'  # 或 'url(data:image/png;base64,)'

            content = re.sub(
                r'url\s*\(\s*["\']?https?://[^)]+?/([^/)"\']+\.(png|jpg|jpeg|gif|svg|webp|ico))["\']?\s*\)',
                replace_css_image_url,
                content,
                flags=re.IGNORECASE
            )

            # 重写字体URL: 检查文件是否存在
            def replace_css_font_url(match):
                filename = match.group(1)
                font_path = self.output_dir / 'fonts' / filename
                if font_path.exists():
                    return f'url(../fonts/{filename})'
                else:
                    logger.warning(f"CSS中的字体不存在: {filename}")
                    # 字体文件缺失，保留原始引用或移除
                    return ''  # 移除该字体引用

            content = re.sub(
                r'url\s*\(\s*["\']?https?://[^)]+?/([^/)"\']+\.(woff|woff2|ttf|eot|otf))["\']?\s*\)',
                replace_css_font_url,
                content,
                flags=re.IGNORECASE
            )

            # 重写其他CSS资源（一般CSS文件很少引用其他CSS）
            content = re.sub(
                r'url\s*\(\s*["\']?https?://[^)]+?/([^/)"\']+\.css)["\']?\s*\)',
                r'url(./\1)',
                content,
                flags=re.IGNORECASE
            )

            # 保存处理后的CSS
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(content)

            if content != original_content:
                logger.info(f"已重写CSS中的CDN引用: {css_file.name}")
            else:
                logger.debug(f"已复制CSS(无需重写): {css_file.name}")

        except Exception as e:
            logger.warning(f"处理CSS文件失败 {css_file}: {e}")
            # 如果处理失败，回退到直接复制
            try:
                shutil.copy2(css_file, dest)
            except Exception as e2:
                logger.error(f"复制CSS文件也失败 {css_file}: {e2}")

    def _create_generic_project(self) -> None:
        """创建通用项目结构"""
        logger.info("创建通用项目结构...")

        structure = {
            'src': {
                'assets': {
                    'css': {},
                    'js': {},
                    'images': {},
                    'fonts': {}
                },
                'index.html': ''
            },
            'package.json': self._generate_package_json('generic'),
            '.gitignore': self._generate_gitignore(),
            '.npmrc': self._generate_npmrc(),
            'README.md': self._generate_readme('generic')
        }

        create_directory_structure(self.output_dir, structure)
        self._copy_assets()

    def _copy_assets(self) -> None:
        """复制静态资源到新项目"""
        logger.info("复制静态资源...")

        asset_mapping = {
            '*.css': 'src/assets/css',
            '*.js': 'src/assets/js',
            '*.png': 'src/assets/images',
            '*.jpg': 'src/assets/images',
            '*.jpeg': 'src/assets/images',
            '*.gif': 'src/assets/images',
            '*.svg': 'src/assets/images',
            '*.woff': 'src/assets/fonts',
            '*.woff2': 'src/assets/fonts',
            '*.ttf': 'src/assets/fonts',
            '*.eot': 'src/assets/fonts'
        }

        for pattern, dest_dir in asset_mapping.items():
            dest_path = self.output_dir / dest_dir
            dest_path.mkdir(parents=True, exist_ok=True)

            for file in self.source_dir.rglob(pattern):
                try:
                    shutil.copy2(file, dest_path / file.name)
                except Exception as e:
                    logger.warning(f"复制文件失败 {file}: {e}")

    def _extract_components_from_html(self) -> None:
        """从 HTML 中提取组件 (简化版)"""
        # 这里可以实现更复杂的组件提取逻辑
        # 暂时只是复制 HTML 文件
        html_files = list(self.source_dir.rglob('*.html'))
        if html_files:
            pages_dir = self.output_dir / 'src' / 'pages'
            pages_dir.mkdir(parents=True, exist_ok=True)

            for html_file in html_files[:10]:  # 限制数量
                try:
                    shutil.copy2(html_file, pages_dir / html_file.name)
                except Exception as e:
                    logger.warning(f"复制 HTML 失败 {html_file}: {e}")

    # ===== 模板生成函数 =====

    def _generate_package_json(self, project_type: str) -> str:
        """生成 package.json"""
        base_package = {
            'name': 'cloned-website',
            'version': '1.0.0',
            'description': 'Cloned website project',
            'scripts': {},
            'dependencies': {},
            'devDependencies': {}
        }

        if project_type == 'react':
            base_package['scripts'] = {
                'dev': 'vite',
                'build': 'vite build',
                'preview': 'vite preview'
            }
            base_package['dependencies'] = {
                'react': '^18.2.0',
                'react-dom': '^18.2.0'
            }
            base_package['devDependencies'] = {
                'vite': '^5.0.0',
                '@vitejs/plugin-react': '^4.2.0'
            }

        elif project_type == 'vue':
            base_package['scripts'] = {
                'dev': 'vite',
                'build': 'vite build',
                'preview': 'vite preview'
            }
            base_package['dependencies'] = {
                'vue': '^3.3.0'
            }
            base_package['devDependencies'] = {
                'vite': '^5.0.0',
                '@vitejs/plugin-vue': '^4.5.0'
            }

        elif project_type == 'next':
            base_package['scripts'] = {
                'dev': 'next dev',
                'build': 'next build',
                'start': 'next start'
            }
            base_package['dependencies'] = {
                'next': '^14.0.0',
                'react': '^18.2.0',
                'react-dom': '^18.2.0'
            }

        # 添加检测到的依赖
        detected_libs = self.detected_tech.get('ui_libraries', [])
        if 'Tailwind CSS' in detected_libs:
            base_package['devDependencies']['tailwindcss'] = '^3.4.0'
            base_package['devDependencies']['autoprefixer'] = '^10.4.0'
            base_package['devDependencies']['postcss'] = '^8.4.0'

        if 'Bootstrap' in detected_libs:
            base_package['dependencies']['bootstrap'] = '^5.3.0'

        return json.dumps(base_package, indent=2, ensure_ascii=False)

    def _generate_app_jsx(self) -> str:
        """生成 React App.jsx"""
        return '''import React from 'react'
import './index.css'

function App() {
  return (
    <div className="App">
      <h1>Cloned Website</h1>
      <p>项目已成功创建,请根据需要修改组件。</p>
    </div>
  )
}

export default App
'''

    def _generate_main_jsx(self) -> str:
        """生成 React main.jsx"""
        return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''

    def _generate_app_vue(self) -> str:
        """生成 Vue App.vue"""
        return '''<template>
  <div id="app">
    <h1>Cloned Website</h1>
    <p>项目已成功创建,请根据需要修改组件。</p>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
}
</style>
'''

    def _generate_main_js_vue(self) -> str:
        """生成 Vue main.js"""
        return '''import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
'''

    def _generate_next_page(self) -> str:
        """生成 Next.js page.tsx"""
        return '''export default function Home() {
  return (
    <main>
      <h1>Cloned Website</h1>
      <p>项目已成功创建,请根据需要修改页面。</p>
    </main>
  )
}
'''

    def _generate_next_layout(self) -> str:
        """生成 Next.js layout.tsx"""
        return '''import './globals.css'

export const metadata = {
  title: 'Cloned Website',
  description: 'Generated from website clone',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  )
}
'''

    def _generate_index_html(self) -> str:
        """生成 index.html"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cloned Website</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
'''

    def _generate_vite_config(self) -> str:
        """生成 Vite 配置"""
        return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
'''

    def _generate_vite_config_vue(self) -> str:
        """生成 Vue Vite 配置"""
        return '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
})
'''

    def _generate_next_config(self) -> str:
        """生成 Next.js 配置"""
        return '''/** @type {import('next').NextConfig} */
const nextConfig = {}

module.exports = nextConfig
'''

    def _generate_tsconfig(self) -> str:
        """生成 TypeScript 配置"""
        tsconfig = {
            'compilerOptions': {
                'target': 'ES2020',
                'lib': ['ES2020', 'DOM', 'DOM.Iterable'],
                'jsx': 'preserve',
                'module': 'ESNext',
                'moduleResolution': 'bundler',
                'resolveJsonModule': True,
                'allowJs': True,
                'strict': True,
                'esModuleInterop': True,
                'skipLibCheck': True,
                'forceConsistentCasingInFileNames': True
            },
            'include': ['app', 'components'],
            'exclude': ['node_modules']
        }
        return json.dumps(tsconfig, indent=2)

    def _generate_gitignore(self) -> str:
        """生成 .gitignore"""
        return '''node_modules
.next
dist
.cache
.env
.env.local
*.log
package-lock.json
'''

    def _generate_npmrc(self) -> str:
        """生成 .npmrc 配置"""
        return '''# npm 配置
# 使用淘宝镜像加速(可选)
# registry=https://registry.npmmirror.com
'''

    def _generate_static_readme(self) -> str:
        """生成静态项目的 README.md"""
        keep_ui = config.DOWNLOAD_CONFIG.get('keep_ui_interactions', False)

        if keep_ui:
            js_section = '''### JavaScript 智能保留
- 保留了 UI 库脚本 (jQuery, Bootstrap, Swiper 等)
- 保留了基础 UI 事件处理器 (onclick, onchange 等)
- 移除了追踪代码 (Google Analytics, 百度统计等)
- 移除了业务逻辑和 API 调用
- 页面的基础交互功能 (按钮、菜单、轮播等) 可以正常使用
- 需要后端支持的功能 (登录、提交表单等) 将无法工作'''
        else:
            js_section = '''### JavaScript 已移除
- 所有 `<script>` 标签已被移除
- 内联事件处理器 (onclick 等) 已被清理
- 页面将无法执行任何交互功能
- 只保留静态展示效果'''

        return f'''# 静态网站项目 (HTML + CSS{' + UI交互' if keep_ui else ''})

## 📋 项目说明
这是一个通过网站复刻工具自动生成的**静态项目**,包含 HTML、CSS{' 和部分 UI 交互脚本' if keep_ui else ',所有 JavaScript 已被移除'}。

## 🎯 检测到的技术栈
{json.dumps(self.detected_tech, indent=2, ensure_ascii=False)}

## 📂 项目结构
```
project/
├── index.html          # 主页面
├── css/               # 所有 CSS 样式文件{'''
├── js/                # JavaScript 文件 (UI库和交互)''' if keep_ui else ''}
├── images/            # 图片资源
├── fonts/             # 字体文件
└── README.md          # 本文件
```

## 🚀 使用方法

### 方法 1: 直接在浏览器打开
直接双击 `index.html` 文件即可在浏览器中查看。

### 方法 2: 使用本地服务器 (推荐)
{'为了UI交互正常工作和避免跨域问题' if keep_ui else '为了避免跨域问题和确保资源正确加载'},建议使用本地服务器:

#### Python 自带服务器
```bash
# 进入项目目录
cd path/to/this/project

# 启动服务器
python -m http.server 8000

# 然后在浏览器打开: http://localhost:8000
```

#### Node.js http-server
```bash
# 安装 (一次性)
npm install -g http-server

# 启动服务器
http-server -p 8000

# 浏览器打开: http://localhost:8000
```

#### VS Code Live Server 插件
1. 在 VS Code 中安装 "Live Server" 插件
2. 右键点击 `index.html`
3. 选择 "Open with Live Server"

## ⚠️ 注意事项

{js_section}

### 适用场景
- 学习网站布局和样式
- 分析 CSS 实现方式
- {'体验基本 UI 交互效果' if keep_ui else '作为设计参考'}
- 静态页面展示

### 资源路径
资源路径已自动修复为相对路径,确保文件结构不变的情况下可以正常加载。

## 💡 如果需要完整功能
如果您需要包含完整 JavaScript 和业务逻辑的版本,请使用以下命令重新下载:
```bash
python main.py clone <URL> --project-type react
```

---

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
'''

    def _generate_readme(self, project_type: str) -> str:
        """生成 README.md"""
        return f'''# Cloned Website Project

## 项目类型
{project_type.upper()}

## 技术栈
{json.dumps(self.detected_tech, indent=2, ensure_ascii=False)}

## 安装依赖
```bash
npm install
```

## 运行项目
```bash
npm run dev
```

## 构建项目
```bash
npm run build
```

## 说明
这是一个通过网站复刻工具自动生成的项目。请根据实际需求进行调整和优化。
'''

    def _get_next_steps(self, project_type: str) -> List[str]:
        """获取下一步操作建议"""
        if project_type == 'static':
            return [
                '1. 进入项目目录',
                '2. 双击 index.html 直接在浏览器打开',
                '3. 或使用本地服务器: python -m http.server 8000',
                '4. 浏览器访问: http://localhost:8000',
                '注意: 已移除所有 JavaScript,仅保留 HTML 和 CSS'
            ]

        steps = [
            '1. 进入项目目录',
            '2. 运行 npm install 安装依赖',
            '3. 运行 npm run dev 启动开发服务器',
            '4. 根据需要调整组件和样式',
            '5. 运行 npm run build 构建生产版本'
        ]

        if 'Tailwind CSS' in self.detected_tech.get('ui_libraries', []):
            steps.append('6. 配置 Tailwind CSS (tailwind.config.js)')

        return steps


def reconstruct_project(source_dir: Path, output_dir: Path, tech_report: Dict, force_static: bool = False) -> Dict:
    """便捷函数: 重构项目"""
    reconstructor = ProjectReconstructor(source_dir, output_dir, tech_report, force_static=force_static)
    return reconstructor.reconstruct()
