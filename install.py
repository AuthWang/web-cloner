"""
自动安装脚本 - 跨平台 Python 安装工具
"""

import sys
import subprocess
import platform
from pathlib import Path


def print_header():
    """打印标题"""
    print("=" * 60)
    print("🌐 网站一比一复刻工具 - 自动安装脚本")
    print("=" * 60)
    print()


def check_python_version():
    """检查 Python 版本"""
    print("📋 检查 Python 版本...")
    version = sys.version_info
    print(f"   当前版本: Python {version.major}.{version.minor}.{version.micro}")

    if version < (3, 10):
        print("\n❌ 错误: 需要 Python 3.10 或更高版本")
        print("   请从 https://www.python.org/downloads/ 下载安装")
        sys.exit(1)

    print("   ✓ 版本满足要求\n")


def check_uv_installed():
    """检查 uv 是否已安装"""
    try:
        subprocess.run(
            ["uv", "--version"],
            check=True,
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_uv():
    """安装 uv"""
    print("\n📦 安装 uv (超快速 Python 包管理器)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "uv"],
            check=True
        )
        print("   ✓ uv 安装成功\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ uv 安装失败: {e}")
        print("   请手动安装: pip install uv")
        return False


def install_dependencies():
    """使用 uv 安装项目依赖"""
    print("📚 安装项目依赖 (使用 uv 超快速安装)...")

    try:
        # 使用 --system 参数在系统环境中安装
        subprocess.run(
            ["uv", "pip", "install", "--system", "-e", "."],
            check=True
        )
        print("   ✓ 依赖安装成功\n")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 依赖安装失败: {e}")
        print("\n提示: 你也可以手动安装依赖:")
        print("   uv pip install --system -r requirements.txt")
        return False


def install_playwright():
    """安装 Playwright 浏览器"""
    print("🌐 安装 Playwright 浏览器...")
    print("   这可能需要几分钟时间...")

    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True
        )
        print("   ✓ Playwright 浏览器安装成功\n")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Playwright 安装失败: {e}")
        print("   请尝试手动安装: python -m playwright install chromium")
        return False


def verify_installation():
    """验证安装"""
    print("🔍 验证安装...")

    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        print("   ✓ 安装验证成功\n")
        return True

    except subprocess.CalledProcessError:
        print("   ⚠️ 验证失败,但可能可以正常使用\n")
        return False
    except FileNotFoundError:
        print("   ⚠️ main.py 未找到,请确认在项目目录中运行\n")
        return False


def print_next_steps():
    """打印下一步操作"""
    print("=" * 60)
    print("✅ 安装完成!")
    print("=" * 60)
    print()
    print("📖 快速开始:")
    print("   python main.py clone https://example.com")
    print()
    print("📋 查看帮助:")
    print("   python main.py --help")
    print()
    print("📚 查看文档:")
    print("   README.md      - 完整文档")
    print("   QUICKSTART.md  - 快速入门")
    print("   INSTALL.md     - 安装指南")
    print()
    print("🎉 祝你使用愉快!")
    print()


def main():
    """主函数"""
    print_header()

    # 检查 Python 版本
    check_python_version()

    # 检查并安装 uv
    if not check_uv_installed():
        print("💡 uv 未安装,正在自动安装...")
        if not install_uv():
            print("\n无法继续安装,请先手动安装 uv:")
            print("   pip install uv")
            sys.exit(1)
    else:
        print("✓ uv 已安装\n")

    # 安装依赖
    if not install_dependencies():
        print("\n请检查错误信息并重试")
        sys.exit(1)

    # 安装 Playwright
    if not install_playwright():
        print("\n⚠️ Playwright 安装失败,但其他功能可能可以使用")
        print("   可以稍后手动安装: python -m playwright install chromium")

    # 验证安装
    verify_installation()

    # 打印下一步操作
    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 安装已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)
