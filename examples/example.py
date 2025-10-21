"""
使用示例 - 演示如何在代码中使用各个模块
"""

import asyncio
from pathlib import Path

# 导入模块
from src.downloader import download_website
from src.detector import detect_tech_stack
from src.reconstructor import reconstruct_project
from src.ai_analyzer import analyze_with_ai
from config import BROWSER_CONFIG, DOWNLOAD_CONFIG, AI_CONFIG


async def example_1_basic_download():
    """示例 1: 基本下载"""
    print("=== 示例 1: 基本下载 ===\n")

    url = "https://example.com"
    output_dir = Path("./output/example1")

    config = {**BROWSER_CONFIG, **DOWNLOAD_CONFIG}

    report = await download_website(url, output_dir, config)

    print(f"下载完成!")
    print(f"  页面数: {report['statistics']['pages_downloaded']}")
    print(f"  总文件: {report['statistics']['total_files']}")
    print(f"  总大小: {report['statistics']['total_size']}")


def example_2_detect_tech_stack():
    """示例 2: 检测技术栈"""
    print("\n=== 示例 2: 检测技术栈 ===\n")

    directory = Path("./output/example1")

    if not directory.exists():
        print("请先运行示例 1 下载网站")
        return

    report = detect_tech_stack(directory)

    print(f"检测到 {report['summary']['total_technologies']} 项技术:")
    for category, techs in report['detected_technologies'].items():
        print(f"  {category}: {', '.join(techs)}")


def example_3_full_workflow():
    """示例 3: 完整工作流"""
    print("\n=== 示例 3: 完整工作流 ===\n")

    async def run():
        url = "https://example.com"
        download_dir = Path("./output/example3/downloads")
        project_dir = Path("./output/example3/project")

        # 1. 下载网站
        print("步骤 1: 下载网站...")
        config = {**BROWSER_CONFIG, **DOWNLOAD_CONFIG}
        download_report = await download_website(url, download_dir, config)
        print(f"  ✓ 下载完成: {download_report['statistics']['total_files']} 个文件\n")

        # 2. 检测技术栈
        print("步骤 2: 检测技术栈...")
        tech_report = detect_tech_stack(download_dir)
        print(f"  ✓ 检测到 {tech_report['summary']['total_technologies']} 项技术\n")

        # 3. 生成项目
        print("步骤 3: 生成项目...")
        project_report = reconstruct_project(download_dir, project_dir, tech_report)
        print(f"  ✓ 项目类型: {project_report['project_type']}\n")

        # 4. AI 分析 (可选)
        print("步骤 4: AI 分析...")
        ai_report = analyze_with_ai(download_report, tech_report, project_report, AI_CONFIG)

        if ai_report['ai_enabled']:
            print(f"  ✓ AI 分析完成")
            suggestions = ai_report['analysis'].get('suggestions', [])
            print(f"  建议数量: {len(suggestions)}")
        else:
            print(f"  ✓ 规则引擎分析完成")

        print("\n完整工作流程完成!")
        print(f"项目目录: {project_dir}")

    asyncio.run(run())


def example_4_custom_config():
    """示例 4: 自定义配置"""
    print("\n=== 示例 4: 自定义配置 ===\n")

    async def run():
        url = "https://example.com"
        output_dir = Path("./output/example4")

        # 自定义配置
        custom_config = {
            'headless': False,  # 显示浏览器
            'max_depth': 1,  # 只爬取一层
            'max_pages': 5,  # 最多 5 个页面
            'download_images': False,  # 不下载图片
            'viewport': {'width': 1366, 'height': 768},
            'timeout': 60000  # 60秒超时
        }

        report = await download_website(url, output_dir, custom_config)

        print(f"自定义下载完成!")
        print(f"  页面数: {report['statistics']['pages_downloaded']}")

    asyncio.run(run())


if __name__ == '__main__':
    import sys

    examples = {
        '1': ('基本下载', example_1_basic_download),
        '2': ('检测技术栈', example_2_detect_tech_stack),
        '3': ('完整工作流', example_3_full_workflow),
        '4': ('自定义配置', example_4_custom_config)
    }

    print("可用示例:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")

    choice = input("\n请选择示例 (1-4): ").strip()

    if choice in examples:
        name, func = examples[choice]
        if asyncio.iscoroutinefunction(func):
            asyncio.run(func())
        else:
            func()
    else:
        print("无效选择!")
