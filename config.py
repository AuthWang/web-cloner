"""
配置文件 - 网站复刻工具全局配置
"""

import os
from pathlib import Path

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
    "use_system_chrome": True,  # 使用系统 Chrome 数据（共享登录状态）
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

# 确保目录存在
def ensure_directories():
    """确保所有必要的目录存在"""
    for directory in [OUTPUT_DIR, DOWNLOADS_DIR, PROJECTS_DIR, REPORTS_DIR, TEMPLATES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
