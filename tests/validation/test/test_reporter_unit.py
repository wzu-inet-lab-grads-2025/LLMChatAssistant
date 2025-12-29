"""
TestReporter单元测试

验证测试报告生成器能够生成符合规范的Markdown报告。
"""

import pytest
from datetime import datetime
from tests.validation.test_framework import (
    TestCase,
    AcceptanceScenario,
    TestResult,
    PerformanceMetrics,
    ValidationResult,
)
from tests.validation.test_reporter import TestReporter


@pytest.mark.asyncio
async def test_reporter_generates_valid_markdown():
    """验证TestReporter能够生成有效的Markdown格式"""
    # 创建测试用例
    test_case = TestCase(
        id="T001",
        name="基础对话功能验证",
        priority="P1",
        description="验证Agent的基础对话能力",
        user_story="用户希望验证Agent的基础对话能力",
        acceptance_scenarios=[
            AcceptanceScenario(
                given="Agent已初始化",
                when="用户发送'你好'",
                then="返回问候且不调用工具"
            )
        ]
    )

    # 创建测试结果
    test_result = TestResult(
        test_case_id="T001",
        status="passed",
        timestamp=datetime.now().isoformat(),
        user_input="你好",
        agent_response="你好！我是智能运维助手，有什么可以帮助你的吗？",
        tool_calls=[],
        performance_metrics=PerformanceMetrics(
            total_response_time=1.82,
            tool_call_count=0,
            tool_execution_times=[],
            tool_execution_total=0.0,
            average_tool_execution=0.0,
            llm_call_count=1,
            llm_total_time=1.30
        ),
        validation_results=[
            ValidationResult(
                scenario_id=1,
                scenario_description="返回问候且不调用工具",
                expected="返回问候",
                actual="Agent返回问候，未调用工具",
                passed=True
            )
        ]
    )

    # 创建报告生成器
    reporter = TestReporter(
        test_case=test_case,
        test_result=test_result,
        report_path="specs/002-agent-validation-test/reports/T001-基础对话.md"
    )

    # 生成Markdown
    markdown = reporter.generate_markdown()

    # 验证Markdown包含所有必需章节
    assert "# 测试报告 T001: 基础对话功能验证" in markdown
    assert "## 测试信息" in markdown
    assert "## 测试输入" in markdown
    assert "## 工具链调用详情" in markdown
    assert "## 最终结果" in markdown
    assert "## 性能指标" in markdown
    assert "## 验收结果" in markdown
    assert "## 测试结论" in markdown

    # 验证必需字段存在
    assert "- 测试编号: T001" in markdown
    assert "- 优先级: P1" in markdown
    assert "✅ 通过" in markdown

    print("✅ TestReporter单元测试通过")


@pytest.mark.asyncio
async def test_reporter_saves_file():
    """验证TestReporter能够保存报告到文件"""
    from pathlib import Path
    import tempfile

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "test_report.md"

        # 创建最小测试数据
        test_case = TestCase(
            id="T999",
            name="单元测试",
            priority="P1",
            description="测试报告保存",
            user_story="测试",
            acceptance_scenarios=[]
        )

        test_result = TestResult(
            test_case_id="T999",
            status="passed",
            timestamp=datetime.now().isoformat(),
            user_input="测试",
            agent_response="测试回复",
            tool_calls=[],
            performance_metrics=PerformanceMetrics(
                total_response_time=0.1,
                tool_call_count=0,
                tool_execution_times=[],
                tool_execution_total=0.0,
                average_tool_execution=0.0,
                llm_call_count=0,
                llm_total_time=0.0
            ),
            validation_results=[]
        )

        # 创建报告并保存
        reporter = TestReporter(test_case, test_result, str(report_path))
        reporter.save()

        # 验证文件存在
        assert report_path.exists()

        # 验证文件内容
        content = report_path.read_text(encoding='utf-8')
        assert "# 测试报告 T999: 单元测试" in content

        print("✅ TestReporter保存文件测试通过")
