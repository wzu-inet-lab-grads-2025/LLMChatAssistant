"""
测试框架基础类

定义测试数据模型和核心类。
"""

import time
import logging
from dataclasses import dataclass
from typing import List, Callable, Any
from datetime import datetime
from pathlib import Path

@dataclass
class AcceptanceScenario:
    """验收场景"""
    given: str  # 初始状态
    when: str   # 操作
    then: str   # 预期结果
    passed: bool = False  # 是否通过

@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    priority: str
    description: str
    user_story: str
    acceptance_scenarios: List[AcceptanceScenario]
    test_type: str = "integration"

@dataclass
class PerformanceMetrics:
    """
    性能指标

    记录测试执行过程中的性能数据，用于验证性能相关的成功标准。
    """
    total_response_time: float  # 总响应时间（秒），从用户输入到Agent回复
    tool_call_count: int  # 工具调用次数
    tool_execution_times: List[float]  # 每个工具的执行时间（秒）
    tool_execution_total: float  # 工具执行总时间（秒）
    average_tool_execution: float  # 平均工具执行时间（秒）
    llm_call_count: int  # LLM调用次数
    llm_total_time: float  # LLM调用总时间（秒）

    def __post_init__(self):
        """初始化后自动计算平均工具执行时间"""
        if self.tool_call_count > 0 and self.tool_execution_total > 0:
            self.average_tool_execution = self.tool_execution_total / self.tool_call_count
        else:
            self.average_tool_execution = 0.0

    def calculate_average(self):
        """
        计算平均工具执行时间

        如果工具调用次数大于0，则计算平均执行时间；
        否则设置为0.0。
        """
        if self.tool_call_count > 0:
            self.average_tool_execution = self.tool_execution_total / self.tool_call_count
        else:
            self.average_tool_execution = 0.0

@dataclass
class ValidationResult:
    """验证结果"""
    scenario_id: int
    scenario_description: str
    expected: str
    actual: str
    passed: bool
    notes: str = ""

@dataclass
class TestResult:
    """测试结果"""
    test_case_id: str
    status: str
    timestamp: str
    user_input: str
    agent_response: str
    tool_calls: List  # ToolCall对象列表
    performance_metrics: PerformanceMetrics
    validation_results: List[ValidationResult]
    error_message: str = ""

@dataclass
class TestSuite:
    """测试套件"""
    name: str
    test_cases: List[TestCase]
    results: List[TestResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

    def get_by_priority(self, priority: str) -> List[TestCase]:
        """按优先级获取测试"""
        return [tc for tc in self.test_cases if tc.priority == priority]

    def get_by_id(self, test_id: str) -> TestCase:
        """按ID获取测试"""
        for tc in self.test_cases:
            if tc.id == test_id:
                return tc
        raise ValueError(f"测试用例不存在: {test_id}")

    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)


# ============================================================================
# 性能指标收集辅助函数
# ============================================================================

class MetricCollector:
    """
    性能指标收集器

    使用高精度计时器记录测试执行过程中的各项时间指标。
    """

    def __init__(self):
        """初始化指标收集器"""
        self.start_time = None
        self.end_time = None
        self.tool_calls_start = None
        self.llm_calls_start = None

    def start_total_timer(self):
        """开始总响应时间计时"""
        self.start_time = time.perf_counter()

    def end_total_timer(self) -> float:
        """
        结束总响应时间计时

        Returns:
            总响应时间（秒）
        """
        if self.start_time is None:
            return 0.0
        self.end_time = time.perf_counter()
        return self.end_time - self.start_time

    @staticmethod
    def measure_execution_time(func: Callable, *args, **kwargs) -> tuple[Any, float]:
        """
        测量函数执行时间

        Args:
            func: 要测量的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            (函数返回值, 执行时间秒数)
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return result, elapsed


# ============================================================================
# 测试执行辅助类
# ============================================================================

class TestRunner:
    """
    测试执行器

    集成测试执行、指标收集和报告生成的功能。
    """

    def __init__(self, logger: logging.Logger = None):
        """
        初始化测试执行器

        Args:
            logger: 日志记录器，如果不提供则创建新的
        """
        self.logger = logger or logging.getLogger(__name__)
        self.metric_collector = MetricCollector()

    async def run_test(
        self,
        test_case: TestCase,
        agent,
        user_message: str,
        conversation_history=None,
        report_path: str = None
    ) -> TestResult:
        """
        运行单个测试用例

        Args:
            test_case: 测试用例
            agent: Agent实例
            user_message: 用户输入消息
            conversation_history: 对话历史（可选）
            report_path: 报告保存路径（可选）

        Returns:
            测试结果对象
        """
        self.logger.info(f"开始执行测试: {test_case.id} - {test_case.name}")

        # 开始性能指标收集
        self.metric_collector.start_total_timer()

        try:
            # 执行Agent的react_loop
            if conversation_history is None:
                # 如果没有提供历史，创建新的
                from src.storage.history import ConversationHistory
                from uuid import uuid4
                session_id = f"test-{uuid4()}"
                conversation_history = ConversationHistory.create_new(session_id)

            # 调用Agent
            response, tool_calls = await agent.react_loop(
                user_message=user_message,
                conversation_history=conversation_history
            )

            # 结束计时
            total_time = self.metric_collector.end_total_timer()

            # 收集性能指标
            metrics = self._collect_performance_metrics(
                total_time, tool_calls
            )

            # 创建测试结果
            result = TestResult(
                test_case_id=test_case.id,
                status="passed",  # 默认通过，后续验证会更新
                timestamp=datetime.now().isoformat(),
                user_input=user_message,
                agent_response=response,
                tool_calls=tool_calls,
                performance_metrics=metrics,
                validation_results=[],
                error_message=""
            )

            self.logger.info(f"测试执行完成: {test_case.id}, 总耗时: {total_time:.2f}s")

            return result

        except Exception as e:
            # 测试执行失败
            total_time = self.metric_collector.end_total_timer()
            self.logger.error(f"测试执行失败: {test_case.id}, 错误: {str(e)}")

            # 创建失败的结果对象
            return TestResult(
                test_case_id=test_case.id,
                status="failed",
                timestamp=datetime.now().isoformat(),
                user_input=user_message,
                agent_response="",
                tool_calls=[],
                performance_metrics=PerformanceMetrics(
                    total_response_time=total_time,
                    tool_call_count=0,
                    tool_execution_times=[],
                    tool_execution_total=0.0,
                    average_tool_execution=0.0,
                    llm_call_count=0,
                    llm_total_time=0.0
                ),
                validation_results=[],
                error_message=str(e)
            )

    def _collect_performance_metrics(
        self,
        total_time: float,
        tool_calls: List
    ) -> PerformanceMetrics:
        """
        从工具调用列表中收集性能指标

        Args:
            total_time: 总响应时间
            tool_calls: 工具调用列表

        Returns:
            性能指标对象
        """
        # 提取工具执行时间
        tool_execution_times = [call.duration for call in tool_calls]
        tool_execution_total = sum(tool_execution_times) if tool_execution_times else 0.0

        # 创建性能指标对象（会自动计算平均值）
        metrics = PerformanceMetrics(
            total_response_time=total_time,
            tool_call_count=len(tool_calls),
            tool_execution_times=tool_execution_times,
            tool_execution_total=tool_execution_total,
            average_tool_execution=0.0,  # __post_init__会自动计算
            llm_call_count=0,  # Agent未单独记录LLM调用次数
            llm_total_time=0.0  # Agent未单独记录LLM调用时间
        )

        return metrics

    async def validate_results(
        self,
        test_case: TestCase,
        result: TestResult
    ) -> List[ValidationResult]:
        """
        验证测试结果

        Args:
            test_case: 测试用例
            result: 测试结果

        Returns:
            验证结果列表
        """
        validation_results = []

        for idx, scenario in enumerate(test_case.acceptance_scenarios, 1):
            # 检查场景是否通过
            # 这里使用简单的验证逻辑，具体测试可以覆盖
            passed = result.status == "passed"

            validation_result = ValidationResult(
                scenario_id=idx,
                scenario_description=scenario.then,
                expected=scenario.then,
                actual=result.agent_response if result.agent_response else result.error_message,
                passed=passed,
                notes=f"场景验证通过" if passed else "场景验证失败"
            )

            validation_results.append(validation_result)

        return validation_results

    def generate_report(
        self,
        test_case: TestCase,
        result: TestResult,
        report_path: str
    ):
        """
        生成并保存测试报告

        Args:
            test_case: 测试用例
            result: 测试结果
            report_path: 报告保存路径
        """
        from tests.validation.test_reporter import TestReporter

        reporter = TestReporter(test_case, result, report_path)
        reporter.save()

        self.logger.info(f"测试报告已生成: {report_path}")

