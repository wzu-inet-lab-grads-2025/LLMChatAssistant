"""
ReAct Agent 模块

实现基于 ReAct 循环的智能 Agent，支持工具调用和思考。
遵循章程：真实实现，使用真实智谱 API，不允许虚假实现或占位符
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..llm.base import LLMProvider, Message
from ..storage.history import ConversationHistory, ToolCall
from ..tools.base import Tool, ToolExecutionResult
from ..tools.command import CommandTool
from ..tools.monitor import MonitorTool
from ..tools.rag import RAGTool
from ..utils.path_validator import get_path_validator
from ..utils.config import get_config


@dataclass
class ReActAgent:
    """ReAct Agent - 推理和行动循环"""

    llm_provider: LLMProvider
    tools: Dict[str, Tool] = field(default_factory=dict)
    max_tool_rounds: int = 5
    tool_timeout: int = 5  # 工具执行超时（秒）
    status_callback: callable = None  # 状态更新回调函数
    path_validator: Optional[Any] = None  # 路径验证器

    def __post_init__(self):
        """初始化工具"""
        # 如果没有提供工具，使用默认工具
        if not self.tools:
            from ..storage.vector_store import VectorStore
            from ..storage.index_manager import IndexManager

            # 获取配置
            config = get_config()

            # 初始化路径验证器
            if self.path_validator is None:
                self.path_validator = get_path_validator(config.file_access)

            # 初始化组件
            vector_store = VectorStore()
            index_manager = IndexManager(
                vector_store=vector_store,
                llm_provider=self.llm_provider,
                path_validator=self.path_validator,
                config=config.file_access
            )

            # 创建工具实例（带路径验证器）
            self.tools = {
                "command_executor": CommandTool(
                    path_validator=self.path_validator,
                    max_output_size=config.file_access.max_output_size
                ),
                "sys_monitor": MonitorTool(),
                "rag_search": RAGTool(
                    llm_provider=self.llm_provider,
                    vector_store=vector_store,
                    index_manager=index_manager,
                    path_validator=self.path_validator,
                    auto_index=config.file_access.auto_index
                )
            }

    async def _send_status(self, status_type: str, content: str):
        """发送状态更新

        Args:
            status_type: 状态类型 (thinking, tool_call, generating)
            content: 状态内容
        """
        if self.status_callback:
            import json
            status_msg = json.dumps({
                "type": status_type,
                "content": content
            }, ensure_ascii=False)
            await self.status_callback(status_msg)

    async def think_stream(self, user_message: str, conversation_history: ConversationHistory):
        """思考并生成回复（流式输出）

        Args:
            user_message: 用户消息
            conversation_history: 对话历史

        Yields:
            str: 流式输出的文本片段
        """
        try:
            # 发送状态：正在分析
            await self._send_status("thinking", "正在分析用户意图")

            # 获取上下文
            context = conversation_history.get_context(max_turns=5)

            # 构建消息列表
            messages = []
            for msg in context:
                messages.append(Message(role=msg.role, content=msg.content))

            # 添加当前用户消息
            messages.append(Message(role="user", content=user_message))

            # 发送状态：正在生成
            await self._send_status("generating", "正在生成回复")

            # 调用 LLM 流式输出
            async for chunk in self.llm_provider.chat_stream(
                messages=messages,
                temperature=0.7
            ):
                yield chunk

        except Exception as e:
            # API 调用失败，降级到本地命令执行
            fallback_response = self._fallback_to_local(user_message, str(e))
            yield fallback_response

    async def think(self, user_message: str, conversation_history: ConversationHistory) -> str:
        """思考并生成回复（非流式，保持向后兼容）

        Args:
            user_message: 用户消息
            conversation_history: 对话历史

        Returns:
            AI 回复
        """
        try:
            # 获取上下文
            context = conversation_history.get_context(max_turns=5)

            # 构建消息列表
            messages = []
            for msg in context:
                messages.append(Message(role=msg.role, content=msg.content))

            # 添加当前用户消息
            messages.append(Message(role="user", content=user_message))

            # 调用 LLM
            response = await self.llm_provider.chat(
                messages=messages,
                temperature=0.7
            )

            return response

        except Exception as e:
            # API 调用失败，降级到本地命令执行
            return self._fallback_to_local(user_message, str(e))

    async def react_loop(
        self,
        user_message: str,
        conversation_history: ConversationHistory
    ) -> tuple[str, List[ToolCall]]:
        """ReAct 循环：推理 -> 行动 -> 观察

        Args:
            user_message: 用户消息
            conversation_history: 对话历史

        Returns:
            (最终回复, 工具调用列表)
        """
        tool_calls = []
        current_message = user_message
        round_count = 0

        # 最多进行 5 轮工具调用
        while round_count < self.max_tool_rounds:
            round_count += 1

            try:
                # 思考：调用 LLM 决定是否需要使用工具
                await self._send_status("thinking", f"正在思考 (第 {round_count} 轮)")
                thought = await self._think_and_decide(current_message, conversation_history)

                # 检查是否需要使用工具
                tool_use = self._parse_tool_use(thought)

                if not tool_use:
                    # 不需要工具，返回最终回复
                    await self._send_status("generating", "正在生成最终回复")
                    final_response = await self._generate_final_response(
                        current_message,
                        conversation_history,
                        tool_calls
                    )
                    return final_response, tool_calls

                # 执行工具
                tool_name = tool_use["name"]
                tool_args = tool_use["args"]

                if tool_name not in self.tools:
                    error_msg = f"工具不存在: {tool_name}"
                    current_message = f"工具调用失败：{error_msg}\n请尝试其他方法。"
                    continue

                tool = self.tools[tool_name]

                # 发送状态：正在调用工具
                await self._send_status("tool_call", f"正在调用工具: {tool_name}")

                # 执行工具（带超时控制）
                start_time = time.time()
                result = tool.execute(**tool_args)
                duration = time.time() - start_time

                # 检查超时
                if duration > self.tool_timeout:
                    result = ToolExecutionResult(
                        success=False,
                        output="",
                        error=f"工具执行超时（{duration:.2f}s > {self.tool_timeout}s）"
                    )

                # 记录工具调用
                tool_call = ToolCall(
                    tool_name=tool_name,
                    arguments=tool_args,
                    result=result.output if result.success else result.error or "",
                    status="success" if result.success else "failed",
                    duration=duration,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
                tool_calls.append(tool_call)

                # 更新当前消息（包含工具结果）
                if result.success:
                    current_message = f"工具 {tool_name} 执行成功，结果：\n{result.output}\n\n请基于此结果回答用户的问题：{user_message}"
                else:
                    current_message = f"工具 {tool_name} 执行失败：{result.error}\n\n请尝试其他方法回答：{user_message}"

            except Exception as e:
                # API 调用失败，降级到本地命令执行
                fallback_response = self._fallback_to_local(user_message, str(e))
                return fallback_response, tool_calls

        # 达到最大轮数，生成最终回复
        await self._send_status("generating", "正在生成最终回复")
        final_response = await self._generate_final_response(
            current_message,
            conversation_history,
            tool_calls
        )
        return final_response, tool_calls

    async def _think_and_decide(self, message: str, conversation_history: ConversationHistory) -> str:
        """思考并决定是否使用工具

        Args:
            message: 消息
            conversation_history: 对话历史

        Returns:
            思考结果（可能包含工具调用）
        """
        # 构建系统提示 - 使用高级提示词工程技术 v2
        system_prompt = """你是一个智能运维助手。你的职责是分析用户需求，并使用合适的工具完成任务。

## 核心原则

1. 优先使用sys_monitor进行系统资源查询（CPU、内存、磁盘使用率）
2. 仅当用户明确使用命令名（如"ls"、"cat"、"free -h"）时才使用command_executor
3. 抽象的系统状态查询统一使用sys_monitor，具体命令执行使用command_executor

## 决策流程

**步骤1: 识别查询类型**
- 系统资源查询（CPU/内存/磁盘使用率、系统状态）→ sys_monitor（优先）
- 具体命令名执行（ls/cat/grep/head/tail/ps/pwd/whoami/df/free）→ command_executor
- 文档/代码搜索（搜索文档、查找说明、检索信息）→ rag_search
- 问候/闲聊 → 直接回答

**步骤2: 匹配命令到工具**
如果是command_executor，严格按用户意图选择命令：
- 列出/查看文件/目录 → ls
- 查看/显示文件内容 → cat
- 搜索/查找包含...的... → grep
- 查看文件开头/前N行 → head
- 查看文件结尾/最后N行 → tail
- 查看/显示进程 → ps
- 显示/当前目录 → pwd
- 显示当前用户/我是谁 → whoami

**步骤3: 构建工具调用**
严格按照两行格式输出，不要添加任何解释。

## 工具使用示例

### command_executor 示例

用户: ls -la
TOOL: command_executor
ARGS: {"command": "ls", "args": ["-la"]}

用户: 列出文件
TOOL: command_executor
ARGS: {"command": "ls", "args": ["-la"]}

用户: cat config.yaml
TOOL: command_executor
ARGS: {"command": "cat", "args": ["config.yaml"]}

用户: 查看配置文件
TOOL: command_executor
ARGS: {"command": "cat", "args": ["config.yaml"]}

用户: grep error log
TOOL: command_executor
ARGS: {"command": "grep", "args": ["error", "log"]}

用户: 搜索错误日志
TOOL: command_executor
ARGS: {"command": "grep", "args": ["error", "log"]}

用户: ps aux
TOOL: command_executor
ARGS: {"command": "ps", "args": ["aux"]}

用户: 查看进程
TOOL: command_executor
ARGS: {"command": "ps", "args": ["aux"]}

用户: pwd
TOOL: command_executor
ARGS: {"command": "pwd"}

用户: df -h
TOOL: command_executor
ARGS: {"command": "df", "args": ["-h"]}

### sys_monitor 示例（系统资源查询，优先使用）

用户: CPU使用情况
TOOL: sys_monitor
ARGS: {"metric": "cpu"}

用户: 内存使用情况
TOOL: sys_monitor
ARGS: {"metric": "memory"}

用户: 磁盘使用情况
TOOL: sys_monitor
ARGS: {"metric": "disk"}

用户: 系统监控
TOOL: sys_monitor
ARGS: {"metric": "all"}

### rag_search 示例

用户: 搜索文档中关于配置的说明
TOOL: rag_search
ARGS: {"query": "配置说明"}

用户: 查找关于日志的文档
TOOL: rag_search
ARGS: {"query": "日志"}

## 负例（不需要工具）

用户: 你好 → 你好！我是运维助手，有什么可以帮你的吗？
用户: 谢谢 → 不客气！
用户: 你能做什么 → 我可以帮你执行系统命令、监控系统资源、搜索文档等。

## 输出格式要求

1. 需要工具时，严格输出两行：
   TOOL: tool_name
   ARGS: {"key": "value"}

2. 不需要工具时，直接用自然语言回答

3. 禁止输出：
   - "让我思考一下"
   - "我需要使用XX工具"
   - 任何除工具调用或答案之外的内容

现在，根据用户消息执行决策流程，直接输出结果。
"""

        # 获取上下文
        context = conversation_history.get_context(max_turns=3)

        # 构建消息列表
        messages = [Message(role="system", content=system_prompt)]
        for msg in context:
            messages.append(Message(role=msg.role, content=msg.content))
        messages.append(Message(role="user", content=message))

        # 调用 LLM
        response = await self.llm_provider.chat(
            messages=messages,
            temperature=0.7
        )

        return response

    def _parse_tool_use(self, thought: str) -> Dict[str, Any] | None:
        """解析思考结果，提取工具调用

        Args:
            thought: 思考结果

        Returns:
            工具调用信息或 None
        """
        # 匹配 TOOL: tool_name
        tool_match = re.search(r'TOOL:\s*(\w+)', thought, re.IGNORECASE)
        if not tool_match:
            return None

        tool_name = tool_match.group(1)

        # 匹配 ARGS: {...}
        args_match = re.search(r'ARGS:\s*(\{.*?\})', thought, re.DOTALL | re.IGNORECASE)
        if not args_match:
            return {"name": tool_name, "args": {}}

        try:
            args = json.loads(args_match.group(1))
            return {"name": tool_name, "args": args}
        except json.JSONDecodeError:
            return {"name": tool_name, "args": {}}

    async def _generate_final_response(
        self,
        message: str,
        conversation_history: ConversationHistory,
        tool_calls: List[ToolCall]
    ) -> str:
        """生成最终回复

        Args:
            message: 消息
            conversation_history: 对话历史
            tool_calls: 工具调用列表

        Returns:
            最终回复
        """
        # 构建提示
        prompt = f"""基于以下工具调用结果，回答用户的问题：

用户问题：{message}

工具调用结果：
"""

        for i, call in enumerate(tool_calls, 1):
            status = "成功" if call.status == "success" else "失败"
            prompt += f"\n{i}. {call.tool_name} ({status})\n"
            prompt += f"   参数: {json.dumps(call.arguments, ensure_ascii=False)}\n"
            prompt += f"   结果: {call.result}\n"

        prompt += "\n请给出清晰、准确的回答。"

        # 调用 LLM
        try:
            response = await self.llm_provider.chat(
                messages=[Message(role="user", content=prompt)],
                temperature=0.7
            )
            return response
        except Exception as e:
            # 如果 LLM 调用失败，返回工具结果摘要
            return self._summarize_tool_results(tool_calls)

    def _summarize_tool_results(self, tool_calls: List[ToolCall]) -> str:
        """汇总工具结果（降级方案）

        Args:
            tool_calls: 工具调用列表

        Returns:
            结果摘要
        """
        if not tool_calls:
            return "抱歉，我遇到了一些技术问题，无法正常处理您的请求。"

        summary = f"执行了 {len(tool_calls)} 个工具调用：\n\n"

        for i, call in enumerate(tool_calls, 1):
            status = "✓" if call.status == "success" else "✗"
            summary += f"{status}. {call.tool_name}\n"
            summary += f"   {call.result}\n\n"

        return summary

    def _fallback_to_local(self, user_message: str, error: str) -> str:
        """降级到本地命令执行

        当智谱 API 调用失败时，尝试使用本地工具回答简单问题。

        Args:
            user_message: 用户消息
            error: 错误信息

        Returns:
            降级后的回复
        """
        # 尝试识别用户意图并使用本地工具
        lower_message = user_message.lower()

        # 系统监控相关
        if any(keyword in lower_message for keyword in ['内存', 'memory', 'cpu', '磁盘', 'disk']):
            try:
                monitor = self.tools.get("sys_monitor")
                if monitor:
                    result = monitor.execute(metric="all")
                    if result.success:
                        return f"[本地模式] {result.output}"
            except Exception:
                pass

        # 命令执行相关
        if any(keyword in lower_message for keyword in ['列出', 'ls', '文件', 'file']):
            try:
                command = self.tools.get("command_executor")
                if command:
                    result = command.execute(command="ls", args=["-la"])
                    if result.success:
                        return f"[本地模式] 当前目录文件列表：\n{result.output}"
            except Exception:
                pass

        # 无法处理，返回错误提示
        return f"""抱歉，AI 服务暂时不可用（{error}）。

当前已降级到本地模式，仅支持有限的系统监控和命令执行功能。

建议：
1. 检查智谱 API Key 配置
2. 检查网络连接
3. 查看日志了解详细错误信息

您可以尝试询问：
- "系统状态如何？"（系统监控）
- "列出当前目录文件"（命令执行）
"""
