# 📦 安装指南

## 快速安装

### 方法 0: 一键自动安装 (最推荐) 🚀

```bash
# 直接运行安装脚本
python install.py
```

这个 Python 脚本会自动:
- ✅ 检查 Python 版本
- ✅ 询问是否使用 uv (比 pip 快 10-100 倍)
- ✅ 安装所有依赖
- ✅ 安装 Playwright 浏览器
- ✅ 验证安装成功

**就这么简单!**

---

### 什么是 uv?

[uv](https://github.com/astral-sh/uv) 是一个极快的 Python 包管理器,比 pip 快 10-100 倍!

### 方法 1: 使用 uv 手动安装 ⚡

```bash
# Step 1: 安装 uv
pip install uv

# Step 2: 克隆或进入项目目录
cd downloadHtml

# Step 3: 使用 uv 安装依赖 (超快!)
uv pip install -e .

# Step 4: 安装 Playwright 浏览器
playwright install chromium

# Step 5: 验证安装
python main.py --help
```

**安装时间对比:**
- ✅ uv: ~10-20 秒
- ⏱️ pip: ~2-5 分钟

### 方法 2: 使用传统 pip

```bash
# Step 1: 进入项目目录
cd downloadHtml

# Step 2: 安装依赖
pip install -r requirements.txt

# Step 3: 安装 Playwright 浏览器
playwright install chromium

# Step 4: 验证安装
python main.py --help
```

## 系统要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows / Linux / macOS
- **磁盘空间**: 至少 500 MB (包含浏览器)
- **内存**: 建议 2GB+

## 安装可选依赖

### 开发工具

```bash
# 使用 uv
uv pip install -e ".[dev]"

# 使用 pip
pip install -e ".[dev]"
```

包括:
- pytest (测试框架)
- black (代码格式化)
- ruff (代码检查)

### 仅安装 AI 功能

如果只想要 AI 分析功能:

```bash
# Anthropic Claude
uv pip install anthropic

# 或 OpenAI GPT
uv pip install openai
```

## 验证安装

### 1. 检查 Python 版本

```bash
python --version
# 应该显示 Python 3.10 或更高
```

### 2. 检查依赖

```bash
python -c "import playwright; print('Playwright OK')"
python -c "import click; print('Click OK')"
python -c "from bs4 import BeautifulSoup; print('BeautifulSoup OK')"
```

### 3. 运行测试命令

```bash
python main.py info
```

应该看到工具信息界面。

### 4. 测试下载功能

```bash
python main.py download https://example.com -o ./test
```

## 常见问题

### Q: uv 安装失败怎么办?

使用传统 pip:
```bash
pip install -r requirements.txt
```

### Q: Playwright 浏览器安装失败?

尝试单独安装 Chromium:
```bash
python -m playwright install chromium
```

或者安装所有浏览器:
```bash
python -m playwright install
```

### Q: 在 Windows 上权限错误?

使用管理员权限运行命令提示符,或使用虚拟环境:

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 然后安装依赖
uv pip install -e .
```

### Q: 代理环境下如何安装?

```bash
# 设置代理
set HTTP_PROXY=http://proxy.example.com:8080
set HTTPS_PROXY=http://proxy.example.com:8080

# 然后正常安装
uv pip install -e .
```

### Q: 离线安装?

```bash
# 在有网络的机器上下载所有包
uv pip download -r requirements.txt -d ./packages

# 在离线机器上安装
uv pip install --no-index --find-links ./packages -r requirements.txt
```

## 升级依赖

### 升级所有依赖到最新版本

```bash
# 使用 uv
uv pip install --upgrade -e .

# 使用 pip
pip install --upgrade -r requirements.txt
```

### 升级特定包

```bash
# 升级 Playwright
uv pip install --upgrade playwright

# 升级 AI 库
uv pip install --upgrade anthropic openai
```

## 卸载

```bash
# 卸载 Python 包
pip uninstall -y $(pip freeze)

# 删除 Playwright 浏览器
playwright uninstall --all

# 删除项目目录
cd ..
rm -rf downloadHtml  # Linux/Mac
# 或
rmdir /s downloadHtml  # Windows
```

## Docker 安装 (可选)

如果你喜欢使用 Docker:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY . .

# 安装依赖
RUN uv pip install -e .

# 安装 Playwright
RUN playwright install --with-deps chromium

# 运行
CMD ["python", "main.py", "--help"]
```

构建和运行:
```bash
docker build -t website-cloner .
docker run -v $(pwd)/output:/app/output website-cloner clone https://example.com
```

## 获取帮助

安装遇到问题?

1. 查看 [README.md](README.md)
2. 检查 [GitHub Issues](https://github.com/your-repo/issues)
3. 运行诊断命令:

```bash
python -m pip check
playwright --version
```

---

**准备好了?开始使用吧!** → [QUICKSTART.md](QUICKSTART.md)
