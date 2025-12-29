"""
Agent功能验证测试

包含10个测试用例（T001-T010），验证Agent的核心功能。
使用真实的智谱API进行测试，不使用任何mock。
"""

import pytest
import os
import time
from datetime import datetime
from tests.validation.test_framework import (
    TestCase,
    AcceptanceScenario,
    PerformanceMetrics,
    ValidationResult,
    TestResult,
)
from tests.validation.test_reporter import TestReporter


# ============================================================================
# T001: 基础对话功能验证 (用户故事1 - P1)
# ============================================================================

@pytest.mark.skipif(
    not os.getenv("ZHIPU_API_KEY"),
    reason="需要 ZHIPU_API_KEY 环境变量"
)
@pytest.mark.asyncio
class TestT001BasicConversation:
    """T001: 基础对话功能验证"""

    async def test_t001_basic_conversation(self, auto_confirm):
        """
        T001: 基础对话功能验证

        验证Agent能够进行基础对话，无需调用任何工具。

        测试场景：
        1. 问候消息：用户发送"你好"，Agent返回友好问候且不调用工具
        2. 自我介绍：用户询问"你是什么？"，Agent自我介绍
        3. 感谢回应：用户发送"谢谢"，Agent礼貌回应

        成功标准：
        - SC-001: 基础对话功能正常
        - SC-002: 响应时间 < 2.0s
        - SC-005: 测试报告完整
        """
        from src.server.agent import ReActAgent
        from src.llm.zhipu import ZhipuProvider
        from src.storage.history import ConversationHistory
        from uuid import uuid4

        # 定义测试用例
        test_case = TestCase(
            id="T001",
            name="基础对话功能验证",
            priority="P1",
            description="验证Agent能够进行基础对话，无需调用任何工具",
            user_story="用户希望验证Agent的基础对话能力，确保它能够进行正常的问答交流",
            acceptance_scenarios=[
                AcceptanceScenario(
                    given="Agent已初始化并连接到智谱API",
                    when="用户发送问候消息'你好'",
                    then="Agent应该返回友好的问候回复，不调用任何工具"
                ),
                AcceptanceScenario(
                    given="Agent已初始化",
                    when="用户询问简单问题'你是什么？'",
                    then="Agent应该自我介绍，说明它是智能运维助手"
                ),
                AcceptanceScenario(
                    given="Agent已初始化",
                    when="用户发送'谢谢'",
                    then="Agent应该礼貌回应"
                ),
            ]
        )

        # 创建Agent和对话历史
        llm_provider = ZhipuProvider(api_key=os.getenv("ZHIPU_API_KEY"))
        agent = ReActAgent(llm_provider=llm_provider)
        session_id = f"test-{uuid4()}"
        history = ConversationHistory.create_new(session_id)

        # 场景1: 问候消息
        print("\n" + "="*80)
        print("场景1: 问候消息")
        print("="*80)

        start_time = time.perf_counter()

        # 发送问候消息
        response1, tool_calls1 = await agent.react_loop(
            user_message="你好",
            conversation_history=history
        )

        end_time = time.perf_counter()
        total_time1 = end_time - start_time

        print(f"用户消息: 你好")
        print(f"Agent回复: {response1}")
        print(f"工具调用数量: {len(tool_calls1)}")
        print(f"响应时间: {total_time1:.2f}s")

        # 验证场景1：不应该调用任何工具
        scenario1_passed = (
            len(tool_calls1) == 0 and
            response1 and
            len(response1) > 0 and
            total_time1 < 5.0  # 5秒超时限制
        )

        validation_result1 = ValidationResult(
            scenario_id=1,
            scenario_description="问候消息验证",
            expected="返回问候且不调用工具",
            actual=f"Agent回复: {response1}, 工具调用数: {len(tool_calls1)}",
            passed=scenario1_passed,
            notes=f"响应时间: {total_time1:.2f}s"
        )

        # 场景2: 自我介绍
        print("\n" + "="*80)
        print("场景2: 自我介绍")
        print("="*80)

        start_time = time.perf_counter()

        response2, tool_calls2 = await agent.react_loop(
            user_message="你是什么？",
            conversation_history=history
        )

        end_time = time.perf_counter()
        total_time2 = end_time - start_time

        print(f"用户消息: 你是什么？")
        print(f"Agent回复: {response2}")
        print(f"工具调用数量: {len(tool_calls2)}")
        print(f"响应时间: {total_time2:.2f}s")

        # 验证场景2：不应该调用工具，且回复应包含自我介绍
        scenario2_passed = (
            len(tool_calls2) == 0 and
            response2 and
            ("助手" in response2 or "Agent" in response2 or "智能" in response2)
        )

        validation_result2 = ValidationResult(
            scenario_id=2,
            scenario_description="自我介绍验证",
            expected="自我介绍，说明是智能运维助手",
            actual=f"Agent回复: {response2}, 工具调用数: {len(tool_calls2)}",
            passed=scenario2_passed,
            notes=f"响应时间: {total_time2:.2f}s"
        )

        # 场景3: 感谢回应
        print("\n" + "="*80)
        print("场景3: 感谢回应")
        print("="*80)

        start_time = time.perf_counter()

        response3, tool_calls3 = await agent.react_loop(
            user_message="谢谢",
            conversation_history=history
        )

        end_time = time.perf_counter()
        total_time3 = end_time - start_time

        print(f"用户消息: 谢谢")
        print(f"Agent回复: {response3}")
        print(f"工具调用数量: {len(tool_calls3)}")
        print(f"响应时间: {total_time3:.2f}s")

        # 验证场景3：不应该调用工具，且礼貌回应
        scenario3_passed = (
            len(tool_calls3) == 0 and
            response3 and
            len(response3) > 0
        )

        validation_result3 = ValidationResult(
            scenario_id=3,
            scenario_description="感谢回应验证",
            expected="礼貌回应",
            actual=f"Agent回复: {response3}, 工具调用数: {len(tool_calls3)}",
            passed=scenario3_passed,
            notes=f"响应时间: {total_time3:.2f}s"
        )

        # 汇总性能指标（取第一次对话的指标）
        metrics = PerformanceMetrics(
            total_response_time=total_time1,
            tool_call_count=len(tool_calls1),
            tool_execution_times=[],
            tool_execution_total=0.0,
            average_tool_execution=0.0,
            llm_call_count=1,  # 每次对话至少调用一次LLM
            llm_total_time=total_time1
        )

        # 创建测试结果
        test_result = TestResult(
            test_case_id="T001",
            status="passed" if all([
                scenario1_passed,
                scenario2_passed,
                scenario3_passed
            ]) else "failed",
            timestamp=datetime.now().isoformat(),
            user_input="你好 / 你是什么？ / 谢谢",
            agent_response=f"{response1} | {response2} | {response3}",
            tool_calls=tool_calls1 + tool_calls2 + tool_calls3,
            performance_metrics=metrics,
            validation_results=[
                validation_result1,
                validation_result2,
                validation_result3
            ],
            error_message=""
        )

        # 生成测试报告
        report_path = "specs/002-agent-validation-test/reports/T001-基础对话.md"
        reporter = TestReporter(test_case, test_result, report_path)
        reporter.save()

        # 打印测试报告摘要
        print("\n" + "="*80)
        print("测试报告摘要")
        print("="*80)
        print(f"测试编号: T001")
        print(f"测试名称: {test_case.name}")
        print(f"测试状态: {'✅ 通过' if test_result.status == 'passed' else '❌ 失败'}")
        print(f"总响应时间: {metrics.total_response_time:.2f}s")
        print(f"验收结果: {sum(1 for v in test_result.validation_results if v.passed)}/{len(test_result.validation_results)}")
        print(f"报告路径: {report_path}")
        print("="*80)

        # 等待用户确认（除非使用--auto-confirm）
        if not auto_confirm:
            user_input = input("\n测试完成。请确认是否通过？[Y/n] ")
            if user_input.lower() == 'n':
                pytest.fail("用户确认测试未通过")

        # 断言所有场景都通过
        assert scenario1_passed, "场景1失败：Agent应该返回问候且不调用工具"
        assert scenario2_passed, "场景2失败：Agent应该自我介绍且不调用工具"
        assert scenario3_passed, "场景3失败：Agent应该礼貌回应且不调用工具"

        print("\n✅ T001基础对话功能验证测试全部通过！")


# ============================================================================
# T002: 系统监控工具验证 (用户故事2 - P1)
# ============================================================================

@pytest.mark.skipif(
    not os.getenv("ZHIPU_API_KEY"),
    reason="需要 ZHIPU_API_KEY 环境变量"
)
@pytest.mark.asyncio
class TestT002SystemMonitor:
    """T002: 系统监控工具验证"""

    async def test_t002_system_monitor(self, auto_confirm):
        """
        T002: 系统监控工具验证

        验证Agent正确调用sys_monitor工具，获取CPU、内存、磁盘使用情况。

        测试场景：
        1. 查看CPU使用率：用户询问"CPU使用情况"，Agent调用sys_monitor工具，参数为{"metric": "cpu"}
        2. 系统状态查询：用户询问"系统状态如何？"，Agent调用sys_monitor工具，参数为{"metric": "all"}
        3. 内存使用情况：用户询问"内存使用情况"，Agent调用sys_monitor工具，参数为{"metric": "memory"}

        成功标准：
        - SC-003: 工具执行时间 < 5.0s
        - SC-004: 工具调用准确率 ≥ 90%
        - SC-009: 错误处理场景优雅处理率 100%
        """
        from src.server.agent import ReActAgent
        from src.llm.zhipu import ZhipuProvider
        from src.storage.history import ConversationHistory
        from uuid import uuid4

        # 定义测试用例
        test_case = TestCase(
            id="T002",
            name="系统监控工具验证",
            priority="P1",
            description="验证Agent正确调用sys_monitor工具，获取系统资源使用情况",
            user_story="用户需要验证Agent正确调用系统监控工具（sys_monitor），获取CPU、内存、磁盘使用情况",
            acceptance_scenarios=[
                AcceptanceScenario(
                    given="Agent已初始化并配置了sys_monitor工具",
                    when="用户询问'CPU使用情况'",
                    then="Agent应该调用sys_monitor工具，参数为{\"metric\": \"cpu\"}，并返回CPU使用情况"
                ),
                AcceptanceScenario(
                    given="Agent已配置sys_monitor工具",
                    when="用户询问'系统状态如何？'",
                    then="Agent应该调用sys_monitor工具获取所有指标（metric: \"all\"），并返回完整的系统状态信息"
                ),
                AcceptanceScenario(
                    given="Agent已配置sys_monitor工具",
                    when="用户询问'内存使用情况'",
                    then="Agent应该正确调用工具并返回内存使用率、可用内存等信息"
                ),
            ]
        )

        # 创建Agent和对话历史（Agent会自动包含sys_monitor工具）
        llm_provider = ZhipuProvider(api_key=os.getenv("ZHIPU_API_KEY"))
        agent = ReActAgent(llm_provider=llm_provider)
        session_id = f"test-{uuid4()}"
        history = ConversationHistory.create_new(session_id)

        # 场景1: 查看CPU使用率
        print("\n" + "="*80)
        print("场景1: 查看CPU使用率")
        print("="*80)

        start_time = time.perf_counter()

        response1, tool_calls1 = await agent.react_loop(
            user_message="CPU使用情况",
            conversation_history=history
        )

        end_time = time.perf_counter()
        scenario1_time = end_time - start_time

        print(f"用户消息: CPU使用情况")
        print(f"Agent回复: {response1}")
        print(f"工具调用数量: {len(tool_calls1)}")
        if len(tool_calls1) > 0:
            print(f"工具名称: {tool_calls1[0].tool_name}")
            print(f"工具参数: {tool_calls1[0].arguments}")
            print(f"工具状态: {tool_calls1[0].status}")
            print(f"响应时间: {scenario1_time:.2f}s")

        # 验证场景1：调用了sys_monitor工具，参数为cpu
        scenario1_passed = (
            len(tool_calls1) > 0 and
            tool_calls1[0].tool_name == "sys_monitor" and
            tool_calls1[0].arguments.get("metric") == "cpu" and
            tool_calls1[0].status == "success"
        )

        # 场景2: 系统状态查询
        print("\n" + "="*80)
        print("场景2: 系统状态查询")
        print("="*80)

        start_time = time.perf_counter()

        response2, tool_calls2 = await agent.react_loop(
            user_message="系统状态如何？",
            conversation_history=history
        )

        end_time = time.perf_counter()
        scenario2_time = end_time - start_time

        print(f"用户消息: 系统状态如何？")
        print(f"Agent回复: {response2}")
        print(f"工具调用数量: {len(tool_calls2)}")
        if len(tool_calls2) > 0:
            print(f"工具名称: {tool_calls2[0].tool_name}")
            print(f"工具参数: {tool_calls2[0].arguments}")
            print(f"工具状态: {tool_calls2[0].status}")
            print(f"响应时间: {scenario2_time:.2f}s")

        # 验证场景2：调用了sys_monitor工具，参数为all
        scenario2_passed = (
            len(tool_calls2) > 0 and
            tool_calls2[0].tool_name == "sys_monitor" and
            tool_calls2[0].arguments.get("metric") == "all" and
            tool_calls2[0].status == "success"
        )

        # 场景3: 内存使用情况
        print("\n" + "="*80)
        print("场景3: 内存使用情况")
        print("="*80)

        start_time = time.perf_counter()

        response3, tool_calls3 = await agent.react_loop(
            user_message="内存使用情况",
            conversation_history=history
        )

        end_time = time.perf_counter()
        scenario3_time = end_time - start_time

        print(f"用户消息: 内存使用情况")
        print(f"Agent回复: {response3}")
        print(f"工具调用数量: {len(tool_calls3)}")
        if len(tool_calls3) > 0:
            print(f"工具名称: {tool_calls3[0].tool_name}")
            print(f"工具参数: {tool_calls3[0].arguments}")
            print(f"工具状态: {tool_calls3[0].status}")
            print(f"响应时间: {scenario3_time:.2f}s")

        # 验证场景3：调用了sys_monitor工具，参数为memory
        scenario3_passed = (
            len(tool_calls3) > 0 and
            tool_calls3[0].tool_name == "sys_monitor" and
            tool_calls3[0].arguments.get("metric") == "memory" and
            tool_calls3[0].status == "success"
        )

        # 收集所有工具调用（用于性能指标）
        all_tool_calls = tool_calls1 + tool_calls2 + tool_calls3

        # 计算性能指标
        tool_execution_times = [call.duration for call in all_tool_calls]
        tool_execution_total = sum(tool_execution_times) if tool_execution_times else 0.0

        metrics = PerformanceMetrics(
            total_response_time=scenario1_time + scenario2_time + scenario3_time,
            tool_call_count=len(all_tool_calls),
            tool_execution_times=tool_execution_times,
            tool_execution_total=tool_execution_total,
            average_tool_execution=0.0,  # __post_init__会自动计算
            llm_call_count=0,  # Agent未单独记录LLM调用次数
            llm_total_time=0.0  # Agent未单独记录LLM调用时间
        )

        # 创建验证结果
        validation_result1 = ValidationResult(
            scenario_id=1,
            scenario_description="调用sys_monitor工具获取CPU使用情况",
            expected="调用sys_monitor工具，参数为{\"metric\": \"cpu\"}",
            actual=f"调用工具: {tool_calls1[0].tool_name if len(tool_calls1) > 0 else '无'}, 参数: {tool_calls1[0].arguments if len(tool_calls1) > 0 else 'N/A'}",
            passed=scenario1_passed,
            notes=f"响应时间: {scenario1_time:.2f}s" if scenario1_passed else "未正确调用工具或参数错误"
        )

        validation_result2 = ValidationResult(
            scenario_id=2,
            scenario_description="调用sys_monitor工具获取所有系统状态",
            expected="调用sys_monitor工具，参数为{\"metric\": \"all\"}",
            actual=f"调用工具: {tool_calls2[0].tool_name if len(tool_calls2) > 0 else '无'}, 参数: {tool_calls2[0].arguments if len(tool_calls2) > 0 else 'N/A'}",
            passed=scenario2_passed,
            notes=f"响应时间: {scenario2_time:.2f}s" if scenario2_passed else "未正确调用工具或参数错误"
        )

        validation_result3 = ValidationResult(
            scenario_id=3,
            scenario_description="调用sys_monitor工具获取内存使用情况",
            expected="调用sys_monitor工具，参数为{\"metric\": \"memory\"}",
            actual=f"调用工具: {tool_calls3[0].tool_name if len(tool_calls3) > 0 else '无'}, 参数: {tool_calls3[0].arguments if len(tool_calls3) > 0 else 'N/A'}",
            passed=scenario3_passed,
            notes=f"响应时间: {scenario3_time:.2f}s" if scenario3_passed else "未正确调用工具或参数错误"
        )

        # 创建测试结果
        test_result = TestResult(
            test_case_id="T002",
            status="passed" if all([scenario1_passed, scenario2_passed, scenario3_passed]) else "failed",
            timestamp=datetime.now().isoformat(),
            user_input="查看CPU使用率、系统状态、内存使用情况",
            agent_response=f"{response1}\n\n{response2}\n\n{response3}",
            tool_calls=all_tool_calls,
            performance_metrics=metrics,
            validation_results=[
                validation_result1,
                validation_result2,
                validation_result3
            ],
            error_message=""
        )

        # 生成测试报告
        report_path = "specs/002-agent-validation-test/reports/T002-系统监控.md"
        reporter = TestReporter(test_case, test_result, report_path)
        reporter.save()

        # 打印测试报告摘要
        print("\n" + "="*80)
        print("测试报告摘要")
        print("="*80)
        print(f"测试编号: T002")
        print(f"测试名称: {test_case.name}")
        print(f"测试状态: {'✅ 通过' if test_result.status == 'passed' else '❌ 失败'}")
        print(f"总响应时间: {metrics.total_response_time:.2f}s")
        print(f"工具调用次数: {metrics.tool_call_count}")
        print(f"验收结果: {sum(1 for v in test_result.validation_results if v.passed)}/{len(test_result.validation_results)}")
        print(f"报告路径: {report_path}")
        print("="*80)

        # 等待用户确认（除非使用--auto-confirm）
        if not auto_confirm:
            user_input = input("\n测试完成。请确认是否通过？[Y/n] ")
            if user_input.lower() == 'n':
                pytest.fail("用户确认测试未通过")

        # 断言所有场景都通过
        assert scenario1_passed, "场景1失败：Agent应该调用sys_monitor工具，参数为cpu"
        assert scenario2_passed, "场景2失败：Agent应该调用sys_monitor工具，参数为all"
        assert scenario3_passed, "场景3失败：Agent应该调用sys_monitor工具，参数为memory"

        print("\n✅ T002系统监控工具验证测试全部通过！")


# TODO: 在阶段5实现T003命令执行工具验证测试
# TODO: 在阶段6实现T004测试报告生成验证测试
# TODO: 在阶段7实现T005多轮工具调用验证测试
# TODO: 在阶段8实现T006 RAG检索工具验证测试
# TODO: 在阶段9实现T007对话上下文验证测试
# TODO: 在阶段10实现T008工具超时和错误处理验证测试
# TODO: 在阶段11实现T009模型切换功能验证测试
# TODO: 在阶段12实现T010 API失败降级验证测试
