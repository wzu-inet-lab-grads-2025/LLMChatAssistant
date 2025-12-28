# 数据模型: 智能网络运维助手

**功能**: 001-llm-chat-assistant | **日期**: 2025-12-28

## 概述

本文档定义智能网络运维助手系统的核心实体、属性、关系和验证规则。

## 核心实体

### 1. Message (消息)

**描述**: 客户端与服务器之间传输的 NPLT 协议消息

```python
@dataclass
class Message:
    """NPLT 协议消息"""
    type: MessageType          # 消息类型 (1B)
    seq: int                   # 序列号 (2B, 0-65535)
    data: bytes                # 消息数据 (<=255B)
    checksum: int | None = None  # 校验和（可选）

    def validate(self) -> bool:
        """验证消息格式"""
        return len(self.data) <= 255 and 0 <= self.seq < 65536
```

**关系**:
- 属于一个 Session（会话）
- 可以被序列化为字节流发送

**验证规则**:
- `seq` 必须在 0-65535 范围内
- `data` 长度 <= 255 字节
- `type` 必须是有效的 MessageType 枚举值

### 2. MessageType (消息类型)

**描述**: NPLT 协议支持的消息类型

```python
class MessageType(IntEnum):
    """NPLT 消息类型"""
    CHAT_TEXT = 0x01         # 聊天文本
    AGENT_THOUGHT = 0x0A     # Agent 思考过程
    DOWNLOAD_OFFER = 0x0C    # 文件下载提议
```

### 3. Session (会话)

**描述**: 客户端与服务器的一次连接会话

```python
@dataclass
class Session:
    """客户端会话"""
    session_id: str              # 会话唯一标识 (UUID)
    client_addr: Tuple[str, int] # 客户端地址 (IP, Port)
    connected_at: datetime       # 连接时间
    last_heartbeat: datetime     # 最后心跳时间
    state: SessionState          # 会话状态
    message_queue: asyncio.Queue # 消息队列

    def is_timeout(self, timeout: int = 90) -> bool:
        """检查是否超时"""
        return (datetime.now() - self.last_heartbeat).seconds > timeout
```

**关系**:
- 包含多个 Message
- 关联一个 ConversationHistory

**验证规则**:
- `session_id` 必须是有效的 UUID 格式
- `connected_at` <= `last_heartbeat`
- 心跳超时时间: 90 秒

### 4. SessionState (会话状态)

**描述**: 会话生命周期状态

```python
class SessionState(Enum):
    """会话状态"""
    CONNECTING = "connecting"     # 连接中
    ACTIVE = "active"            # 活跃
    IDLE = "idle"               # 空闲
    DISCONNECTED = "disconnected" # 已断开
    ERROR = "error"             # 错误
```

**状态转换**:

```
CONNECTING -> ACTIVE -> IDLE -> ACTIVE -> ...
    |          |         |
    v          v         v
DISCONNECTED  ERROR   DISCONNECTED
```

### 5. ConversationHistory (对话历史)

**描述**: 单用户的对话历史记录

```python
@dataclass
class ConversationHistory:
    """对话历史"""
    session_id: str               # 会话 ID
    messages: List[ChatMessage]   # 消息列表
    created_at: datetime          # 创建时间
    updated_at: datetime          # 更新时间

    def add_message(self, role: str, content: str):
        """添加消息"""
        self.messages.append(ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now()
        ))
        self.updated_at = datetime.now()

    def get_context(self, max_turns: int = 10) -> List[ChatMessage]:
        """获取最近 N 轮对话作为上下文"""
        return self.messages[-max_turns*2:]
```

**关系**:
- 属于一个 Session
- 包含多个 ChatMessage
- 持久化到 `storage/history/session_{date}.json`

**验证规则**:
- `messages` 列表按时间戳升序排列
- 消息成对出现（用户消息后跟 AI 回复）

### 6. ChatMessage (聊天消息)

**描述**: 对话中的一条消息

```python
@dataclass
class ChatMessage:
    """聊天消息"""
    role: Literal["user", "assistant", "system"]  # 角色
    content: str                      # 消息内容
    timestamp: datetime                # 时间戳
    tool_calls: List[ToolCall] = None  # 工具调用（可选）
    metadata: dict = None              # 元数据（可选）
```

**关系**:
- 属于一个 ConversationHistory
- 可能包含多个 ToolCall

### 7. ToolCall (工具调用)

**描述**: Agent 调用的工具执行记录

```python
@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str          # 工具名称
    arguments: dict         # 工具参数
    result: str             # 执行结果
    status: ToolCallStatus  # 执行状态
    duration: float         # 执行时长（秒）
    timestamp: datetime     # 调用时间

    def is_timeout(self, timeout: int = 5) -> bool:
        """检查是否超时"""
        return self.duration > timeout
```

**关系**:
- 属于一个 ChatMessage
- 关联一个具体的 Tool 实现

**验证规则**:
- `tool_name` 必须在工具白名单中
- `duration` >= 0
- 超时时间: 5 秒

### 8. ToolCallStatus (工具调用状态)

```python
class ToolCallStatus(Enum):
    """工具调用状态"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 执行中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    TIMEOUT = "timeout"       # 超时
```

### 9. VectorIndex (向量索引)

**描述**: 上传文件的向量索引

```python
@dataclass
class VectorIndex:
    """向量索引"""
    file_id: str                    # 文件唯一标识
    filename: str                   # 文件名
    chunks: List[str]               # 文本分块
    embeddings: List[List[float]]   # 嵌入向量
    chunk_metadata: List[dict]      # 分块元数据
    created_at: datetime            # 创建时间

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[SearchResult]:
        """向量检索"""
        similarities = [
            cosine_similarity(query_embedding, emb)
            for emb in self.embeddings
        ]
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [
            SearchResult(
                chunk=self.chunks[i],
                similarity=similarities[i],
                metadata=self.chunk_metadata[i]
            )
            for i in top_indices if similarities[i] >= 0.3
        ]
```

**关系**:
- 关联一个 UploadedFile
- 包含多个 Chunk

**验证规则**:
- `chunks` 和 `embeddings` 长度必须相等
- 每个 embedding 向量维度相同（embedding-3-pro: 3072 维）
- 相似度阈值: 0.3

### 10. UploadedFile (上传文件)

**描述**: 用户上传的文件元数据

```python
@dataclass
class UploadedFile:
    """上传文件"""
    file_id: str          # 文件唯一标识 (UUID)
    filename: str         # 原始文件名
    size: int             # 文件大小（字节）
    content_type: str     # 内容类型 (text/plain, etc.)
    storage_path: str     # 存储路径
    uploaded_at: datetime # 上传时间
    vector_index_id: str | None = None  # 关联的向量索引 ID

    def validate_size(self, max_size: int = 10 * 1024 * 1024) -> bool:
        """验证文件大小"""
        return self.size <= max_size
```

**关系**:
- 关联一个 VectorIndex（如果已索引）
- 存储在 `storage/uploads/{file_id}/{filename}`

**验证规则**:
- `size` <= 10MB (10 * 1024 * 1024 字节)
- `content_type` 必须是纯文本类型
- `filename` 不能包含路径遍历字符 (`../`)

### 11. SearchResult (检索结果)

**描述**: 向量检索结果

```python
@dataclass
class SearchResult:
    """检索结果"""
    chunk: str              # 匹配的文本片段
    similarity: float       # 相似度 (0-1)
    metadata: dict          # 元数据（文件名、位置等）
```

### 12. RDTPacket (RDT 数据包)

**描述**: RDT 协议的 UDP 数据包

```python
@dataclass
class RDTPacket:
    """RDT 数据包"""
    seq: int          # 序列号 (2B, 0-65535)
    checksum: int     # 校验和 (2B)
    data: bytes       # 数据 (<=1024B)

    def compute_checksum(self) -> int:
        """计算校验和（CRC16）"""
        return crc16(self.data)

    def validate(self) -> bool:
        """验证数据包"""
        return self.checksum == self.compute_checksum() and len(self.data) <= 1024
```

**验证规则**:
- `seq` 必须在 0-65535 范围内
- `data` 长度 <= 1024 字节
- `checksum` 必须匹配计算值

### 13. RDTSession (RDT 传输会话)

**描述**: UDP 文件传输会话

```python
@dataclass
class RDTSession:
    """RDT 传输会话"""
    session_id: str          # 会话 ID
    filename: str            # 文件名
    file_size: int           # 文件大小
    download_token: str      # 下载令牌
    state: RDTState          # 传输状态
    window_size: int = 5     # 滑动窗口大小
    send_base: int = 0       # 发送基序列号
    next_seq: int = 0        # 下一个序列号
    packets: Dict[int, RDTPacket] = field(default_factory=dict)  # 已发送包
    acked_packets: Set[int] = field(default_factory=set)  # 已确认包
    timeout_start: float | None = None  # 超时计时起点

    def can_send(self) -> bool:
        """检查是否可以发送新包"""
        return self.next_seq < self.send_base + self.window_size

    def is_complete(self) -> bool:
        """检查传输是否完成"""
        return len(self.acked_packets) >= math.ceil(self.file_size / 1024)
```

**关系**:
- 关联一个 Session
- 包含多个 RDTPacket

**验证规则**:
- `window_size` = 5
- 每个数据包大小 <= 1024 字节
- 超时时间: 100ms

### 14. RDTState (RDT 传输状态)

```python
class RDTState(Enum):
    """RDT 传输状态"""
    IDLE = "idle"               # 空闲
    WAITING_OFFER = "waiting_offer"  # 等待下载提议
    WAITING_ACK = "waiting_ack"    # 等待确认
    SENDING = "sending"        # 发送中
    RECEIVING = "receiving"    # 接收中
    COMPLETED = "completed"    # 完成
    FAILED = "failed"          # 失败
```

## 配置模型

### 15. LLMConfig (LLM 配置)

**描述**: LLM Provider 配置

```python
@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str              # Provider 名称 (zhipu)
    api_key: str               # API 密钥
    chat_model: str            # 聊天模型 (glm-4-flash, glm-4.5-flash)
    embed_model: str           # 嵌入模型 (embedding-3-pro)
    temperature: float = 0.7   # 温度参数
    max_tokens: int = 2000     # 最大 token 数
    timeout: int = 30          # 请求超时（秒）

    def validate(self) -> bool:
        """验证配置"""
        return bool(self.api_key) and self.temperature >= 0 and self.temperature <= 1
```

**验证规则**:
- `api_key` 不能为空
- `temperature` 在 0-1 范围内
- `chat_model` 必须是支持的后端（glm-4-flash、glm-4.5-flash）
- `embed_model` 必须是 embedding-3-pro

### 16. ServerConfig (服务器配置)

**描述**: 服务器配置

```python
@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 9999
    max_clients: int = 10
    heartbeat_interval: int = 90  # 心跳间隔（秒）
    storage_dir: str = "storage"
    logs_dir: str = "logs"
    log_level: str = "INFO"
```

**验证规则**:
- `port` 在 1024-65535 范围内
- `max_clients` > 0
- `heartbeat_interval` > 0

### 17. AppConfig (应用配置)

**描述**: 从 config.yaml 和 .env 加载的应用配置

```python
@dataclass
class AppConfig:
    """应用配置（从 config.yaml 和 .env 加载）"""
    server: ServerConfig
    llm: LLMConfig

    # 配置文件路径
    config_file: str = "config.yaml"  # 项目根目录
    env_file: str = ".env"            # 项目根目录

    # 配置优先级
    priority: list = field(default_factory=lambda: ["cli", "env", "file"])

    @classmethod
    def load(cls, config_file: str = "config.yaml", env_file: str = ".env") -> 'AppConfig':
        """从 config.yaml 和 .env 加载配置

        加载优先级：命令行参数 > 环境变量 > config.yaml
        """
        # 1. 加载 .env 文件
        from dotenv import load_dotenv
        load_dotenv(env_file)

        # 2. 读取 config.yaml
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # 3. 解析配置
        server_config = ServerConfig(**config_data.get('server', {}))

        # 4. LLM 配置：API key 从环境变量读取
        llm_config_data = config_data.get('llm', {})
        api_key = os.getenv('ZHIPU_API_KEY')
        if not api_key:
            raise ValueError("ZHIPU_API_KEY 环境变量未配置")

        llm_config = LLMConfig(
            provider="zhipu",
            api_key=api_key,
            **llm_config_data
        )

        return cls(
            server=server_config,
            llm=llm_config,
            config_file=config_file,
            env_file=env_file
        )

    def validate(self) -> bool:
        """验证配置有效性"""
        return (
            self.server.port >= 1024 and self.server.port <= 65535 and
            self.server.max_clients > 0 and
            self.llm.validate()
        )
```

**关系**:
- 包含 ServerConfig
- 包含 LLMConfig
- 从项目根目录加载配置文件

**验证规则**:
- `config_file` 必须存在且是有效的 YAML 文件
- `env_file` 如果不存在，仅警告（API key 可从环境变量获取）
- 所有子配置必须通过各自的 `validate()` 方法

## 辅助数据结构

### 17. ToolExecutionResult (工具执行结果)

```python
@dataclass
class ToolExecutionResult:
    """工具执行结果"""
    success: bool           # 是否成功
    output: str             # 输出内容
    error: str | None = None  # 错误信息
    duration: float = 0     # 执行时长
```

### 18. FileTransferOffer (文件传输提议)

```python
@dataclass
class FileTransferOffer:
    """文件传输提议"""
    token: str              # 传输令牌
    filename: str           # 文件名
    size: int               # 文件大小
    checksum: str           # 文件校验和
    expires_at: datetime    # 过期时间
```

## 关系图

```
Session (1) ----< (N) Message
  |
  +---- (1) ConversationHistory
            |
            +---- (N) ChatMessage
                     |
                     +---- (N) ToolCall

UploadedFile (1) ---- (1) VectorIndex
  |
  +---- (N) Chunk

Session (1) ---- (1) RDTSession
  |
  +---- (N) RDTPacket
```

## 数据持久化

### 文件系统结构

```
storage/
├── vectors/
│   ├── index.json              # 向量索引目录
│   │   {"file_id": "vector_file.json"}
│   └── {file_id}.json          # 具体向量数据
│       {
│         "filename": "config.yaml",
│         "chunks": ["文本1", "文本2"],
│         "embeddings": [[0.1, 0.2, ...], ...],
│         "metadata": [...]
│       }
├── history/
│   ├── current.json            # 当前会话历史
│   │   {
│     "session_id": "...",
│     "messages": [
│       {"role": "user", "content": "...", "timestamp": "..."},
│       {"role": "assistant", "content": "...", "timestamp": "..."}
│     ]
│   }
│   └── session_{date}.json     # 历史会话
└── uploads/
    └── {file_id}/
        └── {original_filename}  # 原始文件
```

### 加载策略

- **向量索引**: 服务器启动时加载所有索引到内存
- **对话历史**: 按需加载，当前会话常驻内存
- **上传文件**: 按需读取

## 验证规则汇总

| 实体 | 字段 | 规则 |
|------|------|------|
| Message | data | 长度 <= 255B |
| Message | seq | 0 <= seq < 65536 |
| Session | last_heartbeat | 距离现在 <= 90s |
| UploadedFile | size | <= 10MB (10485760 B) |
| UploadedFile | filename | 不包含 `../` |
| RDTPacket | data | 长度 <= 1024B |
| RDTPacket | seq | 0 <= seq < 65536 |
| LLMConfig | temperature | 0 <= temperature <= 1 |
| ServerConfig | port | 1024 <= port <= 65535 |

## 扩展性考虑

### 未来可能添加的实体

1. **User (用户)**: 如果扩展到多用户场景
2. **ScheduledTask (定时任务)**: 如果支持定时运维任务
3. **Alert (告警)**: 如果支持系统告警
4. **Notification (通知)**: 如果支持主动通知

### 扩展点

- LLM Provider: 添加 OpenAI、Claude 实现
- Tool: 添加新的运维工具（日志分析、性能监控等）
- Storage: 添加数据库后端（PostgreSQL、MongoDB）
- Protocol: 添加 WebSocket 支持
