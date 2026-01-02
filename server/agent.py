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
        """思考并生成回复（流式输出，支持ReAct工具调用）

        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            session: Session对象（用于工具访问uploaded_files等）

        Yields:
            str: 流式输出的文本片段
        """
        import sys
        # 强制写入调试文件
        with open('/tmp/think_stream_debug.log', 'a') as f:
            f.write(f"[{time.time()}] think_stream调用: {user_message[:50]}\n")
            f.flush()

        try:
            # 发送状态：正在分析
            await self._send_status("thinking", "正在分析用户意图")

            # 使用 ReAct 循环处理可能需要工具的请求
            print(f"[DEBUG] think_stream: 开始，消息={user_message[:30]}", file=sys.stderr, flush=True)
            final_response, tool_calls = await self.react_loop(
                user_message=user_message,
                conversation_history=conversation_history,
                session=session
            )
            print(f"[DEBUG] think_stream: react_loop完成，工具调用次数={len(tool_calls)}", file=sys.stderr, flush=True)

            with open('/tmp/think_stream_debug.log', 'a') as f:
                f.write(f"[{time.time()}] react_loop完成，工具调用次数={len(tool_calls)}\n")
                f.flush()

            # 发送状态：正在生成
            await self._send_status("generating", "正在生成回复")

            # 对最终回复进行流式输出
            # 由于 react_loop 返回的是完整字符串，我们需要模拟流式输出
            chunk_size = 2  # 每次发送2个字符
            for i in range(0, len(final_response), chunk_size):
                chunk = final_response[i:i + chunk_size]
                yield chunk
                # 添加小延迟模拟流式输出
                await asyncio.sleep(0.01)

        except Exception as e:
            # API 调用失败，降级到本地命令执行
            import sys
            import traceback
            print(f"[ERROR] think_stream异常: {e}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            fallback_response = self._fallback_to_local(user_message, str(e))
            # 模拟流式输出
            chunk_size = 2
            for i in range(0, len(fallback_response), chunk_size):
                chunk = fallback_response[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.01)

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
        conversation_history: ConversationHistory,
        session=None
    ) -> tuple[str, List[ToolCall]]:
        """ReAct 循环：推理 -> 行动 -> 观察

        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            session: Session对象（用于工具访问uploaded_files等）

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

                # 调试：记录LLM返回
                with open('/tmp/llm_response_debug.log', 'a') as f:
                    f.write(f"\n=== 第{round_count}轮 LLM返回 ===\n{thought}\n{'='*50}\n")
                    f.flush()

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
4. 文件操作（上传、下载、检索）使用专用文件工具

## 决策流程

**步骤1: 识别查询类型**
- 系统资源查询（CPU/内存/磁盘使用率、系统状态）→ sys_monitor（优先）
- 具体命令名执行（ls/cat/grep/head/tail/ps/pwd/whoami/df/free）→ command_executor
- 文件/文档检索（搜索文件、查找文档、检索信息）→ semantic_search（支持混合检索策略：精确匹配→模糊匹配→语义检索）
- 文件索引管理（查看上传的文件、引用文件）→ file_upload
- 文件下载（下载文件、发给我、把XX文件发给我）→ file_download（先用semantic_search定位，再用file_download准备下载）
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

### semantic_search 示例（混合检索策略）

用户: 搜索配置文件
TOOL: semantic_search
ARGS: {"query": "config.yaml", "top_k": 3}
# 精确文件名匹配 → similarity=1.0, match_type=exact_filename

用户: 搜索关于数据库的文档
TOOL: semantic_search
ARGS: {"query": "数据库配置", "top_k": 3, "scope": "all"}
# 语义检索 → 返回相关文档及其匹配片段

用户: 找一下日志文件
TOOL: semantic_search
ARGS: {"query": "log", "top_k": 5}
# 模糊匹配 → 返回所有包含"log"的文件（.log文件）

### 文件操作示例

# 文件索引管理（file_upload - 重新定义为索引管理工具）
用户: 查看上传的文件
TOOL: file_upload
ARGS: {"action": "list", "reference": "all"}

用户: 这个文件的内容是什么？
TOOL: file_upload
ARGS: {"action": "list", "reference": "this"}

# 串行工具调用：先搜索再下载
用户: 把配置文件发给我
TOOL: semantic_search
ARGS: {"query": "config.yaml", "top_k": 1}
# 第1步：精确匹配找到文件
# 第2步：准备下载
TOOL: file_download
ARGS: {"file_path": "/home/zhoutianyu/tmp/LLMChatAssistant/storage/uploads/550e8400/config.yaml"}

用户: 搜索数据库配置文档
TOOL: semantic_search
ARGS: {"query": "数据库配置", "top_k": 3, "scope": "all"}

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
