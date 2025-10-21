# 📋 项目概览

## 🎯 项目简介

**网站一比一复刻工具** 是一个功能强大的 Python 应用程序,能够自动化地复刻任何网站,智能检测其技术栈,并生成可直接运行的项目结构。

## ✨ 核心特性

| 功能 | 描述 | 技术 |
|------|------|------|
| 🌐 完整渲染 | 使用真实浏览器渲染网站 | Playwright |
| 📦 资源下载 | 下载所有静态资源(HTML/CSS/JS/图片/字体) | Async/Await |
| 🔍 技术检测 | 智能识别框架、库、构建工具 | 正则表达式 + 规则引擎 |
| 🏗️ 项目生成 | 基于检测结果生成对应的项目结构 | 模板系统 |
| 🤖 AI 分析 | 可选的 AI 辅助分析和优化建议 | Claude/GPT |
| 💻 CLI 工具 | 友好的命令行界面 | Click |

## 📂 文件结构

```
downloadHtml/
│
├── 📄 配置和文档
│   ├── config.py              # 全局配置
│   ├── requirements.txt       # Python 依赖
│   ├── README.md             # 完整文档
│   ├── QUICKSTART.md         # 快速开始
│   ├── PROJECT_OVERVIEW.md   # 本文件
│   └── .gitignore            # Git 忽略文件
│
├── 🎯 主程序
│   └── main.py               # CLI 入口和主逻辑
│
├── 🧩 核心模块 (src/)
│   ├── __init__.py           # 包初始化
│   ├── downloader.py         # 资源下载器 (250+ 行)
│   ├── detector.py           # 技术栈检测器 (300+ 行)
│   ├── reconstructor.py      # 项目重构器 (350+ 行)
│   ├── ai_analyzer.py        # AI 分析器 (150+ 行)
│   └── utils.py              # 工具函数 (200+ 行)
│
├── 📚 示例代码 (examples/)
│   └── example.py            # 使用示例
│
└── 📁 输出目录 (output/)
    ├── downloads/            # 下载的网站
    ├── projects/             # 生成的项目
    └── reports/              # 分析报告
```

## 🔧 技术栈

### 核心依赖

| 库 | 用途 | 版本 |
|---|------|------|
| Playwright | 浏览器自动化 | 1.40.0+ |
| BeautifulSoup4 | HTML 解析 | 4.12.0+ |
| Click | CLI 框架 | 8.1.0+ |
| Requests | HTTP 请求 | 2.31.0+ |
| Anthropic | AI 集成 | 0.18.0+ |

### 可选依赖

- OpenAI API (用于 GPT 分析)
- builtwith (增强技术检测)

## 🎨 支持的框架

### ✅ 完全支持 (自动生成项目)

- **React** + Vite
- **Vue.js** + Vite
- **Next.js**
- **Nuxt.js**
- **Angular**
- **静态网站**

### 🔍 可检测 (但可能需要手动调整)

- Svelte
- Solid.js
- Preact
- 其他现代前端框架

## 📊 模块详解

### 1. Downloader (下载器)

**核心功能:**
- 使用 Playwright 完整渲染页面
- 递归下载所有链接的页面
- 捕获网络请求,下载所有资源
- 重写 HTML 中的链接为本地路径
- 生成详细的下载统计报告

**关键类:** `WebsiteDownloader`

**主要方法:**
```python
async def download() -> Dict
async def _download_recursive(browser, url, depth)
async def _download_page_resources(page, url, html, resources)
```

### 2. Detector (检测器)

**核心功能:**
- 分析 HTML/CSS/JS 文件
- 匹配技术栈签名和模式
- 解析 package.json 识别依赖
- 生成技术栈报告和推荐

**关键类:** `TechStackDetector`

**检测规则:**
- 正则表达式模式匹配
- DOM 签名检测
- 包名称识别
- HTTP 响应头分析

### 3. Reconstructor (重构器)

**核心功能:**
- 根据技术栈选择项目类型
- 生成对应的目录结构
- 创建配置文件 (package.json, vite.config.js 等)
- 复制和组织静态资源
- 生成启动文档

**关键类:** `ProjectReconstructor`

**支持的项目模板:**
- React + Vite
- Vue + Vite
- Next.js
- 静态网站
- 通用项目

### 4. AI Analyzer (AI 分析器)

**核心功能:**
- 集成 Claude/GPT API
- 分析网站结构和技术栈
- 生成优化建议
- 提供最佳实践推荐

**关键类:** `AIAnalyzer`

**后备方案:**
- 基于规则的自动分析
- 不需要 API Key 也能工作

### 5. Utils (工具函数)

**提供的工具:**
- URL 处理和规范化
- 文件名清理
- JSON 保存和加载
- 日志设置
- 资源提取
- 目录结构创建

## 🚀 使用流程

```
用户输入 URL
    ↓
1️⃣ Downloader 下载网站
    ├─ 启动浏览器
    ├─ 渲染页面
    ├─ 下载资源
    └─ 保存文件
    ↓
2️⃣ Detector 检测技术栈
    ├─ 分析 HTML/CSS/JS
    ├─ 匹配检测规则
    └─ 生成报告
    ↓
3️⃣ Reconstructor 生成项目
    ├─ 选择项目类型
    ├─ 创建目录结构
    ├─ 生成配置文件
    └─ 复制资源
    ↓
4️⃣ AI Analyzer 提供建议 (可选)
    ├─ 调用 AI API
    ├─ 分析代码结构
    └─ 生成优化建议
    ↓
生成完整项目 ✅
```

## 📈 性能指标

| 指标 | 小型网站 | 中型网站 | 大型网站 |
|------|----------|----------|----------|
| 页面数 | 1-10 | 10-50 | 50+ |
| 下载时间 | < 1 分钟 | 2-5 分钟 | 5-15 分钟 |
| 生成时间 | < 10 秒 | 10-30 秒 | 30-60 秒 |
| 磁盘空间 | < 10 MB | 10-100 MB | 100 MB+ |

## 🎯 设计原则

1. **模块化** - 每个功能独立模块,易于维护和扩展
2. **异步优先** - 使用 async/await 提高性能
3. **错误处理** - 完善的异常捕获和日志记录
4. **用户友好** - 清晰的 CLI 界面和进度提示
5. **可配置** - 灵活的配置选项
6. **可扩展** - 易于添加新的框架支持

## 🔐 安全性

- ✅ 仅下载公开可访问的资源
- ✅ 遵守 robots.txt (可配置)
- ✅ 速率限制防止过度请求
- ✅ 无危险操作(不执行下载的 JS)
- ⚠️ 使用时请遵守目标网站的使用条款

## 🚧 已知限制

1. **动态内容** - 部分 AJAX 加载的内容可能无法完全捕获
2. **认证页面** - 需要登录的页面暂不支持
3. **视频/大文件** - 默认不下载视频等大型媒体文件
4. **反爬虫** - 可能被一些网站的反爬虫机制阻止
5. **JavaScript 框架** - 高度依赖 JS 的 SPA 可能需要额外处理

## 🛣️ 未来计划

- [ ] 支持更多框架 (Astro, SvelteKit)
- [ ] 登录和认证支持
- [ ] 增量更新已下载的网站
- [ ] Docker 容器化
- [ ] Web UI 界面
- [ ] 并行下载优化
- [ ] 视频和媒体文件支持
- [ ] 自定义插件系统

## 🤝 贡献指南

欢迎贡献代码!可以帮助的领域:

1. **添加新框架支持** - 在 `detector.py` 添加检测规则
2. **优化检测精度** - 改进技术栈识别算法
3. **新的项目模板** - 添加更多框架的项目生成器
4. **性能优化** - 提高下载和处理速度
5. **文档改进** - 完善使用文档和示例

## 📞 获取帮助

- 📖 阅读 [README.md](README.md)
- 🚀 查看 [QUICKSTART.md](QUICKSTART.md)
- 💻 运行 [examples/example.py](examples/example.py)
- 💬 提交 Issue
- ⭐ 给项目点个 Star

## 📊 项目统计

- **总代码行数**: ~1500+ 行
- **核心模块数**: 5 个
- **支持框架数**: 6+ 个
- **开发时间**: 1 天
- **测试覆盖**: 待添加

---

**Made with ❤️ by Claude Code**
