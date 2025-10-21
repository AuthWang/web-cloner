"""
网站一比一复刻工具 - 主程序
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except:
        pass

import click
from colorama import init, Fore, Style
from tqdm import tqdm

# 导入配置
from config import (
    ensure_directories,
    DOWNLOADS_DIR,
    PROJECTS_DIR,
    REPORTS_DIR,
    BROWSER_CONFIG,
    DOWNLOAD_CONFIG,
    AI_CONFIG,
    LOG_CONFIG
)

# 导入核心模块
from src.downloader import download_website
from src.detector import detect_tech_stack
from src.reconstructor import reconstruct_project
from src.ai_analyzer import analyze_with_ai
from src.utils import setup_logger, save_json

# 初始化
init(autoreset=True)  # colorama
ensure_directories()

logger = setup_logger('main', LOG_CONFIG['level'])


def print_banner():
    """打印程序横幅"""
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════╗
║                                                       ║
║          网站一比一复刻工具                           ║
║                                                       ║
║     一键复刻任何网站,自动检测技术栈,生成项目         ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """网站一比一复刻工具 - 命令行界面"""
    pass


@cli.command()
@click.argument('url')
@click.option('--output', '-o', default=None, help='输出目录')
@click.option('--max-depth', '-d', default=3, help='最大爬取深度')
@click.option('--max-pages', '-p', default=50, help='最大页面数')
@click.option('--no-images', is_flag=True, help='不下载图片')
@click.option('--no-css', is_flag=True, help='不下载CSS')
@click.option('--no-js', is_flag=True, help='不下载JavaScript')
@click.option('--enable-ai', is_flag=True, help='启用AI辅助分析')
@click.option('--headless/--no-headless', default=False, help='无头模式（默认显示浏览器窗口）')
@click.option('--confirm/--no-confirm', default=True, help='下载前等待用户确认页面（默认开启）')
@click.option('--chrome-data-dir', default=None, help='指定 Chrome 用户数据目录（默认自动检测）')
@click.option('--chrome-mode', type=click.Choice(['system', 'playwright', 'temp']), default='playwright', help='Chrome 数据模式: system(需关闭Chrome)/playwright(推荐)/temp(临时)')
@click.option('--use-browser-data', is_flag=True, help='使用系统浏览器数据(登录状态、Cookies等)')
@click.option('--static-only', is_flag=True, help='强制生成纯静态项目(仅HTML+CSS,移除所有JS)')
def clone(url, output, max_depth, max_pages, no_images, no_css, no_js, enable_ai, headless, confirm, chrome_data_dir, chrome_mode, use_browser_data, static_only):
    """
    完整复刻网站

    URL: 要复刻的网站URL
    """
    print_banner()

    click.echo(f"\n{Fore.GREEN}> 开始复刻网站: {Fore.CYAN}{url}{Style.RESET_ALL}\n")

    # 生成输出目录名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    domain = url.split('//')[-1].split('/')[0].replace(':', '_')
    output_name = output or f"{domain}_{timestamp}"

    download_dir = DOWNLOADS_DIR / output_name
    project_dir = PROJECTS_DIR / output_name
    report_dir = REPORTS_DIR / output_name

    # 配置下载选项
    config = DOWNLOAD_CONFIG.copy()
    config.update(BROWSER_CONFIG)
    config['max_depth'] = max_depth
    config['max_pages'] = max_pages
    config['download_images'] = not no_images
    config['download_css'] = not no_css
    config['download_js'] = not no_js
    config['headless'] = headless
    config['wait_for_confirmation'] = confirm
    config['chrome_mode'] = chrome_mode

    # 如果用户指定了 --use-browser-data，启用浏览器数据共享
    if use_browser_data:
        config['use_system_chrome'] = True

    if chrome_data_dir:
        config['chrome_data_dir'] = chrome_data_dir

    # 显示配置提示
    if config.get('use_system_chrome', False):
        mode_desc = {
            'system': '系统完整数据（需关闭所有 Chrome 窗口）',
            'playwright': 'Playwright 专用 Profile（推荐，无需关闭 Chrome）',
            'temp': '临时目录（每次都需要重新登录）'
        }
        click.echo(f"{Fore.CYAN}[浏览器] 使用浏览器数据，模式: {mode_desc.get(chrome_mode, chrome_mode)}{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.CYAN}[浏览器] 独立浏览器模式（不共享登录状态）{Style.RESET_ALL}")

    if confirm:
        click.echo(f"{Fore.CYAN}[提示] 浏览器将打开目标页面，请确认页面正确后继续{Style.RESET_ALL}")
    click.echo()

    try:
        # 第一步:下载网站
        click.echo(f"{Fore.YELLOW}[1/4] 下载网站资源...{Style.RESET_ALL}")
        download_report = asyncio.run(download_website(url, download_dir, config))

        # 检查用户是否取消
        if not download_report:
            click.echo(f"\n{Fore.YELLOW}[取消] 用户取消了下载操作{Style.RESET_ALL}\n")
            return

        # 创建项目目录（只在确认下载后创建）
        project_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        # 保存下载报告
        save_json(download_report, report_dir / 'download_report.json')

        # 统计错误类型
        failed_downloads = download_report.get('failed_downloads', [])
        critical_errors = [f for f in failed_downloads if f.get('severity') in ('warning', 'error')]
        skipped_resources = [f for f in failed_downloads if f.get('severity') == 'info']

        # 生成下载报告
        total_files = download_report['statistics']['total_files']
        report_parts = [f"下载完成: {total_files} 个文件"]

        if skipped_resources:
            report_parts.append(f"已跳过 {len(skipped_resources)} 个无效资源")

        if critical_errors:
            # 只有真正的错误才显示警告
            click.echo(f"{Fore.YELLOW}[OK] {', '.join(report_parts)}{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}[!] 警告: {len(critical_errors)} 个资源下载失败{Style.RESET_ALL}\n")
        else:
            click.echo(f"{Fore.GREEN}[OK] {', '.join(report_parts)}{Style.RESET_ALL}\n")

        # 第二步:检测技术栈
        click.echo(f"{Fore.YELLOW}[2/4] 检测技术栈...{Style.RESET_ALL}")
        tech_report = detect_tech_stack(download_dir)

        # 保存技术栈报告
        save_json(tech_report, report_dir / 'tech_report.json')

        detected_count = tech_report['summary']['total_technologies']
        click.echo(f"{Fore.GREEN}[OK] 检测到 {detected_count} 项技术{Style.RESET_ALL}\n")

        # 打印检测到的技术
        if tech_report['detected_technologies']:
            click.echo(f"{Fore.CYAN}检测到的技术栈:{Style.RESET_ALL}")
            for category, techs in tech_report['detected_technologies'].items():
                click.echo(f"  - {category}: {', '.join(techs)}")
            click.echo()

        # 第三步:重构项目
        click.echo(f"{Fore.YELLOW}[3/4] 重构并生成项目...{Style.RESET_ALL}")
        if static_only:
            click.echo(f"{Fore.CYAN}  → 使用 --static-only 模式,将生成纯静态项目(仅HTML+CSS){Style.RESET_ALL}")
        project_report = reconstruct_project(download_dir, project_dir, tech_report, force_static=static_only)

        # 保存项目报告
        save_json(project_report, report_dir / 'project_report.json')
        click.echo(f"{Fore.GREEN}[OK] 项目生成完成: {project_report['project_type']}{Style.RESET_ALL}\n")

        # 第四步:AI 辅助分析 (可选)
        if enable_ai:
            click.echo(f"{Fore.YELLOW}[4/4] AI 辅助分析...{Style.RESET_ALL}")
            ai_report = analyze_with_ai(download_report, tech_report, project_report, AI_CONFIG)

            # 保存 AI 分析报告
            save_json(ai_report, report_dir / 'ai_analysis.json')

            if ai_report['ai_enabled']:
                click.echo(f"{Fore.GREEN}[OK] AI 分析完成{Style.RESET_ALL}\n")

                # 打印建议
                suggestions = ai_report['analysis'].get('suggestions', [])
                if suggestions:
                    click.echo(f"{Fore.CYAN}AI 建议:{Style.RESET_ALL}")
                    for i, suggestion in enumerate(suggestions[:10], 1):
                        click.echo(f"  {i}. {suggestion}")
                    click.echo()
            else:
                click.echo(f"{Fore.YELLOW}[OK] 使用规则引擎分析{Style.RESET_ALL}\n")

        # 打印总结
        click.echo(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}[SUCCESS] 复刻完成!{Style.RESET_ALL}\n")
        click.echo(f"{Fore.CYAN}下载目录:{Style.RESET_ALL} {download_dir}")
        click.echo(f"{Fore.CYAN}项目目录:{Style.RESET_ALL} {project_dir}")
        click.echo(f"{Fore.CYAN}报告目录:{Style.RESET_ALL} {report_dir}")

        # 打印下一步操作
        click.echo(f"\n{Fore.YELLOW}下一步操作:{Style.RESET_ALL}")
        for step in project_report['next_steps']:
            click.echo(f"  {step}")

        click.echo(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")

    except Exception as e:
        click.echo(f"\n{Fore.RED}[ERROR] 错误: {e}{Style.RESET_ALL}\n")
        logger.exception("复刻过程中发生错误")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
def detect(directory):
    """
    仅检测技术栈

    DIRECTORY: 网站目录路径
    """
    print_banner()

    click.echo(f"\n{Fore.GREEN}▶ 检测技术栈: {Fore.CYAN}{directory}{Style.RESET_ALL}\n")

    try:
        tech_report = detect_tech_stack(Path(directory))

        detected_count = tech_report['summary']['total_technologies']
        click.echo(f"{Fore.GREEN}[OK] 检测到 {detected_count} 项技术{Style.RESET_ALL}\n")

        # 打印检测到的技术
        if tech_report['detected_technologies']:
            click.echo(f"{Fore.CYAN}检测到的技术栈:{Style.RESET_ALL}")
            for category, techs in tech_report['detected_technologies'].items():
                click.echo(f"  - {category}: {', '.join(techs)}")
            click.echo()

        # 打印推荐
        if tech_report.get('recommendations'):
            click.echo(f"{Fore.CYAN}推荐:{Style.RESET_ALL}")
            for rec in tech_report['recommendations']:
                click.echo(f"  - {rec}")

    except Exception as e:
        click.echo(f"\n{Fore.RED}[ERROR] 错误: {e}{Style.RESET_ALL}\n")
        sys.exit(1)


@cli.command()
@click.argument('url')
@click.option('--output', '-o', required=True, help='输出目录')
def download(url, output):
    """
    仅下载网站资源

    URL: 要下载的网站URL
    """
    print_banner()

    click.echo(f"\n{Fore.GREEN}▶ 下载网站: {Fore.CYAN}{url}{Style.RESET_ALL}\n")

    output_dir = Path(output)

    config = DOWNLOAD_CONFIG.copy()
    config.update(BROWSER_CONFIG)

    try:
        download_report = asyncio.run(download_website(url, output_dir, config))

        # 检查是否取消
        if not download_report:
            click.echo(f"\n{Fore.YELLOW}[取消] 用户取消了下载操作{Style.RESET_ALL}\n")
            return

        click.echo(f"\n{Fore.GREEN}[OK] 下载完成!{Style.RESET_ALL}")
        click.echo(f"  - 页面: {download_report['statistics']['pages_downloaded']}")
        click.echo(f"  - 总文件: {download_report['statistics']['total_files']}")
        click.echo(f"  - 总大小: {download_report['statistics']['total_size']}")
        click.echo(f"  - 输出目录: {output_dir}\n")

    except Exception as e:
        click.echo(f"\n{Fore.RED}[ERROR] 错误: {e}{Style.RESET_ALL}\n")
        sys.exit(1)


@cli.command()
def info():
    """显示工具信息"""
    print_banner()

    info_text = f"""
{Fore.CYAN}工具信息:{Style.RESET_ALL}

名称: 网站一比一复刻工具
版本: 1.0.0
作者: Claude Code
描述: 自动复刻网站,检测技术栈,生成可运行项目

{Fore.CYAN}核心功能:{Style.RESET_ALL}
  - 使用 Playwright 完整渲染和下载网站
  - 智能检测前端框架、UI库、构建工具
  - 自动生成 React/Vue/Next.js 等项目结构
  - AI 辅助分析和优化建议

{Fore.CYAN}支持的框架:{Style.RESET_ALL}
  - React (+ Next.js)
  - Vue.js (+ Nuxt.js)
  - Angular
  - 静态网站

{Fore.CYAN}使用示例:{Style.RESET_ALL}
  # 完整复刻
  python main.py clone https://example.com

  # 启用 AI 分析
  python main.py clone https://example.com --enable-ai

  # 仅下载资源
  python main.py download https://example.com -o ./output

  # 检测技术栈
  python main.py detect ./downloaded-site
"""
    click.echo(info_text)


if __name__ == '__main__':
    cli()
