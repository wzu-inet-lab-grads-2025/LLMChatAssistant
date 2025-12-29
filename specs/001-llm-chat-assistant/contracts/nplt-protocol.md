# NPLT 协议规范

**版本**: 2.0 | **日期**: 2025-12-29

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2025-12-28 | 初始版本，使用 1 字节长度字段（最大 255 字节） |
| 2.0 | 2025-12-29 | 扩展为 2 字节长度字段（最大 65535 字节），支持长消息传输 |

## 概述

NPLT (Network Protocol for LLM Transport) 是一个轻量级的二进制应用层协议，用于在客户端和服务器之间传输实时聊天消息、Agent 思考过程和文件传输提议。

## 协议设计目标

1. **简单性**: 固定头部 + 可变负载，易于实现
2. **实时性**: 支持流式传输，低延迟
3. **可靠性**: 序列号支持消息排序和丢失检测
4. **扩展性**: 预留消息类型空间

## 数据包格式

### 包结构

```
+--------+--------+--------+----------+
| Type   | Seq    | Len    | Data     |
| 1 Byte | 2 Bytes| 2 Bytes| <=64KB   |
+--------+--------+--------+----------+
```

### 字段说明

| 字段 | 大小 | 类型 | 描述 |
|------|------|------|------|
| Type | 1 Byte | uint8 | 消息类型，参见 [消息类型](#消息类型) |
| Seq | 2 Bytes | uint16 | 序列号，范围 0-65535，大端序 |
| Len | 2 Bytes | uint16 | 数据长度，范围 0-65535 |
| Data | 0-65535 Bytes | bytes | 消息负载，UTF-8 编码文本 |

**总包大小**: 6 + Len 字节（最大 65541 字节）

### 序列号规则

- 序列号从 0 开始递增
- 达到 65535 后回绕到 0
- 每个连接独立维护序列号
- 接收方根据序列号检测消息丢失

## 消息类型

### 类型定义

| Type 值 | 名称 | 方向 | 描述 |
|---------|------|------|------|
| 0x01 | CHAT_TEXT | 双向 | 聊天文本消息 |
| 0x0A | AGENT_THOUGHT | S→C | Agent 思考过程（流式） |
| 0x0C | DOWNLOAD_OFFER | S→C | 文件下载提议 |
| 0x14 | SESSION_LIST | 双向 | 会话列表请求/响应 |
| 0x15 | SESSION_SWITCH | C→S | 会话切换请求 |
| 0x16 | SESSION_NEW | C→S | 创建新会话请求 |
| 0x17 | SESSION_DELETE | C→S | 删除会话请求 |
| 0x18 | MODEL_SWITCH | C→S | 模型切换请求 |

**保留范围**:
- 0x02-0x09: 保留给未来聊天相关功能
- 0x0B: 保留给 Agent 功能扩展
- 0x0D-0x13: 保留给文件传输扩展
- 0x19-0xFF: 预留给自定义功能

### 消息详解

#### 0x01 CHAT_TEXT

**描述**: 用户与 AI 之间的聊天文本

**方向**: 客户端 ↔ 服务器

**Data 格式**: UTF-8 编码的纯文本

**示例**:
```
Type: 0x01
Seq:  0x00, 0x01 (1)
Len:  0x18 (24)
Data: "帮我检查一下服务器内存"
```

#### 0x0A AGENT_THOUGHT

**描述**: Agent 的思考过程和工具调用状态

**方向**: 服务器 → 客户端

**Data 格式**: JSON 或纯文本

**示例**:
```
Type: 0x0A
Seq:  0x00, 0x02 (2)
Len:  0x3C (60)
Data: "⠙ [Tool: sys_monitor] Reading system metrics..."
```

**流式传输**: Agent_THOUGHT 消息可以分多个包发送，客户端按序列号组装显示。

#### 0x0C DOWNLOAD_OFFER

**描述**: 服务器向客户端提议下载文件

**方向**: 服务器 → 客户端

**Data 格式**: JSON

```json
{
  "token": "abc123",
  "filename": "error.log",
  "size": 2621440,
  "checksum": "a1b2c3d4"
}
```

**字段说明**:
- `token`: 下载令牌，用于关联 TCP 和 UDP 传输
- `filename`: 文件名
- `size`: 文件大小（字节）
- `checksum`: CRC32 校验和

#### 0x14 SESSION_LIST

**描述**: 获取或返回会话列表

**方向**: 客户端 ↔ 服务器

**客户端请求**:
```
Type: 0x14
Seq:  0x00, 0x01
Len:  0x00 (0)
Data: "" (空请求)
```

**服务器响应**:
```
Type: 0x14
Seq:  0x00, 0x02
Len:  0xXX (可变)
Data: JSON 格式
```

**Data 格式** (JSON):
```json
{
  "sessions": [
    {
      "session_id": "abc123...",
      "name": "系统监控",
      "message_count": 15,
      "last_accessed": "2025-12-29T10:30:00",
      "is_current": true
    },
    {
      "session_id": "def456...",
      "name": "故障排查",
      "message_count": 8,
      "last_accessed": "2025-12-28T15:20:00",
      "is_current": false
    }
  ]
}
```

#### 0x15 SESSION_SWITCH

**描述**: 切换到指定会话

**方向**: 客户端 → 服务器

**Data 格式**: JSON

**请求**:
```json
{
  "session_id": "abc123..."
}
```

**响应** (成功):
```
Type: 0x14 (使用 SESSION_LIST 响应格式)
Data: {"success": true, "message": "已切换到会话：系统监控"}
```

**响应** (失败):
```json
{
  "success": false,
  "error": "会话不存在"
}
```

#### 0x16 SESSION_NEW

**描述**: 创建新会话

**方向**: 客户端 → 服务器

**Data 格式**: JSON 或空

**请求**:
```
Type: 0x16
Data: "" (空，服务器自动生成会话)
```

**响应**:
```json
{
  "success": true,
  "session_id": "new-session-uuid...",
  "name": "2025-12-29 10:35"
}
```

#### 0x17 SESSION_DELETE

**描述**: 删除指定会话

**方向**: 客户端 → 服务器

**Data 格式**: JSON

**请求**:
```json
{
  "session_id": "abc123..."
}
```

**响应** (成功):
```json
{
  "success": true,
  "message": "会话已删除"
}
```

**响应** (失败):
```json
{
  "success": false,
  "error": "无法删除当前活跃会话"
}
```

#### 0x18 MODEL_SWITCH

**描述**: 切换 LLM 模型

**方向**: 客户端 → 服务器

**Data 格式**: JSON

**请求**:
```json
{
  "model": "glm-4-flash"
}
```

**响应** (成功):
```json
{
  "success": true,
  "message": "已切换到模型：glm-4-flash",
  "previous_model": "glm-4.5-flash"
}
```

**响应** (失败):
```json
{
  "success": false,
  "error": "不支持的模型：invalid-model"
}
```

## 状态机

### 发送方状态

```
IDLE → SENDING → WAIT_ACK → SENT
                ↓
              TIMEOUT
```

### 接收方状态

```
IDLE → RECEIVING → PROCESSING → DONE
                    ↓
                  ERROR
```

## 错误处理

### 错误检测

1. **长度校验**: `Len` 字段与实际数据长度不匹配
2. **序列号校验**: 检测序列号跳变（表示丢包）
3. **类型校验**: 未知的消息类型

### 错误恢复

1. **长度错误**: 丢弃数据包，记录日志
2. **序列号跳变**: 记录丢失的序列号，继续处理
3. **未知类型**: 记录警告，忽略数据包

## 安全考虑

### 当前实现

- 协议无加密，明文传输
- 无身份验证机制
- 适用于可信网络环境

### 未来增强

- TLS/SSL 加密（TCP 层）
- Token 认证（应用层）
- 消息签名（完整性验证）

## 性能优化

### 批量发送

对于超长文本（>64KB），分多个包发送：

```
包 1: Type=0x01, Seq=0, Data="前 64KB 数据..."
包 2: Type=0x01, Seq=1, Data="后续 64KB 数据..."
包 3: Type=0x01, Seq=2, Data="最后部分"
```

接收方按序列号组装完整消息。

**注**: v2 协议（64KB 限制）通常无需分块，LLM 回复和工具调用结果均可直接传输。

### 流式传输

对于 AGENT_THOUGHT 消息，支持流式传输：

```
包 1: Type=0x0A, Seq=0, Data="⠙ [Tool: sys_monitor] Reading..."
包 2: Type=0x0A, Seq=1, Data="⠹ [Tool: sys_monitor] Reading metrics..."
包 3: Type=0x0A, Seq=2, Data="✓ [Tool: sys_monitor] Done. CPU: 45%, Mem: 53%"
```

## 示例代码

### Python 实现示例

```python
import struct
from dataclasses import dataclass
from enum import IntEnum

class MessageType(IntEnum):
    CHAT_TEXT = 0x01
    AGENT_THOUGHT = 0x0A
    DOWNLOAD_OFFER = 0x0C
    SESSION_LIST = 0x14
    SESSION_SWITCH = 0x15
    SESSION_NEW = 0x16
    SESSION_DELETE = 0x17
    MODEL_SWITCH = 0x18

@dataclass
class NPLTMessage:
    type: MessageType
    seq: int
    data: bytes

    def encode(self) -> bytes:
        """编码为字节流"""
        header = struct.pack(
            ">BHH",  # 大端序: uint8, uint16, uint16 (v2)
            self.type,
            self.seq,
            len(self.data)
        )
        return header + self.data

    @classmethod
    def decode(cls, data: bytes) -> 'NPLTMessage':
        """从字节流解码"""
        if len(data) < 5:  # v2: 头部 5 字节
            raise ValueError("数据包太短")

        type_val, seq, length = struct.unpack(">BHH", data[:5])
        payload = data[5:5+length]

        if len(payload) != length:
            raise ValueError(f"数据长度不匹配: 期望 {length}, 实际 {len(payload)}")

        return cls(
            type=MessageType(type_val),
            seq=seq,
            payload=payload
        )

# 使用示例
msg = NPLTMessage(
    type=MessageType.CHAT_TEXT,
    seq=1,
    data="帮我检查一下服务器内存".encode('utf-8')
)

encoded = msg.encode()
decoded = NPLTMessage.decode(encoded)
```

## 测试场景

### 正常流程测试

1. 客户端发送 CHAT_TEXT 消息
2. 服务器接收并解析
3. 服务器发送 AGENT_THOUGHT 消息（流式）
4. 服务器发送 CHAT_TEXT 消息（AI 回复）
5. 客户端接收并显示

### 边界条件测试

1. **空消息**: `Len = 0`, `Data = ""`
2. **最大消息**: `Len = 65535`, `Data = "..."*65535` (64KB)
3. **序列号回绕**: `Seq = 65535` → `Seq = 0`
4. **未知类型**: `Type = 0xFF`
5. **中文编码**: 长中文消息（UTF-8 编码，每个字符 3 字节）

### 异常场景测试

1. **长度不匹配**: `Len = 10`, 实际数据 20 字节
2. **序列号跳变**: 接收 Seq = 0, 2, 5（缺少 1, 3, 4）
3. **截断数据包**: 只接收到前 3 字节

## 客户端状态管理

### 状态机设计

客户端使用状态机来管理用户交互流程，确保UI响应与服务器消息同步：

```
IDLE（空闲） → WAITING（等待响应） → DISPLAYING（显示消息） → IDLE
```

### 状态转换

| 状态 | 触发条件 | UI表现 | 后续动作 |
|------|---------|--------|----------|
| **IDLE** | 客户端启动或上一轮完成 | 显示 `你:` 提示符，等待用户输入 | 接收用户输入，发送消息，进入WAITING |
| **WAITING** | 发送CHAT_TEXT消息后 | 显示 `⠋ [Agent] 正在分析意图...` Spinner | 等待AGENT_THOUGHT或CHAT_TEXT响应 |
| **WAITING** | 收到AGENT_THOUGHT | 更新Spinner为 `⠙ [Tool: xxx] ...` | 继续等待 |
| **DISPLAYING** | 收到CHAT_TEXT（非心跳） | 停止Spinner，显示AI回复消息 | 触发响应完成回调，返回IDLE |

### 实现细节

#### 1. 状态变量

```python
waiting_for_response: bool  # 是否正在等待AI响应
response_event: asyncio.Event  # 响应完成事件
```

#### 2. 主循环逻辑

```python
while running:
    if waiting_for_response:
        # 等待响应完成（最多30秒）
        await asyncio.wait_for(response_event.wait(), timeout=30.0)
        waiting_for_response = False
        response_event.clear()
        continue

    # 获取用户输入
    user_input = ui.input("你: ")

    # 发送消息
    await send_chat(user_input)

    # 进入等待状态
    waiting_for_response = True
    ui.show_spinner("⠋ [Agent] 正在分析意图...")
```

#### 3. 消息处理回调

```python
async def on_chat_text(text):
    ui.stop_spinner()
    ui.print_message("assistant", text)
    response_event.set()  # 通知主循环

async def on_agent_thought(text):
    ui.stop_spinner()
    ui.show_spinner(f"⠙ {text}")
```

### 优势

1. **无固定延时**：基于事件驱动，响应到达立即显示
2. **状态可见**：Spinner实时显示Agent状态
3. **防止重复输入**：等待期间不显示输入提示符
4. **超时保护**：30秒超时防止无限等待

## 参考资料

- [TCP/IP 协议栈](https://en.wikipedia.org/wiki/Internet_protocol_suite)
- [应用层协议设计最佳实践](https://en.wikipedia.org/wiki/Application_layer)
- [二进制协议设计](https://commandcenter.blogspot.com/2012/04/byte-order-fallacy.html)
