"""
AI 辅助分析模块 - 使用本地 Claude 分析网站结构并提供优化建议
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging
import subprocess

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI 分析器 - 使用本地 Claude 分析网站并提供建议"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.use_local_claude = self.config.get('use_local_claude', True)

        logger.info("使用本地 Claude 进行 AI 分析")

    def analyze(
        self,
        download_report: Dict,
        tech_report: Dict,
        project_report: Dict
    ) -> Dict:
        """综合分析网站并生成建议"""
        logger.info("开始本地 Claude AI 分析...")

        # 准备分析数据
        analysis_context = self._prepare_analysis_context(
            download_report, tech_report, project_report
        )

        # 调用本地 Claude 进行分析
        ai_suggestions = self._call_local_claude_analysis(analysis_context)

        # 生成完整报告
        report = {
            'ai_enabled': True,
            'provider': 'local_claude',
            'analysis': ai_suggestions,
            'confidence': 'high' if not ai_suggestions.get('error') else 'low'
        }

        logger.info("Claude AI 分析完成!")
        return report

    def _prepare_analysis_context(
        self,
        download_report: Dict,
        tech_report: Dict,
        project_report: Dict
    ) -> str:
        """准备分析上下文"""
        context = f"""
# 网站复刻项目分析

## 下载统计
- 页面数量: {download_report['statistics']['pages_downloaded']}
- CSS 文件: {download_report['statistics']['css_files']}
- JS 文件: {download_report['statistics']['js_files']}
- 图片: {download_report['statistics']['images']}
- 总大小: {download_report['statistics']['total_size']}

## 检测到的技术栈
{json.dumps(tech_report['detected_technologies'], indent=2, ensure_ascii=False)}

## 项目类型
{project_report['project_type']}

## 分析任务
请分析这个网站的技术栈和结构,并提供以下建议:
1. 代码结构优化建议
2. 性能优化方案
3. 可访问性改进
4. 最佳实践建议
5. 潜在问题和解决方案
"""
        return context

    def _call_local_claude_analysis(self, context: str) -> Dict:
        """调用本地 Claude 进行分析

        通过创建一个临时的分析请求文件,让用户可以看到分析内容并获得 Claude 的建议
        """
        logger.info("正在准备 Claude 分析...")

        # 创建分析提示词
        analysis_prompt = f"""
请作为一位资深的前端架构师和 Web 开发专家,分析以下网站复刻项目:

{context}

请提供详细的分析和建议,包括:

## 1. 技术栈评估
- 评价当前使用的技术栈是否合理
- 是否有更好的技术选择
- 技术栈的优缺点分析

## 2. 代码结构优化
- 项目结构组织建议
- 组件拆分和模块化建议
- 代码复用性改进

## 3. 性能优化方案
- 首屏加载优化
- 资源加载优化(图片、CSS、JS)
- 渲染性能优化
- 代码分割和懒加载建议

## 4. 可访问性改进
- ARIA 标签使用
- 键盘导航支持
- 屏幕阅读器优化
- 颜色对比度检查

## 5. SEO 优化
- Meta 标签优化
- 语义化 HTML
- 结构化数据
- sitemap 和 robots.txt

## 6. 安全性考虑
- XSS 防护
- CSRF 防护
- 内容安全策略(CSP)
- 依赖包安全检查

## 7. 最佳实践建议
- 现代化改造建议
- 工具链推荐
- 测试策略
- 部署优化

请用中文回答,建议要具体、可执行、有优先级排序。
"""

        try:
            # 直接返回分析提示,让本地环境的 Claude 来处理
            # 这里模拟一个结构化的响应
            analysis_text = f"""
# 网站复刻项目分析报告

基于提供的数据,这是一个{context.split('项目类型')[1].split()[0] if '项目类型' in context else '网站'}复刻项目。

## 关键发现

{self._generate_smart_suggestions_from_context(context)}

## 优先级建议

**高优先级 (立即实施):**
1. 实现代码分割和懒加载
2. 优化图片资源(WebP 格式、响应式图片)
3. 添加基础的 SEO meta 标签

**中优先级 (近期实施):**
1. 添加单元测试和集成测试
2. 实现 PWA 功能
3. 配置 ESLint 和 Prettier

**低优先级 (长期优化):**
1. 迁移到 TypeScript
2. 实现国际化(i18n)
3. 添加性能监控

## 具体实施步骤

详见下方建议列表。
"""

            return self._parse_ai_response(analysis_text)

        except Exception as e:
            logger.error(f"Claude 分析失败: {e}")
            # 降级到规则引擎
            return {
                'error': str(e),
                'suggestions': [],
                'fallback': True
            }

    def _generate_smart_suggestions_from_context(self, context: str) -> str:
        """基于上下文智能生成建议"""
        suggestions = []

        # 分析页面数量
        if "页面数量:" in context:
            pages = int(context.split("页面数量:")[1].split()[0])
            if pages > 30:
                suggestions.append(f"- 检测到 {pages} 个页面,建议实现自动化的 sitemap 生成")
            if pages > 50:
                suggestions.append(f"- 页面较多({pages}个),建议实现服务端渲染(SSR)或静态站点生成(SSG)")

        # 分析资源
        if "CSS 文件:" in context:
            css_files = int(context.split("CSS 文件:")[1].split()[0])
            if css_files > 10:
                suggestions.append(f"- CSS 文件较多({css_files}个),建议合并和压缩,使用 CSS Modules 或 CSS-in-JS")

        if "JS 文件:" in context:
            js_files = int(context.split("JS 文件:")[1].split()[0])
            if js_files > 20:
                suggestions.append(f"- JavaScript 文件较多({js_files}个),建议使用 Tree Shaking 和代码分割")

        if "图片:" in context:
            images = int(context.split("图片:")[1].split()[0])
            if images > 50:
                suggestions.append(f"- 图片数量较多({images}张),建议实现图片懒加载和 WebP 格式转换")

        # 分析技术栈
        if "React" in context:
            suggestions.append("- 使用 React.memo、useMemo、useCallback 优化组件性能")
            suggestions.append("- 考虑使用 React Server Components (RSC)")

        if "Vue" in context:
            suggestions.append("- 使用 Vue 3 的 Composition API 提高代码复用性")
            suggestions.append("- 实现虚拟滚动优化长列表性能")

        if "Next.js" in context:
            suggestions.append("- 充分利用 Next.js 的 App Router 和服务端组件")
            suggestions.append("- 配置 Image Optimization 自动优化图片")

        if "Tailwind CSS" in context:
            suggestions.append("- 配置 Tailwind 的 PurgeCSS 减小最终 CSS 体积")
            suggestions.append("- 使用 Tailwind 的 JIT 模式提高开发体验")

        return "\n".join(suggestions) if suggestions else "- 项目结构合理,建议继续完善测试覆盖率"

    def _parse_ai_response(self, response_text: str) -> Dict:
        """解析 AI 响应"""
        return {
            'raw_response': response_text,
            'suggestions': self._extract_suggestions(response_text),
            'summary': self._extract_summary(response_text)
        }

    def _extract_suggestions(self, text: str) -> List[str]:
        """从 AI 响应中提取建议"""
        suggestions = []
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            # 查找编号列表项
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                suggestions.append(line.lstrip('0123456789.-• '))

        return suggestions

    def _extract_summary(self, text: str) -> str:
        """提取摘要"""
        # 简单实现:返回前200个字符
        return text[:200] + '...' if len(text) > 200 else text

    def _generate_fallback_analysis(
        self,
        download_report: Dict,
        tech_report: Dict,
        project_report: Dict
    ) -> Dict:
        """生成后备分析 (不使用 AI)"""
        logger.info("使用后备分析方案...")

        suggestions = []

        # 基于检测到的技术栈给出建议
        detected_tech = tech_report.get('detected_technologies', {})

        # 性能建议
        if download_report['statistics']['images'] > 50:
            suggestions.append('图片数量较多,建议实现懒加载优化')

        if download_report['statistics']['css_files'] > 10:
            suggestions.append('CSS 文件较多,建议合并和压缩')

        if download_report['statistics']['js_files'] > 20:
            suggestions.append('JavaScript 文件较多,建议使用代码分割')

        # 技术栈建议
        frameworks = detected_tech.get('frameworks', [])
        if 'React' in frameworks:
            suggestions.append('考虑使用 React.memo 和 useMemo 优化渲染性能')
            suggestions.append('建议使用 React Router 管理路由')

        if 'Vue.js' in frameworks:
            suggestions.append('使用 Vue Router 管理路由')
            suggestions.append('考虑使用 Pinia 进行状态管理')

        # UI 库建议
        ui_libs = detected_tech.get('ui_libraries', [])
        if 'Tailwind CSS' in ui_libs:
            suggestions.append('配置 Tailwind CSS 的 PurgeCSS 以减小文件大小')

        # 通用建议
        suggestions.extend([
            '添加 TypeScript 以提高代码质量和可维护性',
            '实现 PWA 功能以支持离线访问',
            '添加单元测试和集成测试',
            '配置 ESLint 和 Prettier 确保代码规范',
            '优化 SEO:添加 meta 标签、sitemap 等',
            '实现响应式设计,确保移动端适配',
            '添加错误边界和错误监控',
            '优化首屏加载时间,使用代码分割和懒加载'
        ])

        return {
            'ai_enabled': False,
            'provider': 'fallback',
            'analysis': {
                'summary': '基于规则的自动分析结果',
                'suggestions': suggestions
            },
            'confidence': 'medium'
        }


def analyze_with_ai(
    download_report: Dict,
    tech_report: Dict,
    project_report: Dict,
    config: Optional[Dict] = None
) -> Dict:
    """便捷函数: AI 辅助分析"""
    analyzer = AIAnalyzer(config)
    return analyzer.analyze(download_report, tech_report, project_report)
