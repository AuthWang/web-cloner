"""
快速状态检查脚本
"""

import sys

print("=" * 60)
print("Web Cloner - Status Check")
print("=" * 60)

# 检查依赖
print("\n[1] Checking dependencies...")
try:
    import playwright
    import psutil
    import colorama
    import requests
    from bs4 import BeautifulSoup
    print("[OK] All dependencies installed")
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# 检查模块
print("\n[2] Checking modules...")
try:
    from src.thread_manager import get_thread_manager
    from src.process_cleaner import get_process_cleaner
    from src.memory_manager import get_memory_manager
    from src.operation_middleware import get_middleware
    from src.downloader import WebsiteDownloader
    print("[OK] All modules loaded")
except Exception as e:
    print(f"[ERROR] Module load failed: {e}")
    sys.exit(1)

# 检查配置
print("\n[3] Checking configuration...")
try:
    from config import validate_config, get_full_config
    validate_config()
    config = get_full_config()
    print(f"[OK] Configuration valid ({len(config)} modules)")
except Exception as e:
    print(f"[ERROR] Configuration invalid: {e}")
    sys.exit(1)

# 检查管理器
print("\n[4] Checking managers...")
try:
    # 线程管理器
    tm = get_thread_manager()
    print(f"  - ThreadManager: OK (max_workers={tm.max_workers})")

    # 内存管理器
    mm = get_memory_manager()
    mem_info = mm.get_current_memory_info()
    print(f"  - MemoryManager: OK (memory={mem_info.get('rss_mb', 0):.1f}MB)")

    # 进程清理器
    pc = get_process_cleaner()
    browsers = pc.get_browser_processes()
    print(f"  - ProcessCleaner: OK (browsers={len(browsers)})")

    # 中间件
    mw = get_middleware()
    print(f"  - Middleware: OK")

except Exception as e:
    print(f"[ERROR] Manager check failed: {e}")
    sys.exit(1)

# 系统信息
print("\n[5] System information...")
try:
    import platform
    import psutil

    print(f"  - OS: {platform.system()} {platform.release()}")
    print(f"  - Python: {sys.version.split()[0]}")
    print(f"  - CPU: {psutil.cpu_count()} cores")
    print(f"  - Memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")

except Exception as e:
    print(f"[WARNING] System info unavailable: {e}")

print("\n" + "=" * 60)
print("Status: ALL SYSTEMS OPERATIONAL")
print("=" * 60)
print("\nYou can now run:")
print("  python main.py clone https://example.com")
print("  python status_cli.py all")
print("=" * 60)