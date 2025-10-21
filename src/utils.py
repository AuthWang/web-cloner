"""
工具函数模块
"""

import os
import re
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse, urljoin
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def sanitize_filename(filename: str) -> str:
    """清理文件名,移除非法字符"""
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 限制长度
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    return filename


def get_domain_from_url(url: str) -> str:
    """从URL中提取域名"""
    parsed = urlparse(url)
    return parsed.netloc


def url_to_filename(url: str, base_dir: Path) -> Path:
    """将URL转换为本地文件路径"""
    parsed = urlparse(url)

    # 处理路径
    path = parsed.path
    if not path or path == '/':
        path = '/index.html'
    elif not os.path.splitext(path)[1]:
        # 如果没有扩展名,添加 index.html
        path = path.rstrip('/') + '/index.html'

    # 清理并组合路径
    path = path.lstrip('/')
    parts = [sanitize_filename(p) for p in path.split('/')]

    return base_dir / parsed.netloc / Path(*parts)


def is_same_domain(url1: str, url2: str) -> bool:
    """检查两个URL是否属于同一域名"""
    return get_domain_from_url(url1) == get_domain_from_url(url2)


def normalize_url(url: str, base_url: str) -> str:
    """规范化URL,处理相对路径"""
    return urljoin(base_url, url)


def get_file_hash(file_path: Path) -> str:
    """计算文件的MD5哈希值"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def save_json(data: Dict, file_path: Path) -> None:
    """保存数据为JSON文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: Path) -> Optional[Dict]:
    """从JSON文件加载数据"""
    if not file_path.exists():
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_links_from_html(html: str, base_url: str) -> List[str]:
    """从HTML中提取所有链接"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    links = []

    # 提取 <a> 标签的链接
    for tag in soup.find_all('a', href=True):
        url = normalize_url(tag['href'], base_url)
        if url not in links:
            links.append(url)

    return links


def extract_resources_from_html(html: str, base_url: str) -> Dict[str, List[str]]:
    """从HTML中提取所有资源链接"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    resources = {
        'css': [],
        'js': [],
        'images': [],
        'fonts': [],
        'other': []
    }

    # CSS 文件
    for tag in soup.find_all('link', rel='stylesheet'):
        if tag.get('href'):
            resources['css'].append(normalize_url(tag['href'], base_url))

    # JavaScript 文件
    for tag in soup.find_all('script', src=True):
        resources['js'].append(normalize_url(tag['src'], base_url))

    # 图片
    for tag in soup.find_all('img', src=True):
        resources['images'].append(normalize_url(tag['src'], base_url))

    # 背景图片和其他CSS资源
    for tag in soup.find_all(style=True):
        style = tag['style']
        urls = re.findall(r'url\(["\']?([^"\']+)["\']?\)', style)
        for url in urls:
            normalized = normalize_url(url, base_url)
            if any(normalized.endswith(ext) for ext in ['.woff', '.woff2', '.ttf', '.eot']):
                resources['fonts'].append(normalized)
            else:
                resources['other'].append(normalized)

    return resources


def format_bytes(bytes_num: int) -> str:
    """格式化字节数为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} TB"


def create_directory_structure(base_path: Path, structure: Dict) -> None:
    """根据字典结构创建目录"""
    for name, content in structure.items():
        path = base_path / name
        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            create_directory_structure(path, content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if content is not None:
                path.write_text(content, encoding='utf-8')
