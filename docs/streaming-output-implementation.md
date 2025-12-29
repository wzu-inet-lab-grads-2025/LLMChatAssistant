# 流式输出实现文档

## 概述

本文档描述了 LLMChatAssistant 的流式输出功能实现，包括 Agent 状态通知、流式消息传输和前端 UI 展示。

## 设计目标

1. **提供实时反馈**：用户可以看到 Agent 的思考过程（分析意图、思考、调用工具、生成回复）
2. **流式输出**：AI 回复采用打字机效果逐字显示
3. **Markdown 实时渲染**：流式输出时正确渲染 Markdown 格式（代码块、加粗、列表等）

## 消息协议设计

### 方案 A：复用现有消息类型

为了保持协议兼容性，我们复用现有的 `AGENT_THOUGHT` 和 `CHAT_TEXT` 消息类型。

#### AGENT_THOUGHT 消息（状态更新）

用于发送 Agent 状态更新，采用 JSON 格式：

```json
{
  "type": "thinking|tool_call|generating|stream_start",
  "content": "状态描述文本"
}
```

**状态类型**：

| type | 说明 | 示例 |
|------|------|------|
| `thinking` | Agent 正在思考 | "正在分析用户意图"<br>"正在思考 (第 1 轮)" |
| `tool_call` | Agent 正在调用工具 | "正在调用工具: sys_monitor" |
| `generating` | Agent 正在生成最终回复 | "正在生成最终回复" |
| `stream_start` | 开始流式输出 | (标记，无内容) |

#### CHAT_TEXT 消息（流式片段）

用于发送流式内容片段：

- **非空内容**：追加到当前流式输出缓冲区
- **空内容**：标记流式输出结束

## 实现架构

### 1. 后端 Agent 层

**文件**: [src/server/agent.py](../src/server/agent.py)

#### 关键改动

1. **添加状态回调机制**：

```python
@dataclass
class ReActAgent:
    status_callback: callable = None  # 状态更新回调函数

    async def _send_status(self, status_type: str, content: str):
        """发送状态更新"""
        if self.status_callback:
            import json
            status_msg = json.dumps({
                "type": status_type,
                "content": content
            }, ensure_ascii=False)
            await self.status_callback(status_msg)
```

2. **在 ReAct 循环中发送状态**：

```python
async def react_loop(self, user_message: str, conversation_history: ConversationHistory):
    while round_count < self.max_tool_rounds:
        # 思考阶段
        await self._send_status("thinking", f"正在思考 (第 {round_count} 轮)")

        # 工具调用阶段
        await self._send_status("tool_call", f"正在调用工具: {tool_name}")

        # 生成回复阶段
        await self._send_status("generating", "正在生成最终回复")
```

### 2. 服务器层

**文件**: [src/server/nplt_server.py](../src/server/nplt_server.py)

#### 关键改动

1. **Session 添加流式发送方法**：

```python
async def send_stream_start(self):
    """发送流式输出开始标记"""
    import json
    start_msg = json.dumps({"type": "stream_start"}, ensure_ascii=False)
    await self.send_message(MessageType.AGENT_THOUGHT, start_msg.encode('utf-8'))

async def send_stream_chunk(self, chunk: str):
    """发送流式内容片段"""
    await self.send_message(MessageType.CHAT_TEXT, chunk.encode('utf-8'))

async def send_stream_end(self):
    """发送流式输出结束标记（空消息）"""
    await self.send_message(MessageType.CHAT_TEXT, b"")

async def send_status_json(self, status_json: str):
    """发送 Agent 状态更新（JSON 格式字符串）"""
    await self.send_message(MessageType.AGENT_THOUGHT, status_json.encode('utf-8'))
```

2. **聊天处理器使用流式输出**：

**文件**: [src/server/main.py](../src/server/main.py)

```python
async def _handle_chat(self, session: Session, message: str):
    # 设置 Agent 的状态回调
    self.agent.status_callback = lambda msg: session.send_status_json(msg)

    # 使用 ReAct Agent 处理消息
    response, tool_calls = await self.agent.react_loop(...)

    # 发送流式开始标记
    await session.send_stream_start()

    # 流式发送回复内容（分块）
    chunk_size = 100
    for i in range(0, len(response), chunk_size):
        chunk = response[i:i + chunk_size]
        await session.send_stream_chunk(chunk)
        await asyncio.sleep(0.02)  # 模拟打字机效果

    # 发送流式结束标记
    await session.send_stream_end()
```

### 3. 客户端层

**文件**: [src/client/nplt_client.py](../src/client/nplt_client.py)

#### 关键改动

1. **添加流式状态机**：

```python
@dataclass
class NPLTClient:
    is_streaming: bool = False  # 是否正在流式输出
```

2. **处理状态更新和流式内容**：

```python
async def _process_message(self, message: NPLTMessage):
    if message.type == MessageType.CHAT_TEXT:
        text = message.data.decode('utf-8', errors='ignore')

        # 流式输出结束标记
        if not text or not text.strip():
            if self.is_streaming:
                self.ui.stop_live_display()
                self.is_streaming = False
            return

        # 流式追加内容
        if self.is_streaming:
            self.ui.stream_content(text)
        else:
            # 非流式模式，直接显示
            self.ui.print_message("assistant", text)

    elif message.type == MessageType.AGENT_THOUGHT:
        text = message.data.decode('utf-8', errors='ignore')

        # 解析 JSON 状态消息
        try:
            import json
            status_data = json.loads(text)
            status_type = status_data.get("type")
            content = status_data.get("content", "")

            if status_type == "stream_start":
                # 开始流式输出
                self.ui.stop_spinner()
                await asyncio.sleep(0.1)
                self.ui.start_live_display()
                self.is_streaming = True

            elif status_type in ["thinking", "tool_call", "generating"]:
                # 更新 spinner 状态
                self.ui.show_spinner(content)
        except json.JSONDecodeError:
            # 兼容旧格式
            self.ui.show_spinner(text)
```

### 4. 前端 UI 层

**文件**: [src/client/ui.py](../src/client/ui.py)

#### 关键改动

1. **流式输出缓冲区**：

```python
def __init__(self):
    self._stream_buffer = ""  # 流式内容的纯文本缓冲区
```

2. **实时 Markdown 渲染**：

```python
def stream_content(self, content: str):
    """流式更新内容"""
    if self.live_display is not None and self.is_live:
        # 1. 累积内容到缓冲区
        self._stream_buffer += content

        # 2. 重新解析 Markdown（全量重新创建以支持跨片段语法）
        markdown_render = Markdown(self._stream_buffer)

        # 3. 创建新的 Panel
        new_panel = Panel(
            markdown_render,
            title="ASSISTANT",
            title_align="left",
            border_style="green"
        )

        # 4. 更新 Live 显示
        self.live_display.update(new_panel)
```

**关键点**：Rich 的 `Markdown` 对象不支持增量更新，必须每次用全量文本重新创建，这样才能正确处理代码块、加粗等跨片段的 Markdown 语法。

## 状态流转图

```
用户发送消息
    ↓
[Agent] 正在分析意图 ⠋ (thinking)
    ↓
[Agent] 正在思考 (第 1 轮) ⠙ (thinking)
    ↓
[Agent] 正在调用工具: sys_monitor ⠹ (tool_call)
    ↓
[Agent] 正在生成最终回复 ⠸ (generating)
    ↓
[开始流式] 停止 spinner，启动 Live Panel (stream_start)
    ↓
[流式内容] 根据... (stream_chunk)
[流式内容] 根据工具执 (stream_chunk)
[流式内容] 行结果... (stream_chunk)
...
    ↓
[结束] 发送空消息 (stream_chunk with empty content)
    ↓
停止 Live Panel，保留最后一帧
```

## 性能优化

1. **刷新率**：Live Display 设置为 12fps，获得流畅的打字机效果
2. **垂直滚动**：设置 `vertical_overflow="visible"` 确保长文本自动滚动
3. **分块大小**：服务器每次发送 100 字符，客户端累积后统一渲染
4. **延迟控制**：服务器发送间隔 20ms，模拟自然的打字速度

## 测试验证

### 测试脚本

**文件**: [test_stream_output.py](../test_stream_output.py)

```bash
python test_stream_output.py
```

### 预期结果

1. ✅ 显示 "正在思考 (第 1 轮)" spinner
2. ✅ 显示 "正在生成最终回复" spinner
3. ✅ 清除 spinner，显示空 Panel
4. ✅ 内容逐字出现（打字机效果）
5. ✅ Markdown 格式正确渲染（列表、加粗等）

## 兼容性说明

- ✅ **向后兼容**：复用现有消息类型，无需修改协议
- ✅ **渐进增强**：旧客户端忽略状态消息，仍然能正常显示最终回复
- ✅ **优雅降级**：如果状态解析失败，回退到普通显示模式

## 未来改进

1. **真正的 LLM 流式输出**：目前是模拟流式（将完整回复分块发送），未来可以直接使用 LLM 的 `chat_stream()` API
2. **工具调用可视化**：在 UI 中展示工具调用的参数和结果
3. **可配置打字速度**：允许用户自定义打字机效果的速度
4. **进度指示**：对于长时间运行的工具，显示进度条或百分比

## 相关文件

- [src/protocols/nplt.py](../src/protocols/nplt.py) - NPLT 协议定义
- [src/server/agent.py](../src/server/agent.py) - Agent 实现
- [src/server/nplt_server.py](../src/server/nplt_server.py) - 服务器实现
- [src/server/main.py](../src/server/main.py) - 服务器主入口
- [src/client/nplt_client.py](../src/client/nplt_client.py) - 客户端实现
- [src/client/ui.py](../src/client/ui.py) - UI 实现
- [src/llm/zhipu.py](../src/llm/zhipu.py) - LLM Provider（支持 `chat_stream()`）

## 更新日志

- **2025-12-29**：初始实现，完成 Agent 状态通知和模拟流式输出
