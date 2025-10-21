"""
技术栈检测引擎 - 识别网站使用的技术、框架和工具
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TechStackDetector:
    """技术栈检测器"""

    def __init__(self):
        self.detected_tech: Dict[str, Set[str]] = defaultdict(set)
        self.confidence_scores: Dict[str, float] = {}

        # 技术检测规则
        self.detection_rules = self._load_detection_rules()

    def _load_detection_rules(self) -> Dict:
        """加载技术检测规则"""
        return {
            # 前端框架
            'frameworks': {
                'React': {
                    'patterns': [
                        r'react(-dom)?\.production\.min\.js',
                        r'react(-dom)?\.development\.js',
                        r'_reactRootContainer',
                        r'__REACT_DEVTOOLS_GLOBAL_HOOK__'
                    ],
                    'dom_signatures': ['data-reactroot', 'data-reactid'],
                    'package_names': ['react', 'react-dom']
                },
                'Vue.js': {
                    'patterns': [
                        r'vue\.js',
                        r'vue\.min\.js',
                        r'vue\.runtime\.esm\.js',
                        r'__VUE__'
                    ],
                    'dom_signatures': ['v-if', 'v-for', 'v-model', '@click'],
                    'package_names': ['vue']
                },
                'Angular': {
                    'patterns': [
                        r'angular\.js',
                        r'angular\.min\.js',
                        r'ng-version',
                        r'@angular/core'
                    ],
                    'dom_signatures': ['ng-app', 'ng-controller', '[ngfor]'],
                    'package_names': ['@angular/core']
                },
                'Next.js': {
                    'patterns': [
                        r'_next/static',
                        r'__NEXT_DATA__',
                        r'next\.js'
                    ],
                    'package_names': ['next']
                },
                'Nuxt.js': {
                    'patterns': [
                        r'_nuxt/',
                        r'__NUXT__'
                    ],
                    'package_names': ['nuxt']
                },
                'Svelte': {
                    'patterns': [
                        r'svelte',
                        r'\.svelte\.'
                    ],
                    'package_names': ['svelte']
                }
            },

            # UI 库和组件库
            'ui_libraries': {
                'Bootstrap': {
                    'patterns': [
                        r'bootstrap\.css',
                        r'bootstrap\.min\.css',
                        r'bootstrap\.js'
                    ],
                    'dom_signatures': ['class="container"', 'class="row"', 'class="col-'],
                    'package_names': ['bootstrap']
                },
                'Tailwind CSS': {
                    'patterns': [
                        r'tailwind\.css',
                        r'@tailwind'
                    ],
                    'dom_signatures': ['class="flex"', 'class="grid"', 'class=".*\s+(p|m|w|h)-\d+'],
                    'package_names': ['tailwindcss']
                },
                'Material-UI': {
                    'patterns': [
                        r'@mui/material',
                        r'@material-ui'
                    ],
                    'package_names': ['@mui/material', '@material-ui/core']
                },
                'Ant Design': {
                    'patterns': [
                        r'antd\.css',
                        r'antd\.min\.css'
                    ],
                    'package_names': ['antd']
                }
            },

            # JavaScript 库
            'js_libraries': {
                'jQuery': {
                    'patterns': [
                        r'jquery\.js',
                        r'jquery\.min\.js',
                        r'\$\(document\)\.ready'
                    ],
                    'package_names': ['jquery']
                },
                'Lodash': {
                    'patterns': [
                        r'lodash\.js',
                        r'lodash\.min\.js',
                        r'_\.map'
                    ],
                    'package_names': ['lodash']
                },
                'Axios': {
                    'patterns': [
                        r'axios\.js',
                        r'axios\.min\.js'
                    ],
                    'package_names': ['axios']
                }
            },

            # 构建工具
            'build_tools': {
                'Webpack': {
                    'patterns': [
                        r'webpack',
                        r'webpackJsonp',
                        r'__webpack_require__'
                    ],
                    'package_names': ['webpack']
                },
                'Vite': {
                    'patterns': [
                        r'/@vite/',
                        r'vite\.svg',
                        r'__vite__'
                    ],
                    'package_names': ['vite']
                },
                'Parcel': {
                    'patterns': [
                        r'parcelRequire'
                    ],
                    'package_names': ['parcel']
                }
            },

            # CSS 预处理器
            'css_preprocessors': {
                'Sass/SCSS': {
                    'patterns': [
                        r'\.scss',
                        r'sass-loader'
                    ],
                    'package_names': ['sass', 'node-sass']
                },
                'Less': {
                    'patterns': [
                        r'\.less',
                        r'less-loader'
                    ],
                    'package_names': ['less']
                },
                'Stylus': {
                    'patterns': [
                        r'\.styl',
                        r'stylus-loader'
                    ],
                    'package_names': ['stylus']
                }
            },

            # 后端技术 (通过响应头检测)
            'backend': {
                'Express.js': {
                    'headers': ['x-powered-by: Express']
                },
                'Django': {
                    'patterns': [r'csrfmiddlewaretoken']
                },
                'Flask': {
                    'patterns': [r'werkzeug']
                }
            },

            # 分析工具
            'analytics': {
                'Google Analytics': {
                    'patterns': [
                        r'google-analytics\.com/analytics\.js',
                        r'gtag/js',
                        r'UA-\d+-\d+'
                    ]
                },
                'Google Tag Manager': {
                    'patterns': [
                        r'googletagmanager\.com/gtm\.js',
                        r'GTM-[A-Z0-9]+'
                    ]
                }
            }
        }

    def detect_from_directory(self, directory: Path) -> Dict:
        """从下载的网站目录检测技术栈"""
        logger.info(f"开始检测技术栈: {directory}")

        # 检测 HTML 文件
        html_files = list(directory.rglob('*.html'))
        for html_file in html_files:
            self._analyze_html_file(html_file)

        # 检测 JavaScript 文件
        js_files = list(directory.rglob('*.js'))
        for js_file in js_files[:50]:  # 限制分析数量
            self._analyze_js_file(js_file)

        # 检测 CSS 文件
        css_files = list(directory.rglob('*.css'))
        for css_file in css_files[:50]:
            self._analyze_css_file(css_file)

        # 检测 package.json
        package_json = self._find_package_json(directory)
        if package_json:
            self._analyze_package_json(package_json)

        # 生成检测报告
        report = self._generate_report()
        logger.info(f"技术栈检测完成,共发现 {len(self.detected_tech)} 类技术")

        return report

    def _analyze_html_file(self, file_path: Path) -> None:
        """分析 HTML 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser')

            # 检测所有类别的技术
            for category, techs in self.detection_rules.items():
                for tech_name, rules in techs.items():
                    # 检查模式匹配
                    if 'patterns' in rules:
                        for pattern in rules['patterns']:
                            if re.search(pattern, content, re.IGNORECASE):
                                self.detected_tech[category].add(tech_name)

                    # 检查 DOM 签名
                    if 'dom_signatures' in rules:
                        for signature in rules['dom_signatures']:
                            if signature.startswith('class='):
                                class_pattern = signature.replace('class="', '').replace('"', '')
                                if soup.find(class_=re.compile(class_pattern)):
                                    self.detected_tech[category].add(tech_name)
                            elif soup.find(attrs={signature.split('=')[0]: True}):
                                self.detected_tech[category].add(tech_name)

        except Exception as e:
            logger.warning(f"分析 HTML 文件失败 {file_path}: {e}")

    def _analyze_js_file(self, file_path: Path) -> None:
        """分析 JavaScript 文件"""
        try:
            # 限制文件大小
            if file_path.stat().st_size > 5 * 1024 * 1024:  # 5MB
                return

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检测框架和库
            for category in ['frameworks', 'js_libraries', 'build_tools']:
                if category in self.detection_rules:
                    for tech_name, rules in self.detection_rules[category].items():
                        if 'patterns' in rules:
                            for pattern in rules['patterns']:
                                if re.search(pattern, content, re.IGNORECASE):
                                    self.detected_tech[category].add(tech_name)

        except Exception as e:
            logger.warning(f"分析 JS 文件失败 {file_path}: {e}")

    def _analyze_css_file(self, file_path: Path) -> None:
        """分析 CSS 文件"""
        try:
            if file_path.stat().st_size > 2 * 1024 * 1024:  # 2MB
                return

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检测 UI 库和预处理器
            for category in ['ui_libraries', 'css_preprocessors']:
                if category in self.detection_rules:
                    for tech_name, rules in self.detection_rules[category].items():
                        if 'patterns' in rules:
                            for pattern in rules['patterns']:
                                if re.search(pattern, content, re.IGNORECASE):
                                    self.detected_tech[category].add(tech_name)

        except Exception as e:
            logger.warning(f"分析 CSS 文件失败 {file_path}: {e}")

    def _find_package_json(self, directory: Path) -> Optional[Path]:
        """查找 package.json 文件"""
        package_files = list(directory.rglob('package.json'))
        return package_files[0] if package_files else None

    def _analyze_package_json(self, file_path: Path) -> None:
        """分析 package.json 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)

            # 合并 dependencies 和 devDependencies
            all_deps = {}
            all_deps.update(package_data.get('dependencies', {}))
            all_deps.update(package_data.get('devDependencies', {}))

            # 检测所有包
            for category, techs in self.detection_rules.items():
                for tech_name, rules in techs.items():
                    if 'package_names' in rules:
                        for package_name in rules['package_names']:
                            if package_name in all_deps:
                                self.detected_tech[category].add(tech_name)

        except Exception as e:
            logger.warning(f"分析 package.json 失败 {file_path}: {e}")

    def _generate_report(self) -> Dict:
        """生成技术栈检测报告"""
        report = {
            'summary': {
                'total_categories': len(self.detected_tech),
                'total_technologies': sum(len(techs) for techs in self.detected_tech.values())
            },
            'detected_technologies': {},
            'recommendations': []
        }

        # 整理检测到的技术
        for category, techs in self.detected_tech.items():
            if techs:
                report['detected_technologies'][category] = list(techs)

        # 生成推荐
        report['recommendations'] = self._generate_recommendations()

        return report

    def _generate_recommendations(self) -> List[str]:
        """基于检测到的技术栈生成推荐"""
        recommendations = []

        # 推荐项目类型
        if 'React' in self.detected_tech.get('frameworks', set()):
            if 'Next.js' in self.detected_tech.get('frameworks', set()):
                recommendations.append("建议创建 Next.js 项目结构")
            else:
                recommendations.append("建议创建 React + Vite 项目结构")

        elif 'Vue.js' in self.detected_tech.get('frameworks', set()):
            if 'Nuxt.js' in self.detected_tech.get('frameworks', set()):
                recommendations.append("建议创建 Nuxt.js 项目结构")
            else:
                recommendations.append("建议创建 Vue + Vite 项目结构")

        elif 'Angular' in self.detected_tech.get('frameworks', set()):
            recommendations.append("建议创建 Angular CLI 项目结构")

        # 推荐 UI 库
        if 'Tailwind CSS' in self.detected_tech.get('ui_libraries', set()):
            recommendations.append("集成 Tailwind CSS 配置")

        if 'Bootstrap' in self.detected_tech.get('ui_libraries', set()):
            recommendations.append("集成 Bootstrap 依赖")

        return recommendations


def detect_tech_stack(directory: Path) -> Dict:
    """便捷函数: 检测技术栈"""
    detector = TechStackDetector()
    return detector.detect_from_directory(directory)
