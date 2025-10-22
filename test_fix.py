"""
简单测试脚本 - 验证修复
"""

import sys
import time

print("=" * 60)
print("测试修复结果")
print("=" * 60)

# 测试 1: 导入模块
print("\n[测试 1] 导入模块...")
try:
    from src.thread_manager import get_thread_manager
    from src.process_cleaner import get_process_cleaner
    from src.memory_manager import get_memory_manager
    from src.operation_middleware import get_middleware, operation_context
    from config import validate_config
    print("[OK] 所有模块导入成功")
except Exception as e:
    print(f"[FAIL] 模块导入失败: {e}")
    sys.exit(1)

# 测试 2: 配置验证
print("\n[测试 2] 配置验证...")
try:
    validate_config()
    print("[OK] 配置验证通过")
except Exception as e:
    print(f"[FAIL] 配置验证失败: {e}")
    sys.exit(1)

# 测试 3: operation_context 函数
print("\n[测试 3] operation_context 函数...")
try:
    with operation_context("测试操作", progress_total=10) as op_id:
        print(f"[OK] operation_context 工作正常，操作ID: {op_id}")
        time.sleep(0.1)
except Exception as e:
    print(f"[FAIL] operation_context 失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 4: 线程管理器
print("\n[测试 4] 线程管理器...")
try:
    thread_manager = get_thread_manager()
    thread_manager.start()

    # 提交一个简单任务
    def simple_task():
        time.sleep(0.1)
        return "完成"

    future = thread_manager.submit_thread_task("test_1", "测试任务", simple_task)
    result = future.result(timeout=5)
    print(f"[OK] 线程任务执行结果: {result}")

    # 停止管理器
    thread_manager.stop(timeout=5)
    print("[OK] 线程管理器正常停止")
except Exception as e:
    print(f"[FAIL] 线程管理器测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 5: 内存管理器
print("\n[测试 5] 内存管理器...")
try:
    memory_manager = get_memory_manager()
    memory_info = memory_manager.get_current_memory_info()
    print(f"[OK] 内存信息获取成功: {memory_info.get('rss_mb', 0):.1f} MB")
except Exception as e:
    print(f"[FAIL] 内存管理器测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 6: 进程清理器
print("\n[测试 6] 进程清理器...")
try:
    process_cleaner = get_process_cleaner()
    browser_processes = process_cleaner.get_browser_processes()
    print(f"[OK] 进程清理器工作正常，发现 {len(browser_processes)} 个浏览器进程")
except Exception as e:
    print(f"[FAIL] 进程清理器测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("所有测试通过！修复成功。")
print("=" * 60)