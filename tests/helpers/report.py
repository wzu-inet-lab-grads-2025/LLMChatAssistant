"""
测试报告生成器

用于生成详细的测试报告,包括Markdown和JSON格式。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, output_dir: Path):
        """初始化报告生成器

        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.test_results = []
        self.stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "partial": 0
        }

    def add_test_result(self, result: Dict[str, Any]):
        """添加测试结果

        Args:
            result: 测试结果字典,包含:
                - test_name: 测试名称
                - category: 测试类别
                - input: 测试输入
                - expected: 预期行为
                - actual: 实际行为
                - status: 状态 (passed/failed/partial/skipped)
                - tool_calls: 工具调用记录(如果有)
                - messages: 传递给前端的消息(如果有)
                - history: 历史记录(如果有)
                - issues: 问题列表
                - notes: 备注
        """
        self.test_results.append(result)
        self.stats["total"] += 1
        self.stats[result["status"]] = self.stats.get(result["status"], 0) + 1

    def generate_markdown_report(self) -> str:
        """生成Markdown格式报告

        Returns:
            Markdown报告内容
        """
        lines = []
        lines.append("# 后端功能审阅测试报告")
        lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 执行摘要
        lines.append("## 执行摘要\n")
        lines.append(f"- **总样例数**: {self.stats['total']}")
        lines.append(f"- **通过**: {self.stats.get('passed', 0)} ✓")
        lines.append(f"- **失败**: {self.stats.get('failed', 0)} ✗")
        lines.append(f"- **部分通过**: {self.stats.get('partial', 0)} ⚠")
        lines.append(f"- **跳过**: {self.stats.get('skipped', 0)} ⊘")

        pass_rate = (self.stats.get('passed', 0) / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        lines.append(f"\n**通过率**: {pass_rate:.1f}%\n")

        # 按类别统计
        category_stats = {}
        for result in self.test_results:
            cat = result.get('category', 'Unknown')
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "passed": 0, "failed": 0}
            category_stats[cat]["total"] += 1
            category_stats[cat][result.get("status", "skipped")] = \
                category_stats[cat].get(result.get("status", "skipped"), 0) + 1

        lines.append("## 测试类别统计\n")
        lines.append("| 类别 | 总数 | 通过 | 失败 | 部分通过 | 通过率 |")
        lines.append("|------|------|------|------|----------|--------|")

        for cat, stats in sorted(category_stats.items()):
            cat_pass_rate = (stats.get('passed', 0) / stats['total'] * 100) if stats['total'] > 0 else 0
            lines.append(
                f"| {cat} | {stats['total']} | {stats.get('passed', 0)} | "
                f"{stats.get('failed', 0)} | {stats.get('partial', 0)} | {cat_pass_rate:.1f}% |"
            )

        # 详细测试结果
        lines.append("\n## 详细测试结果\n")

        for i, result in enumerate(self.test_results, 1):
            status_emoji = {
                "passed": "✓ 通过",
                "failed": "✗ 失败",
                "partial": "⚠ 部分通过",
                "skipped": "⊘ 跳过"
            }.get(result.get("status", "skipped"), "? 未知")

            lines.append(f"### 测试样例 {i}: {result.get('test_name', 'Unknown')}\n")
            lines.append(f"**测试类别**: {result.get('category', 'Unknown')}\n")
            lines.append(f"**测试结果**: {status_emoji}\n")

            # 测试输入
            if result.get('input'):
                lines.append("**测试输入**:")
                lines.append("```")
                lines.append(str(result['input']))
                lines.append("```\n")

            # 预期行为
            if result.get('expected'):
                lines.append("**预期行为**:")
                for step in result['expected']:
                    lines.append(f"- {step}")
                lines.append("")

            # 实际行为
            if result.get('actual'):
                lines.append("**实际行为**:")
                lines.append("```")
                lines.append(str(result['actual']))
                lines.append("```\n")

            # 工具调用记录
            if result.get('tool_calls'):
                lines.append("**工具链调用情况**:\n")
                for j, call in enumerate(result['tool_calls'], 1):
                    lines.append(f"**第{j}轮工具调用**:")
                    lines.append(f"- 工具名称: `{call.get('tool_name', 'Unknown')}`")
                    lines.append(f"- 调用参数: `{json.dumps(call.get('args', {}), ensure_ascii=False)}`")
                    lines.append(f"- 执行结果: {call.get('result', '')[:200]}...")
                    lines.append(f"- 执行时长: {call.get('duration', 0):.2f}秒\n")

            # 传递给前端的消息
            if result.get('messages'):
                lines.append("**传递给前端的消息序列**:")
                lines.append("```json")
                lines.append(json.dumps(result['messages'], ensure_ascii=False, indent=2))
                lines.append("```\n")

            # 历史记录
            if result.get('history'):
                lines.append("**历史记录存储**:")
                lines.append("```json")
                lines.append(json.dumps(result['history'], ensure_ascii=False, indent=2))
                lines.append("```\n")

            # 问题和备注
            if result.get('issues'):
                lines.append("**问题**:")
                for issue in result['issues']:
                    lines.append(f"- {issue}")
                lines.append("")

            if result.get('notes'):
                lines.append("**备注**:")
                lines.append(result['notes'])
                lines.append("")

            lines.append("---\n")

        # 问题清单
        failed_tests = [r for r in self.test_results if r.get("status") in ["failed", "partial"]]
        if failed_tests:
            lines.append("## 问题清单\n")

            # 按严重程度分类
            critical = [r for r in failed_tests if any("严重" in i for i in r.get('issues', []))]
            medium = [r for r in failed_tests if any("中等" in i for i in r.get('issues', []))]
            minor = [r for r in failed_tests if any("轻微" in i for i in r.get('issues', []))]

            if critical:
                lines.append("### 严重问题\n")
                for r in critical:
                    lines.append(f"- **{r.get('test_name', 'Unknown')}**: {r.get('issues', [''])[0]}")

            if medium:
                lines.append("\n### 中等问题\n")
                for r in medium:
                    lines.append(f"- **{r.get('test_name', 'Unknown')}**: {r.get('issues', [''])[0]}")

            if minor:
                lines.append("\n### 轻微问题\n")
                for r in minor:
                    lines.append(f"- **{r.get('test_name', 'Unknown')}**: {r.get('issues', [''])[0]}")

        return "\n".join(lines)

    def generate_json_report(self) -> Dict:
        """生成JSON格式报告

        Returns:
            JSON报告字典
        """
        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tests": self.stats["total"]
            },
            "statistics": self.stats,
            "test_results": self.test_results
        }

    def save_reports(self, base_name: str = "test_report"):
        """保存报告到文件

        Args:
            base_name: 报告文件名(不含扩展名)
        """
        # 保存Markdown报告
        md_content = self.generate_markdown_report()
        md_path = self.output_dir / f"{base_name}.md"
        md_path.write_text(md_content, encoding='utf-8')
        print(f"Markdown报告已保存到: {md_path}")

        # 保存JSON报告
        json_data = self.generate_json_report()
        json_path = self.output_dir / f"{base_name}.json"
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"JSON报告已保存到: {json_path}")
