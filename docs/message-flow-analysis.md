# 客户端-服务器消息传递详解

**创建时间**: 2025-12-31
**目的**: 全面分析NPLT协议下的客户端-服务器消息传递流程

---

## 目录

1. [协议基础](#协议基础)
2. [连接建立](#连接建立)
3. [消息类型与流向](#消息类型与流向)
4. [实时聊天消息流](#实时聊天消息流)
5. [文件传输消息流](#文件传输消息流)
6. [会话管理消息流](#会话管理消息流)
7. [消息格式详解](#消息格式详解)
8. [流式输出机制](#流式输出机制)

---

## 协议基础

### NPLT 协议格式（v2）

```text
+--------+--------+--------+----------+
| Type   | Seq    | Len    | Data     |
| 1 Byte | 2 Bytes| 2 Bytes| <=64KB   |
+--------+--------+--------+----------+
```

**字段说明**:
- `Type`: 1字节，消息类型（MessageType枚举）
- `Seq`: 2字节，序列号（0-65535循环）
- `Len`: 2字节，数据长度（最大65535字节）
- `Data`: 变长，消息载荷（UTF-8编码的文本或JSON）

**实现位置**:
- 协议定义: [src/protocols/nplt.py](../src/protocols/nplt.py)
- 服务器实现: [src/server/nplt_server.py](../src/server/nplt_server.py)
- 客户端实现: [src/client/nplt_client.py](../src/client/nplt_client.py)

---

## 连接建立

### 1. 客户端发起连接

**代码**: [src/client/nplt_client.py:60-97](../src/client/nplt_client.py#L60-L97)

```python
async def connect(self) -> bool:
    while self.retry_count < self.max_retries:
        try:
            # 建立 TCP 连接
            self.reader, self.writer = await asyncio.open_connection(
                self.host,  # 127.0.0.1
                self.port   # 9999
            )
            self.connected = True
            return True
        except Exception as e:
            # 重试逻辑
            await asyncio.sleep(2)
```

**流程**:
```
Client                    Server
  |                         |
  |------- TCP SYN -------> |
  |<------ TCP SYN+ACK ---- |
  |------- TCP ACK -------> |
  |                         |
  |    [连接建立成功]        |
```

### 2. 服务器接受连接

**代码**: [src/server/nplt_server.py:197-239](../src/server/nplt_server.py#L197-L239)

```python
async def _handle_client(self, reader, writer):
    # 创建会话
    session_id = str(uuid.uuid4())
    session = Session(
        session_id=session_id,
        client_addr=addr,
        connected_at=datetime.now(),
        reader=reader,
        writer=writer,
        conversation_history=ConversationHistory.create_new(session_id)
    )

    # 发送欢迎消息
    await session.send_message(
        MessageType.CHAT_TEXT,
        f"欢迎使用智能网络运维助手！会话ID: {session_id[:8]}".encode('utf-8')
    )
```

**流程**:
```
Server
  |
  | 1. 检查连接数限制 (max_clients=10)
  | 2. 创建 Session 对象
  | 3. 初始化 ConversationHistory
  | 4. 发送欢迎消息 (CHAT_TEXT)
  | 5. 启动消息接收循环
```

---

## 消息类型与流向

### 消息类型定义

**代码**: [src/protocols/nplt.py:22-36](../src/protocols/nplt.py#L22-L36)

```python
class MessageType(IntEnum):
    CHAT_TEXT = 0x01          # 聊天文本（双向）
    AGENT_THOUGHT = 0x0A      # Agent思考过程（服务器→客户端）
    DOWNLOAD_OFFER = 0x0C     # 文件下载提议（服务器→客户端）
    FILE_DATA = 0x0D          # 文件数据（客户端→服务器）
    FILE_METADATA = 0x0E      # 文件元数据（客户端→服务器）
    MODEL_SWITCH = 0x0F       # 模型切换请求（客户端→服务器）
    HISTORY_REQUEST = 0x10    # 历史记录请求（客户端→服务器）
    CLEAR_REQUEST = 0x11      # 清空会话请求（客户端→服务器）
    SESSION_LIST = 0x14       # 会话列表请求（客户端→服务器）
    SESSION_SWITCH = 0x15     # 切换会话（客户端→服务器）
    SESSION_NEW = 0x16        # 创建新会话（客户端→服务器）
    SESSION_DELETE = 0x17     # 删除会话（客户端→服务器）
```

### 消息流向图

```
双向消息:
  ┌─────────────────────────────────────┐
  │ CHAT_TEXT                           │
  │   客户端 → 服务器: 用户消息          │
  │   服务器 → 客户端: Agent响应、心跳   │
  └─────────────────────────────────────┘

客户端 → 服务器:
  ┌─────────────────────────────────────┐
  │ FILE_METADATA: 文件上传元数据       │
  │ FILE_DATA: 文件数据块               │
  │ MODEL_SWITCH: 模型切换请求          │
  │ HISTORY_REQUEST: 历史记录请求       │
  │ CLEAR_REQUEST: 清空会话             │
  │ SESSION_LIST/SWITCH/NEW/DELETE      │
  └─────────────────────────────────────┘

服务器 → 客户端:
  ┌─────────────────────────────────────┐
  │ AGENT_THOUGHT: 思考过程、状态更新   │
  │ DOWNLOAD_OFFER: 文件下载提议        │
  └─────────────────────────────────────┘
```

---

## 实时聊天消息流

### 完整流程图

```
用户输入: "查看CPU使用率"
   ↓
┌──────────────────────────────────────────────────────────────┐
│ 1. 客户端发送用户消息                                        │
├──────────────────────────────────────────────────────────────┤
│ Client.send_chat("查看CPU使用率")                           │
│   ↓                                                         │
│ Client.send_message(MessageType.CHAT_TEXT, data)            │
│   ↓                                                         │
│ NPLTMessage.encode(): Type=0x01, Seq=0, Data=...            │
│   ↓                                                         │
│ writer.write(encoded) → TCP 发送                            │
└──────────────────────────────────────────────────────────────┘
   ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. 服务器接收并处理消息                                      │
├──────────────────────────────────────────────────────────────┤
│ Server._process_message(session, message)                   │
│   ↓                                                         │
│ 识别消息类型: CHAT_TEXT                                     │
│   ↓                                                         │
│ 检查内容: 不是 "HEARTBEAT"，不是空消息                       │
│   ↓                                                         │
│ 调用 chat_handler (ReActAgent)                             │
│   ↓                                                         │
│ Agent.think_stream(session, user_message)                   │
└──────────────────────────────────────────────────────────────┘
   ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. Agent 处理 - ReAct 循环                                   │
├──────────────────────────────────────────────────────────────┤
│ a) 获取上下文                                                │
│    context = history.get_context(max_turns=5)               │
│                                                               │
│ b) 思考并决定工具                                            │
│    await _send_status("thinking", "正在思考")                │
│    → session.send_message(AGENT_THOUGHT, JSON状态)          │
│    → 客户端显示 Spinner: "正在思考"                         │
│                                                               │
│ c) 解析工具调用                                              │
│    tool_use = _parse_tool_use(thought)                       │
│    → {"name": "sys_monitor", "args": {"metric": "cpu"}}     │
│                                                               │
│ d) 执行工具                                                  │
│    await _send_status("tool_call", "正在调用工具: sys_monitor")│
│    → 客户端更新 Spinner: "正在调用工具: sys_monitor"         │
│    result = sys_monitor.execute(metric="cpu")               │
│    → "CPU使用率: 3.0%, 负载: 0.70/..."                     │
│                                                               │
│ e) 生成最终响应                                              │
│    await _send_status("generating", "正在生成最终回复")      │
│    → 客户端更新 Spinner: "正在生成最终回复"                 │
│    response = llm.chat(tool_result)                         │
│    → "当前CPU使用率为3.0%，系统负载正常..."                │
└──────────────────────────────────────────────────────────────┘
   ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. 服务器发送 Agent 响应                                     │
├──────────────────────────────────────────────────────────────┤
│ Agent.think_stream() 返回响应                               │
│   ↓                                                         │
│ nplt_server._handle_chat() 调用完成                         │
│   ↓                                                         │
│ session.send_message(MessageType.CHAT_TEXT, response)       │
│   ↓                                                         │
│ NPLTMessage.encode(): Type=0x01, Seq=1, Data=response       │
│   ↓                                                         │
│ writer.write(encoded) → TCP 发送                            │
└──────────────────────────────────────────────────────────────┘
   ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. 客户端接收并显示响应                                      │
├──────────────────────────────────────────────────────────────┤
│ Client.receive_message()                                    │
│   ↓                                                         │
│ 读取头部 (5字节): Type=0x01, Seq=1, Len=XXX                │
│   ↓                                                         │
│ 读取数据: XXX 字节                                          │
│   ↓                                                         │
│ NPLTMessage.decode(full_message)                            │
│   ↓                                                         │
│ Client._process_message(message)                            │
│   ↓                                                         │
│ 识别消息类型: CHAT_TEXT                                     │
│   ↓                                                         │
│ data.decode('utf-8') → "当前CPU使用率为3.0%..."             │
│   ↓                                                         │
│ UI.print_message("assistant", text)                         │
│   ↓                                                         │
│ response_event.set() → 通知主程序响应完成                    │
└──────────────────────────────────────────────────────────────┘
```

### 关键代码位置

**客户端发送**:
- [src/client/nplt_client.py:340-352](../src/client/nplt_client.py#L340-L352)

**服务器接收和处理**:
- [src/server/nplt_server.py:314-350](../src/server/nplt_server.py#L314-L350)

**Agent ReAct循环**:
- [src/server/agent.py:200-290](../src/server/agent.py#L200-L290)

**客户端接收和显示**:
- [src/client/nplt_client.py:242-268](../src/client/nplt_client.py#L242-L268)

---

## 文件传输消息流

### 1. 文件上传（客户端 → 服务器）

```
Client                    Server
  |                         |
  |  1. FILE_METADATA      |
  |-----------------------> |
  |  {"filename": "test.txt", "size": 1024}
  |                         |
  |    [初始化 upload_state]|
  |                         |
  |  2. FILE_DATA (chunk 1) |
  |-----------------------> |
  |  [200 bytes]            |
  |                         |
  |    [追加到 received_data]|
  |                         |
  |  3. FILE_DATA (chunk 2) |
  |-----------------------> |
  |  [200 bytes]            |
  |                         |
  |    [继续追加...]        |
  |                         |
  |  ...                     |
  |                         |
  |  N. FILE_DATA (final)   |
  |-----------------------> |
  |  [remaining bytes]      |
  |                         |
  |    [检查接收完成]       |
  |    [保存文件到]         |
  |    storage/uploads/     |
  |                         |
  |  <--- CHAT_TEXT ------- |
  |  "文件上传成功: test.txt"|
```

**关键代码**:
- 客户端发送元数据: [src/client/nplt_client.py:355-375](../src/client/nplt_client.py#L355-L375)
- 客户端分块发送数据: [src/client/nplt_client.py:377-418](../src/client/nplt_client.py#L377-L418)
- 服务器接收元数据: [src/server/nplt_server.py:446-464](../src/server/nplt_server.py#L446-L464)
- 服务器接收数据: [src/server/nplt_server.py:466-518](../src/server/nplt_server.py#L466-L518)

### 2. 文件下载（Agent工具调用）

**多协议下载流程**:

```
用户: "下载config.yaml"
   ↓
Agent执行: file_download.execute(file_path="/path/config.yaml")
   ↓
┌─────────────────────────────────────────────────────────────┐
│ FileDownloadTool._select_transport_mode()                   │
├─────────────────────────────────────────────────────────────┤
│ if client_type == "cli":                                   │
│     if rdt_server:                                         │
│         return "rdt"  ← 优先使用 RDT (UDP)                 │
│     else:                                                  │
│         return "nplt" ← 降级到 NPLT (TCP)                  │
│ elif client_type == "web":                                 │
│     if http_base_url:                                      │
│         return "http" ← 使用 HTTP                          │
│     else:                                                  │
│         return "nplt" ← 降级到 NPLT (TCP)                  │
└─────────────────────────────────────────────────────────────┘
   ↓
方案 A: RDT 下载（CLI/Desktop优先）
   ↓
Agent → RDTServer.create_session(file_data)
   ↓
生成 download_token
   ↓
Agent返回: "RDT准备就绪，token=xxx"
   ↓
┌─────────────────────────────────────────────────────────────┐
│ Server                                  Client (RDT Client) │
│   |                                        |                │
│   |  ← UDP 连接到 9998 端口               |                │
│   |                                        |                │
│   |  发送数据包 (滑动窗口)                 |                │
│   |  PKT(seq=0, data=...)                  |                │
│   |  PKT(seq=1, data=...)                  |                │
│   |  PKT(seq=2, data=...)                  |                │
│   |                                        |                │
│   |  ← ACK(2)                              |                │
│   |  (滑动窗口)                             |                │
│   |                                        |                │
│   [继续传输...]                            |                │
└─────────────────────────────────────────────────────────────┘

方案 B: HTTP 下载（Web优先）
   ↓
Agent → HTTPServer.create_download_url(file_id)
   ↓
Agent返回: "HTTP下载链接: http://localhost:8080/api/files/download/abc123"
   ↓
┌─────────────────────────────────────────────────────────────┐
│ Client (Browser)                          Server (HTTP)     │
│   |                                        |                │
│   |  GET /api/files/download/abc123      → |                │
│   |                                        |                │
│   |  ← HTTP 200 OK                        |                │
│   |     Content-Type: application/octet-stream            │
│   |     Content-Disposition: attachment; filename="..."   │
│   |     <文件数据>                           |                │
│   |                                        |                │
│   [浏览器下载文件]                         |                │
└─────────────────────────────────────────────────────────────┘
```

---

## 会话管理消息流

### 会话列表请求

```
Client                    Server
  |                         |
  |  SESSION_LIST (0x14)    |
  |-----------------------> |
  |  data: b""              |
  |                         |
  |    [查询 SessionManager]|
  |    [获取所有会话]       |
  |                         |
  |  <--- CHAT_TEXT ------- |
  |  "=== 会话列表 ===      |
  |   1. [abc123] 会话1 (当前)|
  |      消息数: 15         |
  |      最后访问: 2025-12-31 10:00:00|
  |   2. [def456] 会话2      |
  |      消息数: 8          |
  |      ..."
```

**关键代码**: [src/server/nplt_server.py:650-687](../src/server/nplt_server.py#L650-L687)

### 切换会话

```
Client                    Server
  |                         |
  |  SESSION_SWITCH (0x15)  |
  |-----------------------> |
  |  {"session_id": "def456"}|
  |                         |
  |    [SessionManager.     |
  |     switch_session(def456)]|
  |    [ConversationHistory.|
  |     load(def456)]       |
  |    [更新session.        |
  |     conversation_history]|
  |                         |
  |  <--- CHAT_TEXT ------- |
  |  "已切换到会话: 会话2"  |
```

**关键代码**: [src/server/nplt_server.py:689-747](../src/server/nplt_server.py#L689-L747)

---

## 消息格式详解

### 1. 聊天文本消息（CHAT_TEXT）

**格式**: 纯文本

**示例**:
```python
# 用户消息
message = NPLTMessage(
    type=MessageType.CHAT_TEXT,  # 0x01
    seq=0,
    data="查看CPU使用率".encode('utf-8')
)

# 编码后
# 01 00 00 00 0E E6 9F A5 E7 9C 8B 43 50 55 ...
# |  |     |     |           |
# |  |     |     Len = 14    UTF-8数据
# |  |     Seq
# Type
```

### 2. Agent思考消息（AGENT_THOUGHT）

**格式**: JSON状态消息

**示例**:
```python
# 状态消息
status_json = json.dumps({
    "type": "thinking",
    "content": "正在思考 (第 1 轮)"
})

message = NPLTMessage(
    type=MessageType.AGENT_THOUGHT,  # 0x0A
    seq=1,
    data=status_json.encode('utf-8')
)

# 客户端解析后更新Spinner状态
```

**支持的状态类型**:
- `stream_start`: 开始流式输出
- `thinking`: 正在思考
- `tool_call`: 正在调用工具
- `generating`: 正在生成回复

### 3. 文件元数据消息（FILE_METADATA）

**格式**: JSON

**示例**:
```python
metadata = json.dumps({
    "filename": "test.txt",
    "size": 1024
})

message = NPLTMessage(
    type=MessageType.FILE_METADATA,  # 0x0E
    seq=2,
    data=metadata.encode('utf-8')
)
```

### 4. 会话切换消息（SESSION_SWITCH）

**格式**: JSON

**示例**:
```python
request = json.dumps({
    "session_id": "def456-7890-..."
})

message = NPLTMessage(
    type=MessageType.SESSION_SWITCH,  # 0x15
    seq=3,
    data=request.encode('utf-8')
)
```

### 5. 历史记录消息（HISTORY_REQUEST + CHAT_TEXT响应）

**当前格式**: 纯文本（❌ 丢失结构化数据）

**示例**:
```python
# 请求（客户端发送）
message = NPLTMessage(
    type=MessageType.HISTORY_REQUEST,  # 0x10
    seq=4,
    data=b""  # 空数据
)

# 响应（服务器返回）- 当前实现
history_text = """
=== 对话历史 ===

用户: 查看CPU使用率

助手: 当前CPU使用率为3.0%
"""

message = NPLTMessage(
    type=MessageType.CHAT_TEXT,  # 0x01
    seq=5,
    data=history_text.encode('utf-8')
)
```

**问题**:
- ❌ 丢失了 `tool_calls`（工具调用详情）
- ❌ 丢失了 `timestamp`（时间戳）
- ❌ 丢失了 `metadata`（元数据）

**推荐改进**: 使用JSON格式
```python
history_data = {
    "session_id": session.session_id,
    "messages": [
        {
            "role": "user",
            "content": "查看CPU使用率",
            "timestamp": "2025-12-31T10:00:00"
        },
        {
            "role": "assistant",
            "content": "当前CPU使用率为3.0%",
            "timestamp": "2025-12-31T10:00:02",
            "tool_calls": [
                {
                    "tool_name": "sys_monitor",
                    "arguments": {"metric": "cpu"},
                    "result": "CPU使用率: 3.0%",
                    "status": "success",
                    "duration": 0.5
                }
            ]
        }
    ]
}

message = NPLTMessage(
    type=MessageType.CHAT_TEXT,
    seq=5,
    data=json.dumps(history_data).encode('utf-8')
)
```

---

## 流式输出机制

### 流式输出触发

**代码**: [src/client/nplt_client.py:273-303](../src/client/nplt_client.py#L273-L303)

```python
# 客户端接收 AGENT_THOUGHT 消息
if message.type == MessageType.AGENT_THOUGHT:
    text = message.data.decode('utf-8')
    status_data = json.loads(text)
    status_type = status_data.get("type")

    if status_type == "stream_start":
        # 开始流式输出
        self.ui.start_live_display()
        self.is_streaming = True
```

### 流式输出流程

```
Server                    Client
  |                         |
  |  AGENT_THOUGHT          |
  |  {"type": "stream_start"}|
  |-----------------------> |
  |                         |
  |    [启动 live_display]  |
  |    [is_streaming = True]|
  |                         |
  |  CHAT_TEXT (chunk 1)    |
  | "当前"                  |
  |-----------------------> |
  |                         |
  |    [stream_content("当前")]|
  |    [实时显示]           |
  |                         |
  |  CHAT_TEXT (chunk 2)    |
  | "CPU使用率"             |
  |-----------------------> |
  |                         |
  |    [stream_content("CPU使用率")]|
  |    [追加显示]           |
  |                         |
  |  ...                     |
  |                         |
  |  CHAT_TEXT (空消息)      |
  |  b""                    |
  |-----------------------> |
  |                         |
  |    [stop_live_display()] |
  |    [is_streaming = False]|
  |    [response_event.set()]|
```

**关键点**:
1. 空消息（`data=b""`）标记流式输出结束
2. 客户端渐进式显示内容（类似ChatGPT打字效果）
3. `response_event.set()` 通知主程序响应完成

---

## 心跳机制

### 心跳流程

```
Server (心跳检查任务)
  |
  |  每 90 秒检查一次
  |
  |  如果 elapsed >= 90s
  |     发送心跳
  ↓
Server                    Client
  |                         |
  |  CHAT_TEXT              |
  |  "HEARTBEAT"            |
  |-----------------------> |
  |                         |
  |    [更新 last_heartbeat]|
  |    [不显示任何输出]      |
  |                         |
  |  (客户端也可主动发送心跳)|
  |  <-------------------   |
```

**超时检测**:
- 服务器每30秒检查一次会话超时
- 如果 `elapsed > 90秒`，关闭连接
- 超时时间: `Session.HEARTBEAT_TIMEOUT = 90`

**关键代码**:
- 心跳发送: [src/server/nplt_server.py:402-425](../src/server/nplt_server.py#L402-L425)
- 超时检测: [src/server/nplt_server.py:427-444](../src/server/nplt_server.py#L427-L444)

---

## 序列号机制

### 序列号管理

**客户端**:
```python
send_seq: int = 0  # 发送序列号
recv_seq: int = 0  # 接收序列号

async def send_message(self, message_type, data):
    message = NPLTMessage(
        type=message_type,
        seq=self.send_seq,  # 使用当前序列号
        data=data
    )
    self.send_seq = (self.send_seq + 1) % 65536  # 递增（循环）
```

**服务器**:
```python
class Session:
    send_seq: int = 0  # 每个会话独立的发送序列号
    recv_seq: int = 0  # 每个会话独立的接收序列号
```

### 序列号作用

1. **消息去重**: 检测重复消息
2. **乱序处理**: 理论上支持乱序重组（当前未实现）
3. **调试追踪**: 追踪消息流向

---

## 错误处理

### 连接错误

**客户端**:
```python
try:
    message = await self.receive_message()
except asyncio.TimeoutError:
    await self.send_heartbeat()  # 发送心跳
except Exception as e:
    if "0 bytes read" in str(e):
        # 连接关闭（正常）
        self.connected = False
    else:
        # 网络错误
        self.ui.print_error(f"接收消息失败: {e}")
        self.connected = False
```

### 消息验证

**服务器**:
```python
# 验证消息格式
if not message.validate():
    print(f"[WARN] 无效消息: {message}")
    continue  # 跳过无效消息
```

**验证规则**:
```python
def validate(self) -> bool:
    return (
        0 <= self.seq < 65536 and
        len(self.data) <= 65535
    )
```

---

## 总结

### 消息传递特点

1. **TCP可靠传输**: 基于TCP连接，保证消息可靠到达
2. **二进制协议**: 高效的二进制头部 + 变长数据
3. **双向通信**: 客户端和服务器都可主动发送消息
4. **序列号**: 支持消息追踪和去重
5. **心跳机制**: 保持连接活跃，检测超时
6. **异步处理**: 基于asyncio的异步I/O

### 数据格式总结

| 消息类型 | 数据格式 | 结构化 | 用途 |
|---------|---------|-------|------|
| **CHAT_TEXT** | 纯文本 | ❌ | 用户消息、Agent响应、心跳 |
| **AGENT_THOUGHT** | JSON | ✅ | Agent状态更新 |
| **FILE_METADATA** | JSON | ✅ | 文件上传元数据 |
| **FILE_DATA** | 二进制 | N/A | 文件数据块 |
| **DOWNLOAD_OFFER** | JSON | ✅ | 文件下载提议 |
| **SESSION_SWITCH** | JSON | ✅ | 会话切换请求 |
| **HISTORY_REQUEST** | 空或JSON | - | 历史记录请求 |
| **HISTORY响应** | 文本（❌）→ JSON（✅） | ✅ | 历史记录数据 |

### 关键发现

**优点**:
- ✅ 协议简洁高效
- ✅ 支持实时流式输出
- ✅ 完整的会话管理
- ✅ 多协议文件传输支持

**需要改进**:
- ⚠️ 历史记录传输使用文本格式，丢失结构化数据（tool_calls, timestamp）
- ⚠️ 缺少消息校验和（可能数据损坏）
- ⚠️ 流式输出机制依赖特殊标记（空消息），不够明确

---

**文档版本**: v1.0
**最后更新**: 2025-12-31
**作者**: Claude Sonnet 4.5
