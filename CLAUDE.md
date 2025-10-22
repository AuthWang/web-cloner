# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 Playwright 的 Python 网站下载工具，用于完整下载静态网站并进行本地化处理。该工具使用浏览器自动化技术渲染动态内容，下载所有静态资源，并可选地检测技术栈和生成项目结构。

**重要定位**: 这是静态网站下载和备份工具，不是框架转换工具。

## 核心架构

### 主要模块职责

- **`src/downloader.py`**: 核心下载引擎
  - `WebsiteDownloader` 类负责递归下载网站页面和所有资源
  - 使用 Playwright 的 `async_playwright` 进行浏览器自动化
  - 支持三种浏览器数据模式: `system`(系统完整数据), `playwright`(推荐，独立Profile), `temp`(临时)
  - 关键方法:
    - `download()`: 主入口，管理浏览器上下文和下载流程
    - `_download_recursive_with_context()`: 递归下载页面及资源（复用浏览器上下文）
    - `_download_page_resources()`: 提取并下载单个页面的所有资源（CSS、JS、图片、字体）
    - `_process_css_resources()`: 从CSS文件中提取并下载url()引用的资源
    - `_copy_chrome_data_files()`: 安全复制Chrome的登录数据（Cookies、Local Storage等）
  - 资源提取策略:
    - HTML标签属性: `<img src>`, `<link href>`, `<script src>`
    - 内联样式: `style="background-image: url(...)"`
    - `<style>` 标签内的 CSS url()
    - CSS文件内的 @font-face 和 background-image

- **`src/detector.py`**: 技术栈检测引擎
  - `TechStackDetector` 类使用正则匹配检测前端框架和工具
  - 检测类别: frameworks, ui_libraries, build_tools, css_preprocessors
  - 生成检测报告和推荐建议

- **`src/reconstructor.py`**: 项目重构模块
  - 根据检测到的技术栈生成相应的项目结构
  - 可强制生成纯静态项目（`force_static=True`）

- **`src/ai_analyzer.py`**: AI 分析模块（实验性）
  - 当前使用规则引擎，非真实 AI 模型
  - 需要自行配置 API 才能使用真实 AI 功能

- **`main.py`**: CLI 入口，使用 Click 框架定义命令行接口

- **`config.py`**: 全局配置，包括浏览器、下载、AI 等配置

### 关键设计模式

1. **浏览器数据管理**: 支持共享系统浏览器的登录状态，避免重复登录
   - `playwright` 模式（推荐）：创建独立的 Playwright Profile 并自动同步系统 Chrome 数据
   - `system` 模式：直接使用系统 Chrome 数据（需关闭所有 Chrome 窗口）
   - `temp` 模式：每次使用临时目录

2. **用户确认流程**:
   - 默认启用 `wait_for_confirmation`，先打开页面让用户确认（检查登录状态、内容完整性）
   - 用户确认后直接在当前页面开始下载，避免重新打开导致状态丢失
   - 使用 `existing_page` 参数复用已确认的页面

3. **SQLite 数据库复制**: 使用三种方法安全复制被锁定的 Chrome 数据库
   - `VACUUM INTO` (SQLite 3.27.0+)
   - SQLite backup API
   - 直接文件复制（回退方案）

4. **错误分级处理**:
   - 404错误标记为 `severity: 'info'`（常见失效链接）
   - 网络错误和HTTP错误标记为 `severity: 'warning'`
   - 只有关键错误才显示警告信息

## 常用命令

### 开发环境

```bash
# 安装依赖（推荐使用 uv，速度快10-100倍）
python install.py  # 自动安装脚本

# 或使用传统 pip
pip install -r requirements.txt
playwright install chromium
```

### 运行工具

```bash
# 基础下载（独立浏览器，移除所有JS）
python main.py clone https://example.com

# 使用浏览器登录状态（推荐 playwright 模式）
python main.py clone https://example.com --use-browser-data

# 保留 UI 交互脚本（移除追踪代码）
python main.py clone https://example.com --keep-ui-interactions

# 强制纯静态模式（仅HTML+CSS）
python main.py clone https://example.com --static-only

# 自定义选项
python main.py clone https://example.com --max-depth 2 --max-pages 20 --no-images

# 跳过用户确认（自动开始下载）
python main.py clone https://example.com --no-confirm

# 后台模式（不显示浏览器窗口）
python main.py clone https://example.com --headless

# 仅下载资源
python main.py download https://example.com -o ./output

# 检测技术栈
python main.py detect ./downloaded-site

# 查看工具信息
python main.py info
```

### 测试

```bash
# 运行示例
python examples/example.py

# 测试 Chrome 数据同步
python test_chrome_sync.py
```

## 配置说明

### 浏览器配置（config.py: BROWSER_CONFIG）

- `headless`: 默认 `False`（显示浏览器窗口，方便查看登录状态）
- `use_system_chrome`: 默认 `False`（独立浏览器模式）
- `chrome_mode`: `'playwright'`（推荐）/ `'system'` / `'temp'`

### 下载配置（config.py: DOWNLOAD_CONFIG）

- `max_depth`: 最大爬取深度（默认 3）
- `max_pages`: 最大页面数（默认 50）
- `download_js`: 默认 `False`（生成纯静态页面）
- `wait_for_confirmation`: 默认 `True`（下载前等待用户确认）
- `keep_ui_interactions`: 默认 `False`（移除所有JavaScript）

## 输出目录结构

```
output/
├── downloads/          # 下载的原始网站
│   └── [domain_timestamp]/
│       ├── index.html
│       ├── css/
│       ├── images/
│       ├── fonts/
│       └── download_report.json
├── projects/           # 生成的项目结构
│   └── [domain_timestamp]/
└── reports/            # 分析报告
    └── [domain_timestamp]/
        ├── download_report.json
        ├── tech_report.json
        ├── project_report.json
        └── ai_analysis.json (可选)
```

## 重要实现细节

### 1. 资源提取的完整性

工具会从多个来源提取资源URL:
- HTML 标签的 `src`, `href` 属性
- 内联样式的 `style="background-image: url(...)"`
- `<style>` 标签内的所有 `url()` 引用
- 下载的 CSS 文件内的 `url()` 引用（包括 @font-face）

### 2. 浏览器数据同步机制

使用 `playwright` 模式时:
1. 检查 `~/.../Chrome/Playwright/` 目录
2. 从系统 `Default` Profile 复制关键文件: `Cookies`, `Login Data`, `Web Data`, `Local State`
3. 使用缓存标记（`.last_sync`）避免频繁复制（1小时内跳过）
4. 不影响正在运行的 Chrome 窗口

### 3. 页面确认和复用

用户确认流程（`wait_for_confirmation=True`）:
1. 打开目标页面并等待用户检查
2. 用户输入 `y` 确认后，保存 `confirmed_page` 引用
3. 将 `confirmed_page` 传递给 `_download_recursive_with_context(..., existing_page=confirmed_page)`
4. 直接在已确认的页面开始下载，避免重新打开导致状态变化

### 4. 错误处理策略

- 404错误: `logger.debug()` 输出，标记为 `severity: 'info'`，不影响使用
- 网络错误/HTTP错误: `logger.warning()` 输出，标记为 `severity: 'warning'`
- BeautifulSoup 类型错误: `logger.debug()` 输出（常见的无害警告）
- 只在有关键错误时才显示警告信息给用户

## 扩展开发指南

### 添加新的技术检测规则

编辑 `src/detector.py` 的 `_load_detection_rules()` 方法:

```python
'frameworks': {
    'YourFramework': {
        'patterns': [r'your-framework\.js'],
        'dom_signatures': ['data-your-attr'],
        'package_names': ['your-framework']
    }
}
```

### 实现真实 AI 分析

编辑 `src/ai_analyzer.py`，配置真实的 AI API 调用:
- 当前使用规则引擎（`config.py: AI_CONFIG['use_local_claude'] = True`）
- 需要配置 Anthropic 或 OpenAI API Key
- 实现 `_call_ai_api()` 方法

### 自定义资源过滤

在 `src/downloader.py` 的 `_download_resource()` 方法中添加过滤逻辑，或扩展 `DOWNLOAD_CONFIG` 添加新的过滤选项。

## 常见问题处理

### Playwright 浏览器未安装
```bash
playwright install chromium
```

### Chrome 占用端口
使用 `--chrome-mode playwright`（默认），无需关闭 Chrome。

### 需要登录的页面
```bash
# 方法1: 使用浏览器数据
python main.py clone <URL> --use-browser-data

# 方法2: 利用用户确认功能，在打开的浏览器中手动登录后确认
python main.py clone <URL> --use-browser-data
# 等浏览器打开后，手动登录，然后输入 y 确认
```

### 本地打开 HTML 样式丢失
使用本地服务器而非直接双击打开:
```bash
python -m http.server 8000
# 访问 http://localhost:8000
```

## 技术栈

- **Playwright**: 浏览器自动化和页面渲染
- **Beautiful Soup**: HTML 解析和操作
- **Click**: CLI 框架
- **Requests**: HTTP 资源下载
- **Colorama**: 终端彩色输出
- **tqdm**: 进度条显示
