"""
配置文件 - 网站复刻工具全局配置
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 输出目录配置
OUTPUT_DIR = PROJECT_ROOT / "output"
DOWNLOADS_DIR = OUTPUT_DIR / "downloads"
PROJECTS_DIR = OUTPUT_DIR / "projects"
REPORTS_DIR = OUTPUT_DIR / "reports"

# 浏览器配置
BROWSER_CONFIG = {
    "headless": False,  # 默认显示浏览器窗口（方便查看登录状态）
    "timeout": 30000,  # 30秒超时
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "use_system_chrome": False,  # 默认不使用系统 Chrome 数据（独立浏览器模式）
    "chrome_data_dir": None,  # None 表示自动检测系统 Chrome 路径
    "chrome_mode": "playwright",  # Chrome 数据模式: 'system'(需关闭Chrome) / 'playwright'(推荐，独立Profile) / 'temp'(临时)
}

# 下载配置
DOWNLOAD_CONFIG = {
    "max_depth": 3,  # 最大爬取深度
    "max_pages": 50,  # 最大页面数
    "download_images": True,
    "download_css": True,
    "download_js": False,  # 不下载JS，生成纯静态页面
    "download_fonts": True,
    "follow_external_links": False,  # 不跟随外部链接
    "wait_for_confirmation": True,  # 下载前等待用户确认页面是否正确
    "keep_ui_interactions": False,  # 移除所有JavaScript
    # 动态页面处理配置
    "dynamic_page_handling": {
        "enabled": True,  # 启用动态页面处理
        "page_stability_timeout": 5000,  # 页面稳定检查超时（毫秒）
        "content_retry_attempts": 3,  # 页面内容获取重试次数
        "content_retry_delay": 1000,  # 重试间隔（毫秒）
        "network_idle_timeout": 3000,  # 网络空闲等待超时（毫秒）
        "stability_check_delay": 1000,  # 稳定性检查延迟（毫秒）
    }
}

# 技术栈检测配置
TECH_DETECTION = {
    "frameworks": {
        "react": ["react", "react-dom", "_reactRootContainer"],
        "vue": ["Vue", "__VUE__", "vue"],
        "angular": ["ng-version", "angular", "ngVersion"],
        "jquery": ["jQuery", "$"],
        "bootstrap": ["bootstrap"],
        "tailwind": ["tailwind"],
    },
    "build_tools": {
        "webpack": ["webpackJsonp", "__webpack_require__"],
        "vite": ["__vite__"],
        "parcel": ["parcelRequire"],
    }
}

# AI 配置 - 使用本地 Claude
AI_CONFIG = {
    "use_local_claude": True,  # 使用本地 Claude Code 进行分析
    "provider": "local_claude",
}

# 项目模板配置
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

# 线程管理配置
THREAD_CONFIG = {
    "max_workers": 4,  # 最大工作线程数
    "task_timeout": 300,  # 任务超时时间（秒）
    "enable_monitoring": True,  # 启用线程监控
    "shutdown_timeout": 30,  # 关闭超时时间（秒）
}

# 进程清理配置
PROCESS_CLEANUP_CONFIG = {
    "enable_auto_cleanup": False,  # 禁用自动清理（避免误杀用户浏览器）
    "cleanup_on_exit": False,  # 禁用退出时清理
    "force_cleanup_timeout": 10,  # 强制清理超时时间（秒）
    "cleanup_temp_files": False,  # 禁用清理临时文件（保留浏览器数据）
    "cleanup_browser_processes": False,  # ❌ 禁用浏览器进程清理（危险操作）
    "cleanup_playwright_processes": True,  # ✅ 只清理 Playwright 进程
    "temp_cleanup_dirs": [  # 临时清理目录
        ".temp",
        "__pycache__"  # 移除 browser-data，保留用户登录状态
    ]
}

# 内存管理配置
MEMORY_CONFIG = {
    "enable_monitoring": True,  # 启用内存监控
    "check_interval": 30.0,  # 检查间隔（秒）
    "warning_percent": 80.0,  # 内存警告阈值（百分比）
    "critical_percent": 90.0,  # 内存危险阈值（百分比）
    "gc_threshold": 70.0,  # 触发垃圾回收的内存百分比
    "max_objects_growth": 100000,  # 对象增长阈值
    "auto_gc": True,  # 自动垃圾回收
    "cache_cleanup": True,  # 自动缓存清理
    "max_snapshots": 100,  # 最大内存快照数量
}

# 中间件配置
MIDDLEWARE_CONFIG = {
    "enable_operation_tracking": True,  # 启用操作追踪
    "show_progress": True,  # 显示进度条
    "show_details": True,  # 显示详细信息
    "color_output": True,  # 彩色输出
    "clear_old_operations": True,  # 清理旧操作记录
    "operation_retention_time": 3600,  # 操作记录保留时间（秒）
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    "enable_memory_optimization": True,  # 启用内存优化
    "enable_process_optimization": True,  # 启用进程优化
    "enable_thread_optimization": True,  # 启用线程优化
    "parallel_resource_downloads": 5,  # 并行资源下载数
    "chunk_size": 8192,  # 文件下载块大小
    "network_timeout": 30,  # 网络超时时间（秒）
    "retry_attempts": 3,  # 重试次数
    "retry_delay": 1.0,  # 重试延迟（秒）
}

# 监控配置
MONITORING_CONFIG = {
    "enable_system_monitoring": True,  # 启用系统监控
    "log_system_stats": True,  # 记录系统统计
    "stats_log_interval": 60,  # 统计日志间隔（秒）
    "enable_performance_tracking": True,  # 启用性能追踪
    "track_resource_usage": True,  # 追踪资源使用
}

# 确保目录存在
def ensure_directories():
    """确保所有必要的目录存在"""
    directories = [
        OUTPUT_DIR, DOWNLOADS_DIR, PROJECTS_DIR, REPORTS_DIR, TEMPLATES_DIR
    ]

    # 添加临时目录
    if PROCESS_CLEANUP_CONFIG.get("cleanup_temp_files", True):
        for temp_dir in PROCESS_CLEANUP_CONFIG.get("temp_cleanup_dirs", []):
            directories.append(PROJECT_ROOT / temp_dir)

    for directory in directories:
        if directory:
            directory.mkdir(parents=True, exist_ok=True)


# 验证配置
def validate_config():
    """验证配置参数的有效性"""
    errors = []

    # 验证线程配置
    if THREAD_CONFIG["max_workers"] <= 0:
        errors.append("THREAD_CONFIG.max_workers 必须大于 0")

    if THREAD_CONFIG["task_timeout"] <= 0:
        errors.append("THREAD_CONFIG.task_timeout 必须大于 0")

    # 验证内存配置
    if not (0 < MEMORY_CONFIG["warning_percent"] < 100):
        errors.append("MEMORY_CONFIG.warning_percent 必须在 0-100 之间")

    if not (0 < MEMORY_CONFIG["critical_percent"] < 100):
        errors.append("MEMORY_CONFIG.critical_percent 必须在 0-100 之间")

    if MEMORY_CONFIG["critical_percent"] <= MEMORY_CONFIG["warning_percent"]:
        errors.append("MEMORY_CONFIG.critical_percent 必须大于 warning_percent")

    # 验证性能配置
    if PERFORMANCE_CONFIG["parallel_resource_downloads"] <= 0:
        errors.append("PERFORMANCE_CONFIG.parallel_resource_downloads 必须大于 0")

    if PERFORMANCE_CONFIG["chunk_size"] <= 0:
        errors.append("PERFORMANCE_CONFIG.chunk_size 必须大于 0")

    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(f"  - {error}" for error in errors))

    logger.info("配置验证通过")


# 获取完整配置
def get_full_config():
    """获取完整的配置字典"""
    return {
        "browser": BROWSER_CONFIG,
        "download": DOWNLOAD_CONFIG,
        "thread": THREAD_CONFIG,
        "process_cleanup": PROCESS_CLEANUP_CONFIG,
        "memory": MEMORY_CONFIG,
        "middleware": MIDDLEWARE_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "monitoring": MONITORING_CONFIG,
        "tech_detection": TECH_DETECTION,
        "ai": AI_CONFIG,
        "log": LOG_CONFIG
    }
