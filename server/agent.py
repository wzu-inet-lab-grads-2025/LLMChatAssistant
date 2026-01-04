"""
ReAct Agent 模块

实现基于 ReAct 循环的智能 Agent，支持工具调用和思考。
遵循章程：真实实现，使用真实智谱 API，不允许虚假实现或占位符
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from server.llm.base import LLMProvider, Message
from server.storage.history import ConversationHistory, ToolCall
from server.tools.base import Tool, ToolExecutionResult
from server.tools.command import CommandTool
from server.tools.monitor import MonitorTool
from server.tools.semantic_search import SemanticSearchTool
from server.tools.file_upload import FileUploadTool
from server.tools.file_download import FileDownloadTool
from shared.utils.path_validator import get_path_validator
from shared.utils.config import get_config


@dataclass
class ReActAgent:
    """ReAct Agent - 推理和行动循环"""

    llm_provider: LLMProvider
    tools: Dict[str, Tool] = field(default_factory=dict)
    max_tool_rounds: int = 5
    tool_timeout: int = 5  # 工具执行超时（秒）
    status_callback: callable = None  # 状态更新回调函数
    path_validator: Optional[Any] = None  # 路径验证器
    rdt_server: Optional[Any] = None  # RDT服务器实例
    http_base_url: Optional[str] = None  # HTTP下载基础URL

    def __post_init__(self):
        """初始化工具"""
        # 如果没有提供工具，使用默认工具
        if not self.tools:
            from server.storage.vector_store import VectorStore
            from server.storage.index_manager import IndexManager
            from server.rdt_server import RDTServer

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

            # 初始化RDT服务器（混合传输架构 - 方案A）
            if self.rdt_server is None:
                self.rdt_server = RDTServer(
                    host="0.0.0.0",
                    port=9998,
                    window_size=5,
                    timeout=0.1
                )

            # 创建工具实例（带路径验证器）
            # Constitution v1.5.1 - Agent工具清单规范：5个工具
            self.tools = {
                "command_executor": CommandTool(
                    path_validator=self.path_validator,
                    max_output_size=config.file_access.max_output_size
                ),
                "sys_monitor": MonitorTool(),
                # 语义检索工具（合并RAG和file_semantic_search，实施混合检索策略）
                "semantic_search": SemanticSearchTool(
                    llm_provider=self.llm_provider,
                    vector_store=vector_store,
                    index_manager=index_manager,
                    path_validator=self.path_validator,
                    auto_index=config.file_access.auto_index
                ),
                # 文件索引管理工具（重新定义：不处理文件上传，由协议层处理）
                "file_upload": FileUploadTool(),
                # 文件下载准备工具
                "file_download": FileDownloadTool(
                    path_validator=self.path_validator,
                    rdt_server=self.rdt_server,
                    http_base_url=self.http_base_url,
                    client_type="cli"  # 默认CLI客户端
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

    async def think_stream(self, user_message: str, conversation_history: ConversationHistory, session=None):
        """思考并生成回复（真正的流式输出，支持ReAct工具调用）

        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            session: Session对象（用于工具访问uploaded_files等）

        Yields:
            str: 流式输出的文本片段

        实现说明：
        - 简单对话（无需工具）：直接流式生成
        - 复杂任务（需要工具）：先执行工具，再流式生成最终响应
        """
        try:
            # 发送状态：正在分析
            await self._send_status("thinking", "正在分析用户意图")

            # 步骤1：判断是否需要使用工具
            thought = await self._think_and_decide(user_message, conversation_history)

            # 特殊处理：如果是重复请求的响应，直接流式输出
            if thought.startswith("我刚才已经展示过") or "如果您需要重新查看" in thought:
                await self._send_status("generating", "正在生成回复")
                # 直接分块yield响应
                chunk_size = 2
                for i in range(0, len(thought), chunk_size):
                    chunk = thought[i:i + chunk_size]
                    yield chunk
                return

            tool_use = self._parse_tool_use(thought)

            tool_calls = []

            if tool_use:
                # 步骤2a：需要工具，执行ReAct循环
                await self._send_status("thinking", "正在执行工具调用")
                final_response, tool_calls = await self._react_loop_with_tools(
                    user_message,
                    conversation_history,
                    session,
                    tool_use,
                    tool_calls
                )

                # 步骤3a：流式输出最终响应
                await self._send_status("generating", "正在生成回复")
                async for chunk in self._generate_final_response_stream(
                    user_message,
                    conversation_history,
                    tool_calls
                ):
                    yield chunk  # 真正的流式输出

            else:
                # 步骤2b：无需工具，直接流式生成
                await self._send_status("generating", "正在生成回复")

                # 构建消息列表
                context = conversation_history.get_context(max_turns=5)
                messages = []
                for msg in context:
                    messages.append(Message(role=msg.role, content=msg.content))
                messages.append(Message(role="user", content=user_message))

                # 真正的流式输出：直接调用LLM流式API
                async for chunk in self.llm_provider.chat_stream(
                    messages=messages,
                    temperature=0.7
                ):
                    yield chunk  # 立即yield，实现真正的流式

        except Exception as e:
            # API 调用失败，降级到本地命令执行
            import sys
            import traceback
            print(f"[ERROR] think_stream异常: {e}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            fallback_response = self._fallback_to_local(user_message, str(e))
            # 降级响应也分块yield
            chunk_size = 2
            for i in range(0, len(fallback_response), chunk_size):
                chunk = fallback_response[i:i + chunk_size]
                yield chunk

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

    async def _react_loop_with_tools(
        self,
        user_message: str,
        conversation_history: ConversationHistory,
        session,
        initial_tool_use: dict,
        tool_calls: list
    ) -> tuple[str, list]:
        """执行需要工具调用的ReAct循环

        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            session: Session对象
            initial_tool_use: 初始工具调用信息
            tool_calls: 工具调用列表

        Returns:
            (最终回复, 工具调用列表)
        """
        current_message = user_message
        round_count = 0

        # 最多进行 5 轮工具调用
        while round_count < self.max_tool_rounds:
            round_count += 1

            try:
                if round_count > 1:
                    # 重新思考是否需要更多工具
                    await self._send_status("thinking", f"正在思考 (第 {round_count} 轮)")

                    # 调试日志：记录第2轮及后续轮次的上下文
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"[DEBUG] 第{round_count}轮思考: current_message前200字符={repr(current_message[:200])}")

                    thought = await self._think_and_decide(current_message, conversation_history)
                    tool_use = self._parse_tool_use(thought)
                else:
                    tool_use = initial_tool_use

                if not tool_use:
                    # 不需要更多工具，生成最终回复
                    await self._send_status("generating", "正在生成最终回复")
                    full_response = ""
                    async for chunk in self._generate_final_response_stream(
                        current_message,
                        conversation_history,
                        tool_calls
                    ):
                        full_response += chunk

                    # 添加助手回复到历史（带工具调用记录）
                    conversation_history.add_message(
                        role="assistant",
                        content=full_response,
                        tool_calls=tool_calls if tool_calls else None
                    )
                    return full_response, tool_calls

                # 执行工具
                tool_name = tool_use["name"]
                tool_args = tool_use["args"]

                if tool_name not in self.tools:
                    error_msg = f"工具不存在: {tool_name}"
                    current_message = f"工具调用失败：{error_msg}\n请尝试其他方法。"
                    continue

                tool = self.tools[tool_name]

                # 注入 session 到工具（如果工具支持）
                if hasattr(tool, 'session') and session is not None:
                    tool.session = session

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
                    # 关键修改：明确判断任务状态，避免LLM过度调用工具
                    if tool_name == "semantic_search" and tool_calls:
                        # semantic_search成功后，提示LLM继续调用command_executor
                        current_message = f"工具 {tool_name} 执行成功，结果：\n{result.output}\n\n【重要】用户请求：{user_message}\n请判断：如果已找到文件路径，需要继续调用command_executor查看文件内容；如果任务已完成，回答用户问题。"
                    elif tool_name == "command_executor" and tool_args.get("command") in ["cat", "head", "tail"] and result.output:
                        # cat/head/tail成功读取文件后，任务已完成
                        # 截取output的前200字符，避免传递过多内容导致LLM误判
                        output_preview = result.output[:200] + "..." if len(result.output) > 200 else result.output
                        current_message = f"工具 {tool_name} 执行成功，已读取文件内容（共{len(result.output)}字符）。\n\n内容预览：\n{output_preview}\n\n【任务已完成】用户请求：{user_message}\n请根据上述结果直接回答用户问题，不要继续调用工具。"
                    else:
                        # 其他工具成功后，让LLM判断
                        current_message = f"工具 {tool_name} 执行成功，结果：\n{result.output[:500]}\n\n用户请求：{user_message}\n请判断：如果任务已完成，回答用户问题；如果需要更多信息，继续调用工具。"
                else:
                    current_message = f"工具 {tool_name} 执行失败：{result.error}\n\n用户请求：{user_message}\n请尝试其他工具或方法回答。"

            except Exception as e:
                # API 调用失败，降级到本地命令执行
                fallback_response = self._fallback_to_local(user_message, str(e))

                # 添加助手回复到历史
                conversation_history.add_message(
                    role="assistant",
                    content=fallback_response,
                    tool_calls=tool_calls if tool_calls else None
                )
                return fallback_response, tool_calls

        # 达到最大轮数，生成最终回复
        await self._send_status("generating", "正在生成最终回复")
        full_response = ""
        async for chunk in self._generate_final_response_stream(
            current_message,
            conversation_history,
            tool_calls
        ):
            full_response += chunk

        # 添加助手回复到历史（关键修复：确保工具调用的结果也被保存）
        conversation_history.add_message(
            role="assistant",
            content=full_response,
            tool_calls=tool_calls if tool_calls else None
        )

        return full_response, tool_calls

    async def react_loop(
        self,
        user_message: str,
        conversation_history: ConversationHistory,
        session=None
    ) -> tuple[str, List[ToolCall]]:
        """ReAct 循环：推理 -> 行动 -> 观察（用于向后兼容）

        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            session: Session对象（用于工具访问uploaded_files等）

        Returns:
            (最终回复, 工具调用列表)
        """
        # 添加用户消息到历史
        conversation_history.add_message(role="user", content=user_message)

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

                # 调试：记录LLM返回
                with open('/tmp/llm_response_debug.log', 'a') as f:
                    f.write(f"\n=== 第{round_count}轮 LLM返回 ===\n{thought}\n{'='*50}\n")
                    f.flush()

                # 检查是否需要使用工具
                tool_use = self._parse_tool_use(thought)

                if not tool_use:
                    # 不需要工具，返回最终回复（收集完整字符串）
                    await self._send_status("generating", "正在生成最终回复")
                    full_response = ""
                    async for chunk in self._generate_final_response_stream(
                        current_message,
                        conversation_history,
                        tool_calls
                    ):
                        full_response += chunk

                    # 添加助手回复到历史（带工具调用记录）
                    conversation_history.add_message(
                        role="assistant",
                        content=full_response,
                        tool_calls=tool_calls if tool_calls else None
                    )
                    return full_response, tool_calls

                # 执行工具
                tool_name = tool_use["name"]
                tool_args = tool_use["args"]

                if tool_name not in self.tools:
                    error_msg = f"工具不存在: {tool_name}"
                    current_message = f"工具调用失败：{error_msg}\n请尝试其他方法。"
                    continue

                tool = self.tools[tool_name]

                # 注入 session 到工具（如果工具支持）
                if hasattr(tool, 'session') and session is not None:
                    tool.session = session

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
                    # 关键修改：明确判断任务状态，避免LLM过度调用工具
                    if tool_name == "semantic_search" and tool_calls:
                        # semantic_search成功后，提示LLM继续调用command_executor
                        current_message = f"工具 {tool_name} 执行成功，结果：\n{result.output}\n\n【重要】用户请求：{user_message}\n请判断：如果已找到文件路径，需要继续调用command_executor查看文件内容；如果任务已完成，回答用户问题。"
                    elif tool_name == "command_executor" and tool_args.get("command") in ["cat", "head", "tail"] and result.output:
                        # cat/head/tail成功读取文件后，任务已完成
                        # 截取output的前200字符，避免传递过多内容导致LLM误判
                        output_preview = result.output[:200] + "..." if len(result.output) > 200 else result.output
                        current_message = f"工具 {tool_name} 执行成功，已读取文件内容（共{len(result.output)}字符）。\n\n内容预览：\n{output_preview}\n\n【任务已完成】用户请求：{user_message}\n请根据上述结果直接回答用户问题，不要继续调用工具。"
                    else:
                        # 其他工具成功后，让LLM判断
                        current_message = f"工具 {tool_name} 执行成功，结果：\n{result.output[:500]}\n\n用户请求：{user_message}\n请判断：如果任务已完成，回答用户问题；如果需要更多信息，继续调用工具。"
                else:
                    current_message = f"工具 {tool_name} 执行失败：{result.error}\n\n用户请求：{user_message}\n请尝试其他工具或方法回答。"

            except Exception as e:
                # API 调用失败，降级到本地命令执行
                fallback_response = self._fallback_to_local(user_message, str(e))

                # 添加助手回复到历史
                conversation_history.add_message(
                    role="assistant",
                    content=fallback_response,
                    tool_calls=tool_calls if tool_calls else None
                )
                return fallback_response, tool_calls

        # 达到最大轮数，生成最终回复
        await self._send_status("generating", "正在生成最终回复")
        full_response = ""
        async for chunk in self._generate_final_response_stream(
            current_message,
            conversation_history,
            tool_calls
        ):
            full_response += chunk

        # 添加助手回复到历史（关键修复：确保工具调用的结果也被保存）
        conversation_history.add_message(
            role="assistant",
            content=full_response,
            tool_calls=tool_calls if tool_calls else None
        )

        return full_response, tool_calls

    async def _think_and_decide(self, message: str, conversation_history: ConversationHistory) -> str:
        """思考并决定是否使用工具

        Args:
            message: 消息
            conversation_history: 对话历史

        Returns:
            思考结果（可能包含工具调用）
        """
        import logging
        logger = logging.getLogger(__name__)
        # 构建系统提示 - 使用高级提示词工程技术 v2
        system_prompt = """你是一个智能运维助手。你的职责是分析用户需求，并使用合适的工具完成任务。

## 核心原则

1. 优先使用sys_monitor进行系统资源查询（CPU、内存、磁盘使用率）
2. 仅当用户明确使用命令名（如"ls"、"cat"、"free -h"）时才使用command_executor
3. 抽象的系统状态查询统一使用sys_monitor，具体命令执行使用command_executor
4. 文件操作（上传、下载、检索）使用专用文件工具

## 决策流程

**步骤1: 识别查询类型**
- 系统资源查询（CPU/内存/磁盘使用率、系统状态）→ sys_monitor（优先）
- 具体命令名执行（ls/cat/grep/head/tail/ps/pwd/whoami/df/free）→ command_executor
- 文件/文档检索（搜索、找、查找、检索、定位、XX文件在哪里、XX文件位于、查看XX文件）→ semantic_search定位 → command_executor读取完整内容
- 文件索引管理（查看上传的文件、引用文件）→ file_upload
- 文件下载（下载文件、发给我、把XX文件发给我）→ file_download（先用semantic_search定位，再用file_download准备下载）
- 命令询问（有什么用、是什么、怎么使用、介绍一下、请解释、说明一下）→ 直接回答，不调用工具
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

### command_executor 示例（仅用于已知路径的系统命令）

**重要：文件查看必须先使用 semantic_search 定位完整路径，然后才能用 command_executor！**

用户: ls -la
TOOL: command_executor
ARGS: {"command": "ls", "args": ["-la"]}

用户: 列出当前目录文件
TOOL: command_executor
ARGS: {"command": "ls", "args": ["-la"]}

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

### semantic_search 示例（混合检索策略）

**关键：所有文件查看必须分两步执行 - semantic_search定位 → command_executor读取**

用户: 查看config.yaml
TOOL: semantic_search
ARGS: {"query": "config.yaml", "top_k": 1}
# 第1步：精确文件名匹配，找到完整路径
TOOL: command_executor
ARGS: {"command": "cat", "args": ["storage/uploads/da468689-4b29-434d-b618-c3f58d85f9a8/config.yaml"]}
# 第2步：使用完整路径读取文件内容

用户: 查看配置文件
TOOL: semantic_search
ARGS: {"query": "config.yaml", "top_k": 3}
# 第1步：搜索配置文件，获取完整路径
TOOL: command_executor
ARGS: {"command": "cat", "args": ["storage/uploads/da468689-4b29-434d-b618-c3f58d85f9a8/config.yaml"]}
# 第2步：读取文件内容

用户: 查看README
TOOL: semantic_search
ARGS: {"query": "README", "top_k": 1}
TOOL: command_executor
ARGS: {"command": "cat", "args": ["storage/uploads/xxx/README.md"]}

用户: 找一下日志文件
TOOL: semantic_search
ARGS: {"query": "log", "top_k": 5}
# 模糊匹配 → 返回所有包含"log"的文件（.log文件）
TOOL: command_executor
ARGS: {"command": "cat", "args": ["storage/uploads/xxx/server.log"]}

用户: 搜索数据库配置
TOOL: semantic_search
ARGS: {"query": "数据库配置", "top_k": 3}
TOOL: command_executor
ARGS: {"command": "cat", "args": ["storage/uploads/xxx/database.yaml"]}

**semantic_search + command_executor 工具链原则**：
- 所有文件查看请求都必须使用两步工具链
- 第1步：semantic_search 定位文件，获取完整路径（从结果中提取路径字段）
- 第2步：command_executor 使用完整路径读取文件内容
- 不能跳过第1步直接用 cat，因为文件路径可能不在当前目录

### 文件操作示例

# 文件索引管理
用户: 查看上传的文件
TOOL: file_upload
ARGS: {"action": "list", "reference": "all"}

# 文件下载（先搜索再下载）
用户: 把配置文件发给我
TOOL: semantic_search
ARGS: {"query": "config.yaml", "top_k": 1}
# 第1步：找到文件
TOOL: file_download
ARGS: {"file_path": "storage/uploads/da468689-4b29-434d-b618-c3f58d85f9a8/config.yaml"}
# 第2步：准备下载

## 负例（不需要工具）

### 问候/闲聊
用户: 你好 → 你好！我是运维助手，有什么可以帮你的吗？
用户: 谢谢 → 不客气！
用户: 你能做什么 → 我可以帮你执行系统命令、监控系统资源、搜索文档等。

### 命令询问（重要：这些不是执行命令，是知识问答）
用户: ls命令有什么用 → ls命令用于列出目录内容。它会显示指定目录下的文件和子目录列表。
用户: 介绍一下df指令 → df是disk free的缩写，用于显示文件系统的磁盘空间使用情况。
用户: grep怎么使用 → grep是一个强大的文本搜索工具，用于在文件中查找匹配指定模式的文本行。
用户: 请解释一下ps aux的含义 → ps命令用于显示当前运行的进程，aux参数表示显示所有用户的进程详细信息。
用户: cat和more的区别是什么 → cat一次性显示整个文件内容，而more分页显示，可以逐页浏览大文件。
用户: man命令是做什么的 → man是manual的缩写，用于显示Linux系统手册页，提供命令的详细说明。

**重要识别规则**：
- 如果用户问"有什么用"、"是什么"、"怎么使用"、"介绍一下"、"请解释"、"说明一下"、"告诉我关于"、"区别是什么" → 这是知识询问，**不调用任何工具**，直接用自然语言回答
- 如果用户说"查看"、"显示"、"列出"、"执行"、"运行" → 这是操作指令，**调用相应工具**

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

        # 获取上下文（不包括当前消息，避免重复）
        # get_context 返回最近的消息，可能包含当前消息，所以需要排除
        context = conversation_history.get_context(max_turns=3)
        # 检查 context 的最后一条消息是否是当前消息，如果是则排除
        if context and context[-1].role == "user" and context[-1].content == message:
            context = context[:-1]  # 排除最后一条（当前消息）

        # 关键优化：检测重复查看同一文件的请求
        # 如果最近的助手消息包含成功的文件读取操作，且当前请求是重复的，直接返回提示
        if len(context) >= 2:
            last_assistant_msg = None
            # 查找最近的助手消息
            for msg in reversed(context):
                if msg.role == "assistant" and msg.tool_calls:
                    last_assistant_msg = msg
                    break

            if last_assistant_msg:
                # 检查是否成功读取了文件
                has_file_read = any(
                    tc.tool_name == "command_executor" and
                    tc.arguments.get("command") in ["cat", "head", "tail"] and
                    tc.status == "success"
                    for tc in last_assistant_msg.tool_calls
                )

                if has_file_read:
                    # 提取文件名
                    for tc in last_assistant_msg.tool_calls:
                        if tc.tool_name == "command_executor" and tc.arguments.get("command") in ["cat", "head", "tail"]:
                            args = tc.arguments.get("args", [])
                            if args:
                                file_path = args[-1]  # 最后一个参数通常是文件路径
                                file_name = file_path.split('/')[-1]  # 提取文件名

                                # 检查当前消息是否是重复请求
                                # 重要：只在用户原始请求时进行重复检测，不在工具执行结果的中间轮次检测
                                # 工具执行结果通常以"工具 XXX 执行成功"开头
                                is_tool_result = message.startswith("工具 ") or "执行成功" in message[:50]

                                # 调试日志：记录工具结果判断
                                logger.info(f"[DEBUG] 重复检测: message前50字符={repr(message[:50])}, is_tool_result={is_tool_result}")

                                if not is_tool_result:
                                    current_lower = message.lower()
                                    file_name_in_message = file_name.lower() in current_lower
                                    has_view_keyword = any(keyword in current_lower for keyword in ["查看", "显示", "读取"])

                                    if file_name_in_message and has_view_keyword:
                                        # 是重复请求，返回提示
                                        logger.info(f"[DEBUG] 检测到重复文件查看请求: {message} (之前查看过: {file_name})")
                                        return f"我刚才已经展示过{file_name}文件的内容。如果您需要重新查看，请明确说'重新查看'或'刷新'，或者告诉我您想了解文件的哪个具体部分。"

        # 调试日志：记录上下文内容
        logger.info(f"[DEBUG] _think_and_decide 上下文: {len(context)} 条消息")
        for i, msg in enumerate(context):
            logger.info(f"[DEBUG] 上下文[{i}]: role={msg.role}, content前100字符={repr(msg.content[:100])}, tool_calls={len(msg.tool_calls) if msg.tool_calls else 0}")

        # 构建消息列表
        messages = [Message(role="system", content=system_prompt)]

        # 上下文处理策略：直接使用context，它已经是对话历史的合理子集
        # context由ConversationHistory.get_context()返回，包含最近的消息轮次
        # 不要修改或过滤context，直接添加到messages中
        for msg in context:
            messages.append(msg)

        # 添加当前用户消息
        messages.append(Message(role="user", content=message))

        # 调试日志：记录发送给LLM的所有消息
        logger.info(f"[DEBUG] 发送给LLM的消息列表（共{len(messages)}条）:")
        for i, msg in enumerate(messages):
            logger.info(f"[DEBUG]   消息[{i}]: role={msg.role}, content前150字符={repr(msg.content[:150])}")

        # 调用 LLM
        response = await self.llm_provider.chat(
            messages=messages,
            temperature=0.7
        )

        # 调试日志：记录LLM的响应
        logger.info(f"[DEBUG] _think_and_decide LLM响应: {repr(response[:200])}")

        return response

    def _parse_tool_use(self, thought: str) -> Dict[str, Any] | None:
        """解析思考结果，提取工具调用

        Args:
            thought: 思考结果

        Returns:
            工具调用信息或 None
        """
        import logging
        logger = logging.getLogger(__name__)

        # 格式1: 匹配标准格式 TOOL: tool_name
        tool_match = re.search(r'TOOL:\s*(\w+)', thought, re.IGNORECASE)
        args_match = re.search(r'ARGS:\s*(\{.*?\})', thought, re.DOTALL | re.IGNORECASE)

        if tool_match:
            tool_name = tool_match.group(1)
            if args_match:
                try:
                    args = json.loads(args_match.group(1))
                    logger.info(f"[DEBUG] 解析工具调用(标准格式): {tool_name} {args}")
                    return {"name": tool_name, "args": args}
                except json.JSONDecodeError:
                    logger.warning(f"[DEBUG] JSON解析失败，使用空参数")
                    return {"name": tool_name, "args": {}}
            else:
                logger.info(f"[DEBUG] 解析工具调用(标准格式，无参数): {tool_name}")
                return {"name": tool_name, "args": {}}

        # 格式2: 匹配简化格式 (tool_name\n{args}) - LLM有时会返回这种格式
        lines = thought.strip().split('\n')
        if len(lines) >= 1:
            first_line = lines[0].strip()
            # 检查是否是有效的工具名称
            valid_tools = ["semantic_search", "command_executor", "sys_monitor", "file_upload", "file_download"]
            if first_line in valid_tools:
                tool_name = first_line
                args = {}
                # 尝试从第二行解析JSON参数
                if len(lines) >= 2:
                    try:
                        args = json.loads(lines[1].strip())
                        logger.info(f"[DEBUG] 解析工具调用(简化格式): {tool_name} {args}")
                        return {"name": tool_name, "args": args}
                    except json.JSONDecodeError:
                        logger.warning(f"[DEBUG] 简化格式JSON解析失败")
                        return {"name": tool_name, "args": {}}
                else:
                    logger.info(f"[DEBUG] 解析工具调用(简化格式，无参数): {tool_name}")
                    return {"name": tool_name, "args": {}}

        logger.warning(f"[DEBUG] 无法解析工具调用: {repr(thought[:100])}")
        return None

    async def _generate_final_response_stream(
        self,
        message: str,
        conversation_history: ConversationHistory,
        tool_calls: List[ToolCall]
    ):
        """生成最终回复（流式输出）

        Args:
            message: 消息
            conversation_history: 对话历史
            tool_calls: 工具调用列表

        Yields:
            str: 流式输出的文本片段
        """
        # 调试日志：检查tool_calls
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] _generate_final_response_stream被调用, tool_calls数量: {len(tool_calls)}")
        for i, call in enumerate(tool_calls):
            logger.info(f"[DEBUG] tool_call[{i}]: tool_name={call.tool_name}, status={call.status}")
            logger.info(f"[DEBUG] tool_call[{i}] arguments: {call.arguments}")

        # 特殊处理1: semantic_search成功后，自动调用command_executor读取完整文件内容
        if (len(tool_calls) == 1 and
            tool_calls[0].status == "success" and
            tool_calls[0].tool_name == "semantic_search" and
            tool_calls[0].result):

            # 提取文件路径
            result = tool_calls[0].result
            # semantic_search返回格式: "文件路径: xxx\n..."
            import re
            path_match = re.search(r'文件路径[:：]\s*(.+?)(?:\n|$)', result)
            if path_match:
                file_path = path_match.group(1).strip()
                logger.info(f"[DEBUG] 检测到semantic_search返回文件路径: {file_path}")

                # 调用command_executor读取文件
                try:
                    cmd_result = self.tools["command_executor"].execute(
                        "cat",
                        [file_path]
                    )

                    if cmd_result.success:
                        # 替换tool_calls为command_executor的结果，用于后续处理
                        from server.storage.history import ToolCall
                        import datetime

                        new_call = ToolCall(
                            tool_name="command_executor",
                            arguments={"command": "cat", "args": [file_path]},
                            result=cmd_result.output,
                            status="success",
                            duration=0.0,
                            timestamp=datetime.datetime.now(),
                            error=None
                        )
                        tool_calls = [new_call]

                        logger.info(f"[DEBUG] 已自动调用cat读取完整文件，长度: {len(cmd_result.output)}")
                    else:
                        logger.warning(f"[DEBUG] cat命令执行失败: {cmd_result.error}")
                except Exception as e:
                    logger.error(f"[DEBUG] 自动调用cat失败: {e}")

        # 特殊处理2：如果tool_calls中包含成功的cat/head/tail命令，直接返回该命令的结果（不经过LLM）
        # 查找第一个成功的 cat/head/tail 命令
        file_content_call = None
        for call in tool_calls:
            if (call.status == "success" and
                call.tool_name == "command_executor" and
                call.arguments.get("command") in ["cat", "head", "tail"]):
                file_content_call = call
                break

        if file_content_call:
            # 直接返回文件内容，使用代码块格式
            file_content = file_content_call.result
            command = file_content_call.arguments.get("command", "")

            # 调试日志：记录原始工具结果
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[DEBUG] Agent直接返回文件内容")
            logger.info(f"[DEBUG] file_content长度: {len(file_content)} 字符")
            logger.info(f"[DEBUG] file_content字节: {len(file_content.encode('utf-8'))} bytes")
            logger.info(f"[DEBUG] file_content前100字符: {repr(file_content[:100])}")
            logger.info(f"[DEBUG] file_content后100字符: {repr(file_content[-100:])}")

            # 根据文件扩展名确定代码块语言
            args = file_content_call.arguments.get("args", [])
            if args and len(args) > 0:
                file_path = args[-1]  # 最后一个参数通常是文件路径
                if file_path.endswith(".yaml") or file_path.endswith(".yml"):
                    lang = "yaml"
                elif file_path.endswith(".json"):
                    lang = "json"
                elif file_path.endswith(".py"):
                    lang = "python"
                elif file_path.endswith(".txt"):
                    lang = "text"
                else:
                    lang = ""  # 自动检测
            else:
                lang = ""

            # 生成响应（使用无语言标记的代码块，保留格式但不触发语法高亮）
            # 使用``````而不是```yaml```，避免Rich的YAML语法高亮导致的中文显示问题
            response = f"文件内容如下：\n\n```\n{file_content}\n```\n"

            # 调试日志：记录生成的响应
            logger.info(f"[DEBUG] response长度: {len(response)} 字符")
            logger.info(f"[DEBUG] response字节: {len(response.encode('utf-8'))} bytes")
            logger.info(f"[DEBUG] response前150字符: {repr(response[:150])}")
            logger.info(f"[DEBUG] response后150字符: {repr(response[-150:])}")

            # 一次性输出整个响应，避免分块破坏markdown代码块结构
            yield response
            return

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

        # 调用 LLM 流式API
        try:
            async for chunk in self.llm_provider.chat_stream(
                messages=[Message(role="user", content=prompt)],
                temperature=0.7
            ):
                yield chunk  # 真正的流式输出
        except Exception as e:
            # 如果 LLM 调用失败，返回工具结果摘要（非流式）
            summary = self._summarize_tool_results(tool_calls)
            # 将摘要模拟为流式输出
            chunk_size = 2
            for i in range(0, len(summary), chunk_size):
                yield summary[i:i + chunk_size]
                await asyncio.sleep(0.01)

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
