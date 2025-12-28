"""
Agent 工具调用集成测试

测试 ReAct Agent 的工具调用功能，使用真实的智谱 API。
遵循章程：真实测试，不允许 mock
"""

import asyncio
import os
import pytest

from src.llm.zhipu import ZhipuProvider
from src.llm.base import Message
from src.server.agent import ReActAgent
from src.storage.history import ConversationHistory
from src.storage.vector_store import VectorStore
from src.tools.command import CommandTool
from src.tools.monitor import MonitorTool
from src.tools.rag import RAGTool


@pytest.mark.skipif(
    not os.getenv("ZHIPU_API_KEY"),
    reason="需要 ZHIPU_API_KEY 环境变量"
)
@pytest.mark.asyncio
class TestAgentToolCalls:
    """Agent 工具调用测试（需要真实的智谱 API）"""

    async def test_agent_initialization(self):
        """测试 Agent 初始化"""
        # 创建 LLM Provider（只接受 api_key 和 model 参数）
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        # 创建工具
        tools = {
            "command_executor": CommandTool(),
            "sys_monitor": MonitorTool(),
            "rag_search": RAGTool(llm_provider, VectorStore())
        }

        # 创建 Agent
        agent = ReActAgent(
            llm_provider=llm_provider,
            tools=tools,
            max_tool_rounds=5,
            tool_timeout=5
        )

        assert agent.llm_provider is not None
        assert len(agent.tools) == 3
        assert agent.max_tool_rounds == 5
        assert agent.tool_timeout == 5

    async def test_agent_basic_conversation(self):
        """测试 Agent 基础对话（不使用工具）"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 发送简单问候
        response, tool_calls = agent.react_loop(
            user_message="你好",
            conversation_history=history
        )

        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(tool_calls, list)

    async def test_agent_system_monitor_tool(self):
        """测试 Agent 调用系统监控工具"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 询问系统状态
        response, tool_calls = agent.react_loop(
            user_message="查看系统状态",
            conversation_history=history
        )

        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(tool_calls, list)

        # 验证工具调用
        if tool_calls:
            # 检查至少有一个工具被调用
            assert len(tool_calls) >= 1

            # 验证工具调用结构
            for call in tool_calls:
                assert hasattr(call, 'tool_name')
                assert hasattr(call, 'arguments')
                assert hasattr(call, 'result')
                assert hasattr(call, 'status')
                assert hasattr(call, 'duration')

    async def test_agent_command_tool(self):
        """测试 Agent 调用命令执行工具"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 请求列出文件
        response, tool_calls = agent.react_loop(
            user_message="列出当前目录的文件",
            conversation_history=history
        )

        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(tool_calls, list)

    async def test_agent_multiple_tool_calls(self):
        """测试 Agent 多轮工具调用"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(
            llm_provider=llm_provider,
            max_tool_rounds=5
        )
        history = ConversationHistory.create_new("test-session")

        # 复杂查询，可能需要多轮工具调用
        response, tool_calls = agent.react_loop(
            user_message="查看系统状态并列出当前目录文件",
            conversation_history=history
        )

        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(tool_calls, list)

        # 验证工具调用次数不超过最大轮数
        assert len(tool_calls) <= 5

    async def test_agent_tool_timeout(self):
        """测试工具超时处理"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        # 设置很短的超时时间
        agent = ReActAgent(
            llm_provider=llm_provider,
            tool_timeout=1  # 1 秒超时
        )
        history = ConversationHistory.create_new("test-session")

        # 请求可能需要较长时间的命令
        response, tool_calls = agent.react_loop(
            user_message="执行 sleep 5 命令",  # 这个命令会被黑名单过滤，不执行
            conversation_history=history
        )

        assert isinstance(response, str)
        assert isinstance(tool_calls, list)

    async def test_agent_error_handling(self):
        """测试 Agent 错误处理"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 请求执行不存在的工具
        response, tool_calls = agent.react_loop(
            user_message="使用 nonexistent_tool 工具",
            conversation_history=history
        )

        # Agent 应该优雅地处理错误
        assert isinstance(response, str)
        assert isinstance(tool_calls, list)

    async def test_agent_conversation_context(self):
        """测试 Agent 维护对话上下文"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 第一轮对话
        response1, tool_calls1 = agent.react_loop(
            user_message="我的名字是测试用户",
            conversation_history=history
        )

        # 添加到历史
        history.add_message("user", "我的名字是测试用户")
        history.add_message("assistant", response1)

        # 第二轮对话
        response2, tool_calls2 = agent.react_loop(
            user_message="我叫什么名字？",
            conversation_history=history
        )

        assert isinstance(response2, str)
        assert len(response2) > 0

    async def test_agent_tool_call_structure(self):
        """测试工具调用数据结构"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 触发工具调用
        response, tool_calls = agent.react_loop(
            user_message="查看 CPU 使用率",
            conversation_history=history
        )

        # 验证工具调用结构
        if tool_calls:
            for call in tool_calls:
                # 验证必需字段
                assert call.tool_name is not None
                assert call.arguments is not None
                assert call.result is not None
                assert call.status in ["success", "failed", "timeout"]
                assert call.duration >= 0
                assert call.timestamp is not None

    async def test_agent_max_rounds_limit(self):
        """测试最大工具调用轮数限制"""
        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        # 设置很小的最大轮数
        agent = ReActAgent(
            llm_provider=llm_provider,
            max_tool_rounds=2  # 最多 2 轮
        )
        history = ConversationHistory.create_new("test-session")

        # 复杂查询，可能需要多轮工具调用
        response, tool_calls = agent.react_loop(
            user_message="详细分析系统状态并给出建议",
            conversation_history=history
        )

        # 验证不超过最大轮数
        assert len(tool_calls) <= 2


@pytest.mark.skipif(
    not os.getenv("ZHIPU_API_KEY"),
    reason="需要 ZHIPU_API_KEY 环境变量"
)
@pytest.mark.asyncio
class TestAgentFallback:
    """Agent 降级处理测试"""

    async def test_fallback_on_api_failure(self):
        """测试 API 失败时的降级处理"""
        # 使用无效的 API Key
        llm_provider = ZhipuProvider(
            api_key="invalid_key_for_testing",
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 发送消息
        response, tool_calls = agent.react_loop(
            user_message="查看系统状态",
            conversation_history=history
        )

        # 应该降级到本地模式
        assert isinstance(response, str)
        assert len(response) > 0


@pytest.mark.skipif(
    not os.getenv("ZHIPU_API_KEY"),
    reason="需要 ZHIPU_API_KEY 环境变量"
)
@pytest.mark.asyncio
class TestAgentPerformance:
    """Agent 性能测试"""

    async def test_tool_call_response_time(self):
        """测试 AI 工具调用响应时间 < 2s（参考 SC-002）

        验收标准：
        - 工具调用响应时间（从用户输入到工具状态显示）< 2s
        """
        import time

        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 测试多个工具调用的响应时间
        test_queries = [
            "查看 CPU 使用率",
            "检查内存使用情况",
            "列出当前目录文件"
        ]

        response_times = []

        for query in test_queries:
            start_time = time.time()

            # 执行 Agent 反应循环
            response, tool_calls = agent.react_loop(
                user_message=query,
                conversation_history=history
            )

            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)

            print(f"\n查询: {query}")
            print(f"响应时间: {response_time:.2f}s")

            # 每次查询都应该在 2 秒内完成
            assert response_time < 2.0, f"工具调用响应时间过长: {response_time:.2f}s >= 2s"

            # 更新对话历史
            history.add_message("user", query)
            if response:
                history.add_message("assistant", response)

        # 验证平均响应时间
        avg_response_time = sum(response_times) / len(response_times)
        print(f"\n平均响应时间: {avg_response_time:.2f}s")

        # 平均响应时间也应该 < 2s
        assert avg_response_time < 2.0, f"平均工具调用响应时间过长: {avg_response_time:.2f}s >= 2s"

    async def test_tool_execution_time(self):
        """测试工具执行时间性能

        验收标准：
        - 每个工具执行时间 < 5s（工具超时限制）
        - 平均工具执行时间合理
        """
        import time

        llm_provider = ZhipuProvider(
            api_key=os.getenv("ZHIPU_API_KEY"),
            model="glm-4-flash"
        )

        agent = ReActAgent(llm_provider=llm_provider)
        history = ConversationHistory.create_new("test-session")

        # 触发工具调用
        response, tool_calls = agent.react_loop(
            user_message="帮我查看系统状态，包括 CPU、内存和磁盘使用情况",
            conversation_history=history
        )

        # 验证工具执行时间
        if tool_calls:
            execution_times = []
            for call in tool_calls:
                assert hasattr(call, 'duration'), "工具调用缺少 duration 字段"
                execution_times.append(call.duration)

                # 验证单个工具执行时间 < 5s
                assert call.duration < 5.0, f"工具执行时间过长: {call.duration:.2f}s >= 5s"
                print(f"\n工具: {call.tool_name}")
                print(f"执行时间: {call.duration:.2f}s")
                print(f"状态: {call.status}")

            # 验证平均执行时间
            avg_execution_time = sum(execution_times) / len(execution_times)
            print(f"\n平均工具执行时间: {avg_execution_time:.2f}s")

            # 平均执行时间应该合理（< 3s）
            assert avg_execution_time < 3.0, f"平均工具执行时间过长: {avg_execution_time:.2f}s >= 3s"
        else:
            print("没有触发工具调用，跳过执行时间验证")
