"""
状态监控命令行工具
"""

import click
from colorama import init, Fore, Style
from src.thread_manager import get_thread_manager
from src.process_cleaner import get_process_cleaner
from src.memory_manager import get_memory_manager
from src.operation_middleware import get_middleware

# 初始化
init(autoreset=True)


@click.group()
def status():
    """状态监控和系统管理工具"""
    pass


@status.command()
def threads():
    """显示线程管理状态"""
    thread_manager = get_thread_manager()
    thread_manager.print_status()


@status.command()
def processes():
    """显示进程状态"""
    process_cleaner = get_process_cleaner()
    process_cleaner.print_process_status()


@status.command()
def memory():
    """显示内存使用状态"""
    memory_manager = get_memory_manager()
    memory_manager.print_memory_status()


@status.command()
def operations():
    """显示操作摘要"""
    middleware = get_middleware()
    middleware.print_summary()
    middleware.print_running_operations()


@status.command()
def all():
    """显示所有状态信息"""
    click.echo(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}系统状态监控{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")

    # 线程状态
    click.echo(f"\n{Fore.YELLOW}1. 线程管理状态{Style.RESET_ALL}")
    threads()

    # 进程状态
    click.echo(f"\n{Fore.YELLOW}2. 进程状态{Style.RESET_ALL}")
    processes()

    # 内存状态
    click.echo(f"\n{Fore.YELLOW}3. 内存状态{Style.RESET_ALL}")
    memory()

    # 操作状态
    click.echo(f"\n{Fore.YELLOW}4. 操作状态{Style.RESET_ALL}")
    operations()


@status.command()
@click.option('--force', is_flag=True, help='强制清理')
def cleanup():
    """执行系统清理"""
    click.echo(f"\n{Fore.YELLOW}[清理] 开始执行系统清理...{Style.RESET_ALL}")

    # 进程清理
    process_cleaner = get_process_cleaner()
    results = process_cleaner.cleanup_all(force=force)

    click.echo(f"{Fore.GREEN}[清理完成] 浏览器进程: {results['browser_processes']['total']} 个, "
              f"终止 {results['browser_processes']['terminated']} 个, 强制 {results['browser_processes']['forced']} 个{Style.RESET_ALL}")
    click.echo(f"{Fore.GREEN}[清理完成] Playwright 进程: {results['playwright_processes']['total']} 个, "
              f"终止 {results['playwright_processes']['terminated']} 个, 强制 {results['playwright_processes']['forced']} 个{Style.RESET_ALL}")
    click.echo(f"{Fore.GREEN}[清理完成] 临时文件: {results['temp_files']['files']} 个文件, "
              f"{results['temp_files']['dirs']} 个目录{Style.RESET_ALL}")


@status.command()
def gc():
    """执行垃圾回收"""
    memory_manager = get_memory_manager()
    collected = memory_manager.force_garbage_collection()
    click.echo(f"\n{Fore.GREEN}[垃圾回收] 完成，回收了 {collected} 个对象{Style.RESET_ALL}")


if __name__ == '__main__':
    status()