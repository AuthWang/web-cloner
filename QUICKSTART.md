# 🚀 快速开始指南

## 30 秒上手

### 1. 安装依赖

#### 一键安装 (推荐) 🚀

```bash
python install.py
```

就这么简单!脚本会自动处理一切。

#### 手动安装

```bash
# 使用 uv (推荐,10倍速)
pip install uv
uv pip install -e .
playwright install chromium

# 或使用 pip
pip install -r requirements.txt
playwright install chromium
```

### 2. 复刻你的第一个网站

```bash
python main.py clone https://example.com
```

就这么简单!工具会自动:
- ✅ 下载所有资源
- ✅ 检测技术栈
- ✅ 生成可运行的项目

## 📍 输出位置

所有输出都在 `output/` 目录下:

```
output/
├── downloads/example.com_20250122_123456/  # 下载的原始文件
├── projects/example.com_20250122_123456/   # 生成的项目
└── reports/example.com_20250122_123456/    # 分析报告
```

## 🎯 运行生成的项目

```bash
# 进入项目目录
cd output/projects/example.com_*

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

> 💡 **提示**: 如果生成的项目包含 package.json，需要先安装 Node.js 依赖

## 🔥 常用命令

### 启用 AI 分析

```bash
# 设置 API Key
set ANTHROPIC_API_KEY=your_api_key_here

# 运行
python main.py clone https://example.com --enable-ai
```

### 只下载小型网站

```bash
python main.py clone https://example.com --max-depth 1 --max-pages 10
```

### 不下载图片(节省空间)

```bash
python main.py clone https://example.com --no-images
```

### 查看浏览器窗口(调试)

```bash
python main.py clone https://example.com --no-headless
```

## 💡 实用技巧

### 1. 快速预览技术栈

```bash
python main.py download https://example.com -o ./temp
python main.py detect ./temp
```

### 2. 批量处理多个网站

创建 `sites.txt`:
```
https://site1.com
https://site2.com
https://site3.com
```

批处理脚本:
```bash
for url in $(cat sites.txt); do
    python main.py clone "$url"
done
```

### 3. 自定义输出名称

```bash
python main.py clone https://example.com -o my-awesome-site
```

### 4. 纯静态网站模式

生成的项目可直接通过双击 `index.html` 打开，无需服务器！

工具会自动：
- ✅ 移除所有 JavaScript 引用（保留纯 HTML+CSS）
- ✅ 下载所有背景图片和字体（从 CSS、内联样式、`<style>` 标签）
- ✅ 重写所有资源路径为本地相对路径

**特别提示**：智能资源提取确保所有被引用的资源都会被下载：
- CSS 中的 `url()` 引用 → 自动提取并下载
- 内联样式的背景图 → 自动提取并下载
- `<style>` 标签的字体 → 自动提取并下载

## ⚙️ 配置优化

编辑 `config.py` 进行全局配置:

```python
# 提高下载速度
DOWNLOAD_CONFIG = {
    "max_depth": 2,      # 减少深度
    "max_pages": 20,     # 限制页面数
}

# 调整浏览器性能
BROWSER_CONFIG = {
    "timeout": 60000,    # 增加超时时间
}
```

## 🐛 常见问题

**Q: 下载很慢怎么办?**
- 减少 `max-depth` 和 `max-pages`
- 使用 `--no-images` 跳过图片

**Q: 某些资源下载失败?**
- 检查 `reports/*/download_report.json` 查看失败原因
- 可能是反爬虫机制,尝试添加延迟

**Q: 生成的项目无法运行?**
- 确保安装了所有依赖:`npm install`
- 查看 `README.md` 了解特定项目的要求

## 📚 下一步

- 查看完整文档: [README.md](README.md)
- 学习代码示例: [examples/example.py](examples/example.py)
- 自定义技术检测规则: `src/detector.py`
- 添加新的项目模板: `src/reconstructor.py`

## 🎉 祝你使用愉快!

有问题?欢迎提 Issue!
