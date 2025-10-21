# 🌐 静态网站下载工具

一款基于 Playwright 的 Python 工具，用于**完整下载静态网站**并进行本地化处理，适合学习、备份和静态展示。

> ⚠️ **定位说明**: 这是一个**静态网站下载工具**，主要用于学习和备份。它不是框架转换工具，无法将网站转换为 React/Vue 等现代框架项目。

## ✨ 核心功能

### 1. 完整网站渲染和下载
- 🎯 使用 Playwright 浏览器自动化，完整渲染动态网站（包括JavaScript生成的内容）
- 📦 下载所有静态资源：HTML、CSS、JavaScript、图片、字体
- 🔍 **智能资源提取**：
  - ✅ 自动从 CSS 文件中提取 `url()` 引用的图片和字体
  - ✅ 自动从内联样式 `style="background-image: url(...)"` 提取资源
  - ✅ 自动从 `<style>` 标签中提取 @font-face 等引用
- 📊 生成详细的下载统计报告

### 2. CDN 资源本地化
- 🔗 自动识别并下载 CDN 托管的资源（图片、CSS、JS、字体）
- 🔄 智能重写资源路径为本地相对路径
- 🌐 处理绝对路径和相对路径的各种情况
- 📁 统一整理到规范的目录结构（css/、images/、fonts/）

### 3. JavaScript 智能过滤
- 🧹 **默认模式**：移除所有 `<script>` 标签和内联事件，生成纯静态页面
- 🎨 **UI交互保留模式**（`--keep-ui-interactions`）：
  - ✅ 保留 UI 库脚本（jQuery、Bootstrap、Swiper、AOS 等）
  - ✅ 保留基础 UI 事件处理器（onclick、onchange 等）
  - ❌ 移除追踪脚本（Google Analytics、百度统计、Sentry 等）
  - ❌ 移除业务逻辑和 API 调用

### 4. 技术栈检测（基础）
- 🔍 通过正则匹配检测前端框架（React、Vue、Angular、Next.js 等）
- 📚 识别 UI 库（Bootstrap、Tailwind CSS、Material-UI 等）
- 🛠️ 识别构建工具（Webpack、Vite、Parcel）
- 📊 生成技术栈检测报告

### 5. AI 辅助分析（实验性）
- 🤖 **状态**：实验性功能，未充分测试，需自行完善
- 💡 基于规则引擎的代码分析和优化建议
- 📋 生成项目改进建议报告
- ⚠️ **注意**：当前版本使用规则引擎，非真实AI模型调用。如需完整AI功能，需自行配置 API 并完善代码。

## 🚀 快速开始

> 💡 **推荐使用 uv** - 比 pip 快 10-100 倍的包管理器！详见 [INSTALL.md](INSTALL.md)

### 安装依赖

#### 方法 1: 一键自动安装（推荐）

```bash
# 进入项目目录
cd web-cloner

# 运行自动安装脚本
python install.py
```

这个脚本会：
- ✅ 检查 Python 版本
- ✅ 询问是否使用 uv（超快速）
- ✅ 自动安装所有依赖
- ✅ 安装 Playwright 浏览器
- ✅ 验证安装

#### 方法 2: 使用传统 pip

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 基本使用

#### 1. 下载静态网站（基础模式）

```bash
python main.py clone https://example.com
```

这将：
- 使用独立浏览器打开页面（不共享登录状态）
- 等待用户确认页面正确
- 下载网站所有资源
- 移除所有 JavaScript
- 生成纯静态 HTML+CSS 网站
- 生成详细报告

#### 2. 保留 UI 交互

```bash
# 保留 UI 库，移除追踪代码
python main.py clone https://example.com --keep-ui-interactions
```

#### 3. 强制纯静态模式

```bash
# 强制生成纯静态项目（仅HTML+CSS）
python main.py clone https://example.com --static-only
```

#### 4. 使用浏览器登录状态

```bash
# 共享浏览器的登录状态和 Cookies（需要已登录的网站）
python main.py clone https://example.com --use-browser-data
```

这将：
- 使用系统浏览器的数据（Playwright 专用 Profile）
- 无需重新登录即可下载需要认证的页面
- 不会影响正在运行的 Chrome 窗口

#### 5. 自定义选项

```bash
# 限制爬取深度和页面数
python main.py clone https://example.com --max-depth 2 --max-pages 20

# 不下载图片
python main.py clone https://example.com --no-images

# 跳过用户确认（自动开始下载）
python main.py clone https://example.com --no-confirm

# 后台模式（不显示浏览器窗口）
python main.py clone https://example.com --headless
```

### 其他命令

#### 仅下载网站资源

```bash
python main.py download https://example.com -o ./my-download
```

#### 检测已下载网站的技术栈

```bash
python main.py detect ./my-download
```

#### 查看工具信息

```bash
python main.py info
```

## 📂 项目结构

```
web-cloner/
├── src/                      # 源代码
│   ├── __init__.py
│   ├── downloader.py         # 资源下载模块（Playwright）
│   ├── detector.py           # 技术栈检测（正则匹配）
│   ├── reconstructor.py      # 项目生成模块
│   ├── ai_analyzer.py        # AI 分析（实验性）
│   └── utils.py              # 工具函数
├── templates/                # 项目模板
├── output/                   # 输出目录
│   ├── downloads/            # 下载的网站
│   ├── projects/             # 生成的项目
│   └── reports/              # 分析报告
├── config.py                 # 配置文件
├── main.py                   # 主程序入口
├── requirements.txt          # Python 依赖
├── .gitignore
└── README.md
```

## 📋 命令行选项

### `clone` 命令

完整下载并处理网站

```bash
python main.py clone [OPTIONS] URL

选项:
  -o, --output TEXT           输出目录名称
  -d, --max-depth INT         最大爬取深度 [默认: 3]
  -p, --max-pages INT         最大页面数 [默认: 50]
  --no-images                 不下载图片
  --no-css                    不下载 CSS
  --no-js                     不下载 JavaScript
  --static-only               强制生成纯静态项目（仅HTML+CSS，移除所有JS）
  --enable-ai                 启用 AI 辅助分析（实验性）
  --headless/--no-headless    后台模式 [默认: 显示浏览器]
  --confirm/--no-confirm      下载前等待用户确认 [默认: 开启]
  --use-browser-data          使用系统浏览器数据（登录状态、Cookies等）
  --chrome-mode               Chrome 数据模式: system/playwright/temp [默认: playwright]
  --chrome-data-dir PATH      指定 Chrome 用户数据目录
  --help                      显示帮助信息
```

#### 浏览器模式说明

**默认（独立浏览器）**：
```bash
python main.py clone <URL>
```
- 独立浏览器实例，不共享任何数据
- 需要重新登录
- 类似隐身模式

**使用浏览器数据**：
```bash
python main.py clone <URL> --use-browser-data
```
- 共享系统浏览器的登录状态
- 无需重新登录
- 使用 Playwright 专用 Profile（不影响正在运行的 Chrome）

**Chrome 数据模式**：
- `playwright`（默认，推荐）：独立 Profile，无需关闭 Chrome
- `system`：完整系统数据，需关闭所有 Chrome 窗口
- `temp`：临时目录，每次都需要重新登录

#### 用户确认流程

**默认行为**（开启确认）：
1. 浏览器打开目标页面
2. 用户检查页面是否正确（是否已登录、内容完整）
3. 输入 `y` 确认后开始下载
4. **直接在已确认的页面开始下载**（不会重新打开页面）

**跳过确认**：
```bash
python main.py clone <URL> --no-confirm
```
- 自动开始下载，不等待确认

### `download` 命令

仅下载网站资源

```bash
python main.py download [OPTIONS] URL

选项:
  -o, --output TEXT  输出目录 [必需]
  --help            显示帮助信息
```

### `detect` 命令

检测技术栈

```bash
python main.py detect [OPTIONS] DIRECTORY

参数:
  DIRECTORY  网站目录路径
```

## ⚙️ 配置

编辑 `config.py` 自定义配置：

```python
# 浏览器配置
BROWSER_CONFIG = {
    "headless": False,  # 默认显示浏览器窗口
    "timeout": 30000,
    "viewport": {"width": 1920, "height": 1080},
    "use_system_chrome": False,  # 默认不使用系统浏览器数据（独立模式）
    "chrome_mode": "playwright",  # playwright/system/temp
}

# 下载配置
DOWNLOAD_CONFIG = {
    "max_depth": 3,
    "max_pages": 50,
    "download_images": True,
    "wait_for_confirmation": True,  # 下载前等待用户确认
    "keep_ui_interactions": False,  # 是否保留UI交互脚本
    # ...
}

# AI 配置（实验性）
AI_CONFIG = {
    "provider": "anthropic",  # 'anthropic' 或 'openai'
    "model": "claude-3-5-sonnet-20241022",
    # 注意: 需要自行配置 API Key
}
```

## 🎯 使用场景

### 1. 学习网站布局和样式

```bash
python main.py clone https://example-portfolio.com --static-only
```

下载静态副本，学习 HTML/CSS 实现方式。

### 2. 网站备份

```bash
python main.py download https://my-old-site.com -o ./backup
```

完整备份网站内容和资源。

### 3. 创建静态展示页面

```bash
python main.py clone https://company-site.com
```

生成可本地运行的静态展示页面。

### 4. 技术栈分析

```bash
python main.py detect ./existing-website
```

分析网站使用的技术栈和工具。

## 📊 输出说明

### 下载报告（`download_report.json`）

```json
{
  "statistics": {
    "pages_downloaded": 10,
    "css_files": 5,
    "js_files": 15,
    "images": 30,
    "total_size": "2.5 MB"
  },
  "visited_urls": [...],
  "failed_downloads": [...]
}
```

### 技术栈报告（`tech_report.json`）

```json
{
  "detected_technologies": {
    "frameworks": ["React", "Next.js"],
    "ui_libraries": ["Tailwind CSS"],
    "build_tools": ["Webpack"]
  },
  "recommendations": [...]
}
```

### AI 分析报告（`ai_analysis.json`）- 实验性

```json
{
  "ai_enabled": true,
  "analysis": {
    "summary": "...",
    "suggestions": [
      "优化建议1",
      "优化建议2"
    ]
  }
}
```

## 🔧 高级功能

### 自定义技术检测规则

编辑 `src/detector.py` 中的 `detection_rules`：

```python
'frameworks': {
    'YourFramework': {
        'patterns': [r'your-framework\.js'],
        'package_names': ['your-framework']
    }
}
```

### 扩展 AI 分析

编辑 `src/ai_analyzer.py`，配置真实的 AI API 调用：

```python
# 需要自行实现 API 调用逻辑
# 当前版本使用规则引擎，非真实 AI
```

## 🐛 故障排除

### 问题: Playwright 浏览器未安装

```bash
playwright install chromium
```

### 问题: 某些资源下载失败

工具已优化错误提示：
- **404 错误**：自动跳过（常见的失效链接，不影响使用）
- **二进制文件**：自动识别并跳过（字体文件等）
- **关键错误**：才会显示警告

检查输出信息：
```
[OK] 下载完成: 104 个文件, 已跳过 2 个无效资源
```

如有关键资源下载失败，可查看 `download_report.json` 中的 `failed_downloads` 部分。

### 问题: 本地打开HTML样式丢失

建议使用本地服务器而非直接双击打开：

```bash
# Python 自带服务器
python -m http.server 8000

# 然后访问 http://localhost:8000
```

### 问题: Chrome 占用端口

使用 `--chrome-mode playwright` 模式（默认），无需关闭 Chrome。

### 问题: 需要登录才能访问的页面

使用 `--use-browser-data` 参数：

```bash
# 方法1: 先在浏览器中登录，然后运行
python main.py clone <URL> --use-browser-data

# 方法2: 使用用户确认功能，在打开的浏览器中登录
python main.py clone <URL> --use-browser-data
# 等浏览器打开后，手动登录，然后输入 y 确认
```

### 问题: 输入 y 后页面内容变了

**已修复**：工具会直接在用户确认的页面开始下载，不会重新打开新页面。

### 问题: 输入 n 取消后还是创建了文件夹

**已修复**：输入 n 取消后不会创建任何目录。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

如果你想帮助完善 AI 功能，欢迎：
1. 接入真实的 AI API（Anthropic Claude、OpenAI GPT）
2. 实现更智能的组件提取逻辑
3. 改进技术栈检测算法

## 📜 许可证

MIT License

## ⚠️ 法律声明与免责条款

### 使用限制

本工具**仅供以下合法用途**：
- ✅ 学习和研究 Web 技术
- ✅ 备份您**自己拥有版权**的网站
- ✅ 在**获得明确授权**的情况下复制网站
- ✅ 分析公开可用的技术栈和最佳实践
- ✅ 用于个人学习，使用 `example.com` 等测试域名

### 明确禁止

❌ **严禁用于以下行为**：
1. 复制任何商业网站用于商业目的或竞争
2. 侵犯他人知识产权、版权、商标权
3. 绕过反爬虫机制进行大规模爬取
4. 未经授权复制受版权保护的内容
5. 违反目标网站的服务条款和 robots.txt
6. 对目标服务器造成过度负担

### 免责条款

- 使用者需**自行承担**所有法律责任
- 开发者**不对任何侵权行为负责**
- 开发者不对使用本工具造成的任何损失负责
- 本工具仅作为技术研究和学习工具提供

### 合规建议

在使用本工具前，请务必：
1. ✅ 检查目标网站的版权声明和使用条款
2. ✅ 查看并遵守 robots.txt 文件
3. ✅ 考虑联系网站所有者获取授权
4. ✅ 仅用于个人学习，不得分发或商用
5. ✅ 测试时使用 `example.com` 或自己的网站

**使用本工具即表示您同意遵守以上条款**

## 🎉 致谢

基于以下开源项目：

- **Playwright** - 浏览器自动化
- **Beautiful Soup** - HTML 解析
- **Click** - CLI 框架
- **Colorama** - 终端彩色输出

---

**⭐ 如果这个工具对你有帮助，请给个 Star！**

## 🔮 未来计划（欢迎贡献）

- [ ] 真正的 AI 分析（接入 Claude/GPT API）
- [ ] HTML 到 React/Vue 组件的智能转换
- [ ] 更强大的技术栈检测
- [ ] 支持更多浏览器引擎
- [ ] 增量下载和差异检测
- [ ] GUI 图形界面
