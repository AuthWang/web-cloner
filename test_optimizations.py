"""
优化功能测试脚本
"""

import asyncio
import time
import logging
from colorama import init, Fore, Style

# 初始化
init(autoreset=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_thread_manager():
    """测试线程管理器"""
    print(f"\n{Fore.CYAN}[测试] 线程管理器功能测试{Style.RESET_ALL}")

    try:
        from src.thread_manager import get_thread_manager

        thread_manager = get_thread_manager()
        thread_manager.start()

        # 提交一些测试任务
        def test_task(n):
            time.sleep(0.5)
            return f"Task {n} completed"

        futures = []
        for i in range(3):
            future = thread_manager.submit_thread_task(f"test_{i}", f"测试任务 {i}", test_task, i)
            futures.append(future)

        # 等待所有任务完成
        results = [f.result() for f in futures]
        print(f"{Fore.GREEN}[✓] 线程任务执行结果: {results}{Style.RESET_ALL}")

        thread_manager.print_status()
        thread_manager.stop()

        return True

    except Exception as e:
        print(f"{Fore.RED}[✗] 线程管理器测试失败: {e}{Style.RESET_ALL}")
        return False


def test_memory_manager():
    """测试内存管理器"""
    print(f"\n{Fore.CYAN}[测试] 内存管理器功能测试{Style.RESET_ALL}")

    try:
        from src.memory_manager import get_memory_manager

        memory_manager = get_memory_manager()
        memory_manager.start_monitoring()

        # 获取当前内存信息
        memory_info = memory_manager.get_current_memory_info()
        print(f"{Fore.GREEN}[✓] 当前内存信息: {memory_info}{Style.RESET_ALL}")

        # 触发垃圾回收
        collected = memory_manager.trigger_garbage_collection()
        print(f"{Fore.GREEN}[✓] 垃圾回收完成，回收了 {collected} 个对象{Style.RESET_ALL}")

        memory_manager.print_memory_status()
        memory_manager.stop_monitoring()

        return True

    except Exception as e:
        print(f"{Fore.RED}[✗] 内存管理器测试失败: {e}{Style.RESET_ALL}")
        return False


def test_process_cleaner():
    """测试进程清理器"""
    print(f"\n{Fore.CYAN}[测试] 进程清理器功能测试{Style.RESET_ALL}")

    try:
        from src.process_cleaner import get_process_cleaner

        process_cleaner = get_process_cleaner()

        # 获取浏览器进程
        browser_processes = process_cleaner.get_browser_processes()
        print(f"{Fore.GREEN}[✓] 发现 {len(browser_processes)} 个浏览器进程{Style.RESET_ALL}")

        # 获取 Playwright 进程
        playwright_processes = process_cleaner.get_playwright_processes()
        print(f"{Fore.GREEN}[✓] 发现 {len(playwright_processes)} 个 Playwright 进程{Style.RESET_ALL}")

        process_cleaner.print_process_status()

        return True

    except Exception as e:
        print(f"{Fore.RED}[✗] 进程清理器测试失败: {e}{Style.RESET_ALL}")
        return False


def test_operation_middleware():
    """测试操作中间件"""
    print(f"\n{Fore.CYAN}[测试] 操作中间件功能测试{Style.RESET_ALL}")

    try:
        from src.operation_middleware import get_middleware, operation_context

        middleware = get_middleware()

        # 测试操作上下文
        with operation_context("test_operation", "测试操作", progress_total=10) as op_id:
            for i in range(10):
                time.sleep(0.1)
                middleware.update_progress(op_id, i + 1, f"步骤 {i + 1}")

        middleware.print_summary()

        return True

    except Exception as e:
        print(f"{Fore.RED}[✗] 操作中间件测试失败: {e}{Style.RESET_ALL}")
        return False


def test_config():
    """测试配置验证"""
    print(f"\n{Fore.CYAN}[测试] 配置验证功能测试{Style.RESET_ALL}")

    try:
        from config import validate_config, get_full_config

        # 验证配置
        validate_config()
        print(f"{Fore.GREEN}[✓] 配置验证通过{Style.RESET_ALL}")

        # 获取完整配置
        full_config = get_full_config()
        print(f"{Fore.GREEN}[✓] 获取到 {len(full_config)} 个配置模块{Style.RESET_ALL}")

        return True

    except Exception as e:
        print(f"{Fore.RED}[✗] 配置测试失败: {e}{Style.RESET_ALL}")
        return False


async def test_async_functionality():
    """测试异步功能"""
    print(f"\n{Fore.CYAN}[测试] 异步功能测试{Style.RESET_ALL}")

    try:
        from src.operation_middleware import async_operation

        @async_operation("异步测试", progress_total=5)
        async def test_async_task():
            for i in range(5):
                await asyncio.sleep(0.1)
                print(f"异步步骤 {i + 1} 完成")
            return "异步任务完成"

        result = await test_async_task()
        print(f"{Fore.GREEN}[✓] 异步任务结果: {result}{Style.RESET_ALL}")

        return True

    except Exception as e:
        print(f"{Fore.RED}[✗] 异步功能测试失败: {e}{Style.RESET_ALL}")
        return False


def main():
    """主测试函数"""
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}网站下载工具 - 优化功能测试{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")

    tests = [
        ("配置验证", test_config),
        ("线程管理器", test_thread_manager),
        ("内存管理器", test_memory_manager),
        ("进程清理器", test_process_cleaner),
        ("操作中间件", test_operation_middleware),
    ]

    results = []

    # 运行同步测试
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # 运行异步测试
    try:
        async_result = asyncio.run(test_async_functionality())
        results.append(("异步功能", async_result))
    except Exception as e:
        print(f"{Fore.RED}[✗] 异步功能测试失败: {e}{Style.RESET_ALL}")
        results.append(("异步功能", False))

    # 输出测试结果
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}测试结果摘要{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

    passed = 0
    total = len(results)

    for name, result in results:
        status = f"{Fore.GREEN}[✓] 通过{Style.RESET_ALL}" if result else f"{Fore.RED}[✗] 失败{Style.RESET_ALL}"
        print(f"{name:15} {status}")
        if result:
            passed += 1

    print(f"\n{Fore.CYAN}总计: {passed}/{total} 个测试通过{Style.RESET_ALL}")

    if passed == total:
        print(f"{Fore.GREEN}🎉 所有测试通过！优化功能正常工作。{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠️  有 {total - passed} 个测试失败，请检查相关模块。{Style.RESET_ALL}")

    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")


if __name__ == '__main__':
    main()