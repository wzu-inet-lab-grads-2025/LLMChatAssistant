# 流式输出速度问题分析与解决

## 问题描述

用户反馈流式输出"太快"，一秒不到就显示出了大块文字，看起来不像"打字机效果"。

## 问题分析

### 原因 1：服务器端分块发送速度过快

**原始代码**：
```python
chunk_size = 100  # 每次发送 100 字符
await asyncio.sleep(0.02)  # 每次延迟 20ms
```

**时间计算**：
- 300 字符回复 = 3 块 × 20ms = **60ms** (0.06秒)
- 1000 字符回复 = 10 块 × 20ms = **200ms** (0.2秒)

### 原因 2：网络延迟几乎为 0

本地环境（localhost）的网络延迟 < 1ms，可以忽略不计。

### 原因 3：UI 刷新率不匹配

- 服务器：每 20ms 发送一次
- 客户端 UI：12fps = 每 83ms 刷新一次
- 结果：客户端累积 3-4 个 chunk 才刷新一次显示，导致"跳跃式"输出

### 原因 4：LLM 本身不是真正的流式

当前实现：
1. Agent 调用 LLM 的 `chat()` 方法（非流式）
2. 等待完整回复
3. 将完整回复分块发送
4. 每块之间有延迟

**关键问题**：这不是真正的流式输出，而是"延迟显示"。

## 解决方案

### 方案 1：调整参数（已实现）

**修改配置**：
```yaml
streaming:
  enabled: true
  chunk_size: 20  # 从 100 减小到 20
  delay: 0.05  # 从 0.02 增加到 0.05 (50ms)
```

**新时间计算**：
- 300 字符回复 = 15 块 × 50ms = **750ms** (0.75秒)
- 1000 字符回复 = 50 块 × 50ms = **2500ms** (2.5秒)

**效果**：更接近"打字机效果"的自然速度。

### 方案 2：真正的 LLM 流式输出（未来）

使用 LLM 的 `chat_stream()` API，从模型生成时就开始发送：

```python
async def _handle_chat(self, session: Session, message: str):
    # 发送流式开始标记
    await session.send_stream_start()

    # 直接使用 LLM 流式 API
    async for chunk in self.llm_provider.chat_stream(
        messages=messages,
        temperature=0.7
    ):
        # 立即发送每个字符/标记
        await session.send_stream_chunk(chunk)

    # 发送流式结束标记
    await session.send_stream_end()
```

**优点**：
- 真正的实时流式输出
- 无需等待完整回复
- 延迟更小

**缺点**：
- 需要修改 Agent 逻辑
- 工具调用流程需要重新设计

### 方案 3：智能延迟（未来）

根据回复长度自动调整速度：

```python
# 短消息（< 100 字符）：较快
if len(response) < 100:
    delay = 0.03
# 中等消息（100-500 字符）：中等
elif len(response) < 500:
    delay = 0.05
# 长消息（> 500 字符）：较慢
else:
    delay = 0.08
```

## 配置说明

### 参数推荐值

| 场景 | chunk_size | delay | 说明 |
|------|-----------|-------|------|
| 快速输出 | 50 | 0.03 | 适合频繁交互 |
| 平衡（默认） | 20 | 0.05 | 推荐配置 |
| 慢速输出 | 10 | 0.1 | 更明显的打字效果 |
| 极慢（演示） | 5 | 0.15 | 用于展示 |

### 参数范围限制

```python
# 验证规则
1 <= chunk_size <= 100
0.01 <= delay <= 0.5
```

## 性能影响

### 网络开销

- **chunk_size = 20**：每个消息约 60 字节（5 字节头部 + 20 字符 UTF-8 约 60 字节）
- 1000 字符回复 = 50 条消息 = 3000 字节
- 网络开销可忽略不计（< 0.1% 带宽）

### CPU 开销

- 服务器：主要在 `asyncio.sleep()`，CPU 占用极低
- 客户端：Rich Markdown 渲染，每块约 1-2ms

## 测试建议

1. **短消息测试**（50-100 字符）
   ```bash
   python test_stream_output.py
   ```

2. **长消息测试**（500-1000 字符）
   - 问复杂问题，如"详细介绍 Python 的历史"

3. **参数调优**
   - 修改 `config.yaml` 中的 `chunk_size` 和 `delay`
   - 找到最适合你感觉的配置

## 相关文件

- [src/server/main.py](../src/server/main.py) - 使用配置参数
- [src/utils/config.py](../src/utils/config.py) - 流式输出配置类
- [config.yaml](../config.yaml) - 配置文件
- [docs/streaming-output-implementation.md](streaming-output-implementation.md) - 实现文档

## 更新日志

- **2025-12-29**：初始分析，将 chunk_size 从 100 降低到 20，delay 从 0.02s 增加到 0.05s
