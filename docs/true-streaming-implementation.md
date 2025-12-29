# 真正的流式输出实现

## 核心理念

流式输出的目的是**改善用户体验**，让用户在等待 LLM 响应期间就能看到输出，而不是等待几秒钟后突然看到完整回复。

## 对比：假流式 vs 真流式

### 假流式（之前）

```
用户发送消息
  ↓
[等待 2-5 秒] LLM 生成完整回复（后台，用户看不到任何东西）
  ↓
拿到完整回复后，分块慢慢发送
  ↓
[显示 0.5-2 秒] 打字机效果
  ↓
用户看到完整回复

总用户等待时间：2-7 秒（其中 2-5 秒是什么都看不到）
```

**问题**：用户在 LLM 生成期间（最耗时的部分）看不到任何反馈，失去了流式输出的意义。

### 真流式（现在）

```
用户发送消息
  ↓
LLM 开始生成，立即返回第一个字符
  ↓
[几乎 0 等待] 立即发送给客户端并显示
  ↓
LLM 继续生成...
  ↓
边生成边发送边显示
  ↓
用户立即看到输出，持续更新直到完成

总用户等待时间：0 秒（立即看到第一个字符）
```

**优势**：
- ✅ 用户立即看到输出（几乎 0 等待）
- ✅ 感知响应速度更快
- ✅ 更自然的交互体验
- ✅ 显示速度由 LLM 生成速度决定（不是人工延迟）

## 实现方案

### 服务器端代码

**文件**: [src/server/main.py](../src/server/main.py)

```python
async def _handle_chat(self, session: Session, message: str):
    # 设置 Agent 的状态回调（用于发送状态更新）
    self.agent.status_callback = lambda msg: session.send_status_json(msg)

    # 使用 Agent 的 think_stream 方法，它会自动发送状态通知
    full_response = ""
    buffer = ""
    buffer_size = 50  # 增大缓冲区以减少客户端 Panel 重新渲染次数
    stream_started = False

    async for chunk in self.agent.think_stream(
        user_message=message,
        conversation_history=session.conversation_history
    ):
        full_response += chunk
        buffer += chunk

        # 缓冲区满了就发送
        if len(buffer) >= buffer_size:
            if not stream_started:
                await session.send_stream_start()
                stream_started = True
            await session.send_stream_chunk(buffer)
            buffer = ""

    # 发送剩余的缓冲区内容
    if buffer:
        if not stream_started:
            await session.send_stream_start()
        await session.send_stream_chunk(buffer)

    # 发送流式结束标记
    await session.send_stream_end()
```

**关键点**：
1. **使用 Agent.think_stream()**：通过 Agent 层调用 LLM 的流式 API，保留状态通知
2. **状态回调**：Agent 会自动发送 "正在分析意图"、"正在生成回复" 等状态
3. **适中的缓冲区**：`buffer_size = 50`，平衡实时性和性能
4. **累积完整回复**：用于保存到历史记录

### Agent 层

**文件**: [src/server/agent.py](../src/server/agent.py)

Agent 提供了 `think_stream()` 方法，用于带状态通知的流式输出：

```python
async def think_stream(self, user_message: str, conversation_history: ConversationHistory):
    """思考并生成回复（流式输出）"""
    try:
        # 发送状态：正在分析
        await self._send_status("thinking", "正在分析用户意图")

        # 获取上下文并构建消息
        context = conversation_history.get_context(max_turns=5)
        messages = []
        for msg in context:
            messages.append(Message(role=msg.role, content=msg.content))
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
```

## 效果对比

### 时间分析

**300 字符回复**：

| 方式 | 用户等待 | 显示时间 | 总体验 |
|------|---------|---------|--------|
| 假流式 | 2-5秒 | 0.5秒 | 差 |
| 真流式 | **0秒** | 2-5秒 | 优秀 |

**1000 字符回复**：

| 方式 | 用户等待 | 显示时间 | 总体验 |
|------|---------|---------|--------|
| 假流式 | 3-7秒 | 2秒 | 差 |
| 真流式 | **0秒** | 3-7秒 | 优秀 |

### 用户体验

**假流式**：
```
用户：你好
[等待 3 秒...]
Assistant: 你好！我是...
```

**真流式**：
```
用户：你好
Assistant: 你 [立即出现]
Assistant: 你好！[持续更新]
Assistant: 你好！我是 AI 助手[持续更新]
...
```

## 权衡与取舍

### 工具调用 vs 流式输出

**问题**：ReAct Agent 需要完整回复来判断是否调用工具，这与流式输出冲突。

**当前解决方案**：
- **简单对话**：直接使用流式输出（无工具）
- **复杂对话**：暂时不使用流式（需要工具调用）

**未来改进**：
1. 两阶段流式：
   - 第一阶段：快速预判（小模型/少 token）是否需要工具
   - 第二阶段：流式输出最终回复

2. 并行推理：
   - 后台进行 ReAct 推理（工具调用）
   - 前台同时流式输出思考过程

### 性能考虑

**缓冲区大小选择**：

| buffer_size | 优点 | 缺点 | 推荐场景 |
|-------------|------|------|---------|
| 1-5 | 最实时 | 网络开销大 | 演示/局域网 |
| **10** | **平衡** | **适中** | **默认推荐** |
| 20-50 | 低开销 | 略有延迟 | 公网/远程 |

## 测试结果

实际测试（300 字符回复）：

```
✓ 立即看到空 Panel（0 等待）
✓ 文字逐渐出现（由 LLM 生成速度决定）
✓ 最终内容完整显示
✓ 无人工延迟，完全自然
```

## 配置文件

**注意**：真正的流式输出不需要调整 `config.yaml` 中的 `delay` 参数，因为不再使用人工延迟。

```yaml
streaming:
  enabled: true
  # 这些参数仅用于"假流式"模式
  chunk_size: 20
  delay: 0.05
```

## 相关文件

- [src/server/main.py](../src/server/main.py) - 使用 Agent.think_stream() 实现流式输出
- [src/server/agent.py](../src/server/agent.py) - Agent.think_stream() 方法
- [src/llm/zhipu.py](../src/llm/zhipu.py) - LLM 流式 API
- [src/protocols/nplt.py](../src/protocols/nplt.py) - 消息协议
- [src/client/nplt_client.py](../src/client/nplt_client.py) - 客户端接收和状态处理
- [src/client/ui.py](../src/client/ui.py) - UI 渲染和节流优化

## 更新日志

- **2025-12-29 15:30**：优化流式输出
  - 通过 Agent.think_stream() 恢复状态通知
  - 服务器缓冲区从 10 增加到 50 字符
  - 添加客户端节流（10fps），大幅减少 Panel 重新渲染
- **2025-12-29 14:12**：实现真正的流式输出，移除人工延迟，直接使用 LLM 流式 API
- **2025-12-29 13:57**：初始实现（假流式），使用完整回复+分块发送+人工延迟
