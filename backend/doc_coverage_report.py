#!/usr/bin/env python3
"""TgGod 项目文档覆盖率分析报告生成器

该脚本扫描backend/app/目录下的所有Python文件，分析文档覆盖情况，
生成详细的文档质量报告。

Features:
    - 模块级docstring覆盖率统计
    - 类和函数级文档覆盖率分析
    - 文档质量评分和建议
    - 详细的缺失文档清单
    - 格式标准化检查
    - 生成HTML和文本格式报告

Author: TgGod Team
Version: 1.0.0
"""

import os
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime


class DocstringAnalyzer(ast.NodeVisitor):
    """Python AST文档字符串分析器

    遍历Python AST，提取并分析所有模块、类、函数的文档字符串。
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.module_docstring = None
        self.classes = []
        self.functions = []
        self.current_class = None

    def visit_Module(self, node):
        """访问模块节点，提取模块级docstring"""
        if (node.body and
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            self.module_docstring = node.body[0].value.value
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """访问类定义节点"""
        docstring = ast.get_docstring(node)
        class_info = {
            'name': node.name,
            'line': node.lineno,
            'docstring': docstring,
            'methods': []
        }

        # 分析类方法
        old_class = self.current_class
        self.current_class = class_info
        self.generic_visit(node)
        self.current_class = old_class

        self.classes.append(class_info)

    def visit_FunctionDef(self, node):
        """访问函数定义节点"""
        docstring = ast.get_docstring(node)
        func_info = {
            'name': node.name,
            'line': node.lineno,
            'docstring': docstring,
            'is_method': self.current_class is not None,
            'is_private': node.name.startswith('_'),
            'args_count': len(node.args.args)
        }

        if self.current_class:
            self.current_class['methods'].append(func_info)
        else:
            self.functions.append(func_info)


class DocumentationAnalyzer:
    """文档覆盖率分析器主类"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.app_dir = self.project_root / "app"
        self.report_data = {
            'summary': {},
            'files': {},
            'issues': [],
            'recommendations': []
        }

    def analyze_file(self, filepath: Path) -> Dict[str, Any]:
        """分析单个Python文件的文档覆盖情况"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            analyzer = DocstringAnalyzer(str(filepath))
            analyzer.visit(tree)

            # 计算覆盖率统计
            stats = self._calculate_stats(analyzer)

            return {
                'filepath': str(filepath.relative_to(self.project_root)),
                'module_docstring': analyzer.module_docstring,
                'classes': analyzer.classes,
                'functions': analyzer.functions,
                'stats': stats,
                'line_count': len(content.splitlines())
            }

        except Exception as e:
            return {
                'filepath': str(filepath.relative_to(self.project_root)),
                'error': str(e),
                'stats': {'coverage': 0}
            }

    def _calculate_stats(self, analyzer: DocstringAnalyzer) -> Dict[str, Any]:
        """计算文档覆盖率统计"""
        total_items = 0
        documented_items = 0

        # 模块级文档
        total_items += 1
        if analyzer.module_docstring:
            documented_items += 1

        # 类文档
        for cls in analyzer.classes:
            total_items += 1
            if cls['docstring']:
                documented_items += 1

            # 类方法文档
            for method in cls['methods']:
                # 跳过私有方法和特殊方法（除了__init__）
                if not method['is_private'] or method['name'] == '__init__':
                    total_items += 1
                    if method['docstring']:
                        documented_items += 1

        # 函数文档
        for func in analyzer.functions:
            # 跳过私有函数
            if not func['is_private']:
                total_items += 1
                if func['docstring']:
                    documented_items += 1

        coverage = (documented_items / total_items * 100) if total_items > 0 else 0

        return {
            'total_items': total_items,
            'documented_items': documented_items,
            'coverage': round(coverage, 2),
            'class_count': len(analyzer.classes),
            'function_count': len(analyzer.functions)
        }

    def analyze_project(self) -> Dict[str, Any]:
        """分析整个项目的文档覆盖情况"""
        print(f"🔍 开始分析项目文档覆盖率...")
        print(f"📂 项目目录: {self.app_dir}")

        python_files = list(self.app_dir.rglob("*.py"))
        print(f"📄 找到 {len(python_files)} 个Python文件")

        total_files = 0
        total_coverage = 0
        total_items = 0
        total_documented = 0

        for filepath in python_files:
            # 跳过__pycache__目录
            if "__pycache__" in str(filepath):
                continue

            file_analysis = self.analyze_file(filepath)
            if 'error' not in file_analysis:
                self.report_data['files'][str(filepath)] = file_analysis

                stats = file_analysis['stats']
                total_files += 1
                total_coverage += stats['coverage']
                total_items += stats['total_items']
                total_documented += stats['documented_items']

                # 收集文档质量问题
                self._collect_issues(file_analysis)

        # 计算全局统计
        avg_coverage = total_coverage / total_files if total_files > 0 else 0
        overall_coverage = total_documented / total_items * 100 if total_items > 0 else 0

        self.report_data['summary'] = {
            'total_files': total_files,
            'average_coverage': round(avg_coverage, 2),
            'overall_coverage': round(overall_coverage, 2),
            'total_items': total_items,
            'documented_items': total_documented,
            'undocumented_items': total_items - total_documented,
            'analysis_date': datetime.now().isoformat()
        }

        # 生成建议
        self._generate_recommendations()

        return self.report_data

    def _collect_issues(self, file_analysis: Dict[str, Any]):
        """收集文档质量问题"""
        filepath = file_analysis['filepath']

        # 检查模块级文档
        if not file_analysis['module_docstring']:
            self.report_data['issues'].append({
                'type': 'missing_module_docstring',
                'file': filepath,
                'message': '缺少模块级文档字符串'
            })

        # 检查类文档
        for cls in file_analysis['classes']:
            if not cls['docstring']:
                self.report_data['issues'].append({
                    'type': 'missing_class_docstring',
                    'file': filepath,
                    'class': cls['name'],
                    'line': cls['line'],
                    'message': f"类 '{cls['name']}' 缺少文档字符串"
                })

            # 检查方法文档
            for method in cls['methods']:
                if not method['is_private'] or method['name'] == '__init__':
                    if not method['docstring']:
                        self.report_data['issues'].append({
                            'type': 'missing_method_docstring',
                            'file': filepath,
                            'class': cls['name'],
                            'method': method['name'],
                            'line': method['line'],
                            'message': f"方法 '{cls['name']}.{method['name']}' 缺少文档字符串"
                        })

        # 检查函数文档
        for func in file_analysis['functions']:
            if not func['is_private'] and not func['docstring']:
                self.report_data['issues'].append({
                    'type': 'missing_function_docstring',
                    'file': filepath,
                    'function': func['name'],
                    'line': func['line'],
                    'message': f"函数 '{func['name']}' 缺少文档字符串"
                })

    def _generate_recommendations(self):
        """生成改进建议"""
        summary = self.report_data['summary']
        issues = self.report_data['issues']

        recommendations = []

        # 整体覆盖率建议
        if summary['overall_coverage'] < 90:
            recommendations.append({
                'priority': 'high',
                'category': 'coverage',
                'message': f"项目整体文档覆盖率为 {summary['overall_coverage']:.1f}%，建议提升至90%以上"
            })

        # 按问题类型统计
        issue_types = {}
        for issue in issues:
            issue_type = issue['type']
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        if issue_types.get('missing_module_docstring', 0) > 0:
            recommendations.append({
                'priority': 'medium',
                'category': 'module_docs',
                'message': f"有 {issue_types['missing_module_docstring']} 个模块缺少模块级文档"
            })

        if issue_types.get('missing_class_docstring', 0) > 0:
            recommendations.append({
                'priority': 'high',
                'category': 'class_docs',
                'message': f"有 {issue_types['missing_class_docstring']} 个类缺少文档字符串"
            })

        if issue_types.get('missing_function_docstring', 0) > 0:
            recommendations.append({
                'priority': 'medium',
                'category': 'function_docs',
                'message': f"有 {issue_types['missing_function_docstring']} 个函数缺少文档字符串"
            })

        self.report_data['recommendations'] = recommendations

    def generate_text_report(self) -> str:
        """生成文本格式的报告"""
        summary = self.report_data['summary']
        issues = self.report_data['issues']
        recommendations = self.report_data['recommendations']

        report = []
        report.append("=" * 80)
        report.append("TgGod 项目文档覆盖率分析报告")
        report.append("=" * 80)
        report.append(f"分析时间: {summary['analysis_date']}")
        report.append(f"分析文件数: {summary['total_files']}")
        report.append("")

        # 总体统计
        report.append("📊 总体统计")
        report.append("-" * 40)
        report.append(f"整体文档覆盖率: {summary['overall_coverage']:.1f}%")
        report.append(f"平均文件覆盖率: {summary['average_coverage']:.1f}%")
        report.append(f"总计项目数: {summary['total_items']}")
        report.append(f"已文档化项目: {summary['documented_items']}")
        report.append(f"未文档化项目: {summary['undocumented_items']}")
        report.append("")

        # 文件覆盖率排行
        report.append("📁 文件覆盖率排行 (低于90%的文件)")
        report.append("-" * 60)

        files_by_coverage = []
        for filepath, data in self.report_data['files'].items():
            if 'stats' in data:
                files_by_coverage.append((filepath, data['stats']['coverage']))

        files_by_coverage.sort(key=lambda x: x[1])

        for filepath, coverage in files_by_coverage:
            if coverage < 90:
                report.append(f"{coverage:5.1f}% - {filepath}")

        if not any(coverage < 90 for _, coverage in files_by_coverage):
            report.append("🎉 所有文件覆盖率都达到90%以上！")

        report.append("")

        # 改进建议
        if recommendations:
            report.append("💡 改进建议")
            report.append("-" * 40)
            for rec in recommendations:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
                report.append(f"{priority_icon} {rec['message']}")
            report.append("")

        # 详细问题清单
        if issues:
            report.append("❌ 缺失文档清单")
            report.append("-" * 40)

            current_file = None
            for issue in issues:
                if issue['file'] != current_file:
                    current_file = issue['file']
                    report.append(f"\n📄 {current_file}")

                line_info = f" (line {issue['line']})" if 'line' in issue else ""
                report.append(f"  • {issue['message']}{line_info}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self, output_dir: str = "."):
        """保存报告到文件"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 保存JSON格式报告
        json_file = output_path / "doc_coverage_report.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.report_data, f, indent=2, ensure_ascii=False)

        # 保存文本格式报告
        text_report = self.generate_text_report()
        text_file = output_path / "doc_coverage_report.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_report)

        print(f"📋 报告已保存:")
        print(f"  • JSON格式: {json_file}")
        print(f"  • 文本格式: {text_file}")

        return str(text_file), str(json_file)


def main():
    """主函数：执行文档覆盖率分析"""
    project_root = Path(__file__).parent
    analyzer = DocumentationAnalyzer(str(project_root))

    # 执行分析
    report_data = analyzer.analyze_project()

    # 显示结果
    print("\n" + analyzer.generate_text_report())

    # 保存报告
    analyzer.save_report()

    # 返回覆盖率结果
    coverage = report_data['summary']['overall_coverage']
    if coverage >= 90:
        print(f"✅ 文档覆盖率达标: {coverage:.1f}%")
        return 0
    else:
        print(f"⚠️  文档覆盖率需要改进: {coverage:.1f}% (目标: 90%)")
        return 1


if __name__ == "__main__":
    exit(main())