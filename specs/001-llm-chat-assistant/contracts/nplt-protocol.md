# NPLT 协议规范

**版本**: 1.0 | **日期**: 2025-12-28

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
| 1 Byte | 2 Bytes| 1 Byte | <=255 Bytes|
+--------+--------+--------+----------+
```

### 字段说明

| 字段 | 大小 | 类型 | 描述 |
|------|------|------|------|
| Type | 1 Byte | uint8 | 消息类型，参见 [消息类型](#消息类型) |
| Seq | 2 Bytes | uint16 | 序列号，范围 0-65535，大端序 |
| Len | 1 Byte | uint8 | 数据长度，范围 0-255 |
| Data | 0-255 Bytes | bytes | 消息负载，UTF-8 编码文本 |

**总包大小**: 5 + Len 字节（最大 260 字节）

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

**保留范围**:
- 0x02-0x09: 保留给未来聊天相关功能
- 0x0B: 保留给 Agent 功能扩展
- 0x0D-0x0F: 保留给文件传输扩展
- 0x10-0xFF: 预留给自定义功能

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

对于长文本（>255 字节），分多个包发送：

```
包 1: Type=0x01, Seq=0, Data="前 250 字符..."
包 2: Type=0x01, Seq=1, Data="后续 250 字符..."
包 3: Type=0x01, Seq=2, Data="最后部分"
```

接收方按序列号组装完整消息。

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

@dataclass
class NPLTMessage:
    type: MessageType
    seq: int
    data: bytes

    def encode(self) -> bytes:
        """编码为字节流"""
        header = struct.pack(
            ">BHB",  # 大端序: uint8, uint16, uint8
            self.type,
            self.seq,
            len(self.data)
        )
        return header + self.data

    @classmethod
    def decode(cls, data: bytes) -> 'NPLTMessage':
        """从字节流解码"""
        if len(data) < 4:
            raise ValueError("数据包太短")

        type_val, seq, length = struct.unpack(">BHB", data[:4])
        payload = data[4:4+length]

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
2. **最大消息**: `Len = 255`, `Data = "..."*255`
3. **序列号回绕**: `Seq = 65535` → `Seq = 0`
4. **未知类型**: `Type = 0xFF`

### 异常场景测试

1. **长度不匹配**: `Len = 10`, 实际数据 20 字节
2. **序列号跳变**: 接收 Seq = 0, 2, 5（缺少 1, 3, 4）
3. **截断数据包**: 只接收到前 3 字节

## 参考资料

- [TCP/IP 协议栈](https://en.wikipedia.org/wiki/Internet_protocol_suite)
- [应用层协议设计最佳实践](https://en.wikipedia.org/wiki/Application_layer)
- [二进制协议设计](https://commandcenter.blogspot.com/2012/04/byte-order-fallacy.html)
