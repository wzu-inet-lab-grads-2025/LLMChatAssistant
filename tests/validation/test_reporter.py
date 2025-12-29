"""
测试报告生成器

生成符合contracts/test-report-schema.md规范的Markdown测试报告。
"""

import json
from datetime import datetime
from pathlib import Path


class TestReporter:
    """
    测试报告生成器

    根据测试用例和测试结果生成符合规范的Markdown测试报告。
    """

    def __init__(self, test_case, test_result, report_path):
        """
        初始化报告生成器

        Args:
            test_case: 测试用例 (TestCase)
            test_result: 测试结果 (TestResult)
            report_path: 报告文件路径
        """
        self.test_case = test_case
        self.test_result = test_result
        self.report_path = report_path
        self.generated_at = datetime.now().isoformat()

    def generate_markdown(self) -> str:
        """
        生成Markdown格式的报告

        Returns:
            Markdown格式的报告文本
        """
        lines = []

        # 标题
        lines.append(f"# 测试报告 {self.test_case.id}: {self.test_case.name}\n")

        # 测试信息
        lines.append("## 测试信息")
        lines.append(f"- 测试编号: {self.test_case.id}")
        lines.append(f"- 测试名称: {self.test_case.name}")
        lines.append(f"- 优先级: {self.test_case.priority}")
        lines.append(f"- 执行时间: {self.test_result.timestamp}")
        status_icon = "✅ 通过" if self.test_result.status == "passed" else "❌ 失败"
        lines.append(f"- 状态: {status_icon}\n")

        # 测试输入
        lines.append("## 测试输入")
        lines.append("### 用户消息")
        lines.append(f"```\n{self.test_result.user_input}\n```\n")

        # 工具链调用详情
        lines.append("## 工具链调用详情")
        if self.test_result.tool_calls:
            for idx, tool_call in enumerate(self.test_result.tool_calls, 1):
                lines.append(self._format_tool_call(tool_call, idx))
        else:
            lines.append("本次测试未调用任何工具。\n")

        # 最终结果
        lines.append("## 最终结果")
        lines.append("### Agent回复")
        lines.append(f"```\n{self.test_result.agent_response}\n```\n")

        # 性能指标
        lines.append(self._format_performance_metrics())

        # 验收结果
        lines.append(self._format_validation_results())

        # 测试结论
        lines.append("## 测试结论")
        lines.append(self._generate_conclusion())

        return "\n".join(lines)

    def _format_tool_call(self, tool_call, index: int) -> str:
        """
        格式化工具调用详情

        Args:
            tool_call: ToolCall对象
            index: 工具调用序号

        Returns:
            格式化的工具调用字符串
        """
        status_icon_map = {
            "success": "✅",
            "failed": "❌",
            "timeout": "⏱️"
        }
        status_icon = status_icon_map.get(tool_call.status, "❓")

        lines = []
        lines.append(f"### 工具调用 {index}")
        lines.append(f"- **工具名称**: {tool_call.tool_name}")
        lines.append(f"- **调用时间**: {tool_call.timestamp}")
        lines.append(f"- **参数**:")
        lines.append(f"  ```json")
        try:
            params = json.dumps(tool_call.arguments, ensure_ascii=False, indent=2)
        except:
            params = str(tool_call.arguments)
        lines.append(f"  {params}")
        lines.append(f"  ```")
        lines.append(f"- **执行时间**: {tool_call.duration:.2f}s")
        lines.append(f"- **状态**: {status_icon} {tool_call.status}")
        lines.append(f"- **结果**:")
        lines.append(f"  ```")

        # 截断过长的结果（最多200字符）
        result = tool_call.result
        if len(result) > 200:
            result = result[:200] + "\n  ..."
        lines.append(f"  {result}")
        lines.append(f"  ```\n")

        return "\n".join(lines)

    def _format_performance_metrics(self) -> str:
        """
        格式化性能指标

        Returns:
            格式化的性能指标字符串
        """
        metrics = self.test_result.performance_metrics

        lines = []
        lines.append("## 性能指标")
        lines.append(f"- 总响应时间: {metrics.total_response_time:.2f}s")
        lines.append(f"- 工具调用次数: {metrics.tool_call_count}")
        lines.append(f"- 工具执行总时间: {metrics.tool_execution_total:.2f}s")
        lines.append(f"- 平均工具执行时间: {metrics.average_tool_execution:.2f}s")
        lines.append(f"- LLM调用次数: {metrics.llm_call_count}")
        lines.append(f"- LLM调用总时间: {metrics.llm_total_time:.2f}s")

        # 性能评估（检查成功标准）
        lines.append("\n### 性能评估")

        # SC-002: 工具调用响应时间（从用户输入到工具状态显示）90%的情况下 < 2秒
        # 注意：此标准仅适用于有工具调用的测试
        # 对于纯LLM对话（无工具调用），LLM API响应时间本身就需要1-3秒，2秒标准不适用
        if metrics.tool_call_count > 0:
            # 有工具调用时，应用SC-002标准
            if metrics.total_response_time < 2.0:
                lines.append(f"- ✅ 总响应时间 {metrics.total_response_time:.2f}s < 2.0s（符合SC-002）")
            else:
                lines.append(f"- ❌ 总响应时间 {metrics.total_response_time:.2f}s >= 2.0s（不符合SC-002）")
        else:
            # 无工具调用时（纯LLM对话），使用更宽松的标准
            # 网络环境下LLM API调用通常需要1-4秒，这是正常的
            if metrics.total_response_time < 5.0:
                lines.append(f"- ✅ 总响应时间 {metrics.total_response_time:.2f}s < 5.0s（LLM响应时间正常，本次测试无工具调用）")
            else:
                lines.append(f"- ⚠️  总响应时间 {metrics.total_response_time:.2f}s >= 5.0s（LLM响应较慢，建议检查网络，本次测试无工具调用）")

        if metrics.tool_execution_total < 5.0:
            lines.append(f"- ✅ 工具执行时间 {metrics.tool_execution_total:.2f}s < 5.0s（符合SC-003）")
        else:
            lines.append(f"- ❌ 工具执行时间 {metrics.tool_execution_total:.2f}s >= 5.0s（不符合SC-003）")

        return "\n".join(lines) + "\n"

    def _format_validation_results(self) -> str:
        """
        格式化验收结果

        Returns:
            格式化的验收结果字符串
        """
        lines = []
        lines.append("## 验收结果\n")

        for result in self.test_result.validation_results:
            status_icon = "✅" if result.passed else "❌"
            lines.append(f"### 场景{result.scenario_id}: {result.scenario_description}")
            lines.append(f"- **状态**: {status_icon} {'通过' if result.passed else '失败'}")
            lines.append(f"- **给定**: {result.expected}")
            lines.append(f"- **实际**: {result.actual}")
            if result.notes:
                lines.append(f"- **备注**: {result.notes}")
            lines.append("")

        return "\n".join(lines)

    def _generate_conclusion(self) -> str:
        """
        生成测试结论

        Returns:
            测试结论字符串
        """
        passed_count = sum(1 for r in self.test_result.validation_results if r.passed)
        total_count = len(self.test_result.validation_results)

        lines = []
        lines.append("### 总体评估")

        if self.test_result.status == "passed":
            lines.append("✅ **测试通过**")
        else:
            lines.append("❌ **测试失败**")

        lines.append("")
        lines.append("### 通过原因" if self.test_result.status == "passed" else "### 失败原因")

        # 处理空验证结果的情况
        if total_count > 0:
            pass_rate = passed_count * 100 // total_count
            lines.append(f"1. 验收场景通过率: {passed_count}/{total_count} ({pass_rate}%)")
        else:
            lines.append("1. 无验收场景定义")

        # 根据测试结果添加详细分析
        if self.test_result.error_message:
            lines.append(f"2. 错误信息: {self.test_result.error_message}")
        elif self.test_result.status == "passed":
            lines.append("2. 所有验收场景均通过" if total_count > 0 else "2. 测试执行成功")
            lines.append(f"3. Agent行为符合预期")
            lines.append(f"4. 性能指标符合成功标准")
        else:
            lines.append("2. 部分验收场景未通过" if total_count > 0 else "2. 测试执行失败")
            lines.append("3. 需要调查失败原因并修复")

        return "\n".join(lines)

    def save(self):
        """保存报告到文件"""
        # 确保目录存在
        Path(self.report_path).parent.mkdir(parents=True, exist_ok=True)

        # 写入报告
        Path(self.report_path).write_text(
            self.generate_markdown(),
            encoding='utf-8'
        )
