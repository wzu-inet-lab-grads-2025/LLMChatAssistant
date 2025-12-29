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

**描述**: 客户端与服务器的一次连接会话（TCP 连接层）

```python
@dataclass
class Session:
    """客户端会话（TCP 连接层）"""
    session_id: str              # 会话唯一标识 (UUID)
    client_addr: Tuple[str, int] # 客户端地址 (IP, Port)
    connected_at: datetime       # 连接时间
    last_heartbeat: datetime     # 最后心跳时间
    state: SessionState          # 会话状态
    message_queue: asyncio.Queue # 消息队列
    conversation_session_id: str | None = None  # 关联的对话会话 ID

    def is_timeout(self, timeout: int = 90) -> bool:
        """检查是否超时"""
        return (datetime.now() - self.last_heartbeat).seconds > timeout
```

**关系**:
- 包含多个 Message
- 关联一个 ConversationSession（对话会话）

**验证规则**:
- `session_id` 必须是有效的 UUID 格式
- `connected_at` <= `last_heartbeat`
- 心跳超时时间: 90 秒

### 3.1. ConversationSession (对话会话)

**描述**: 用户的多会话管理实体（持久化对话会话）

```python
@dataclass
class ConversationSession:
    """对话会话（多会话管理）"""
    session_id: str               # 会话唯一标识 (UUID)
    name: str                     # 会话名称（AI 自动生成或用户手动设置）
    created_at: datetime          # 创建时间
    updated_at: datetime          # 最后更新时间
    last_accessed: datetime       # 最后访问时间
    message_count: int            # 消息数量
    archived: bool = False        # 是否已归档
    archive_path: str | None = None  # 归档文件路径（如果已归档）

    def should_archive(self, days: int = 30) -> bool:
        """检查是否应该归档"""
        if self.archived:
            return False
        days_since_access = (datetime.now() - self.last_accessed).days
        return days_since_access >= days

    def generate_default_name(self) -> str:
        """生成默认名称"""
        return self.created_at.strftime("%Y-%m-%d %H:%M")
```

**关系**:
- 包含一个 ConversationHistory
- 被多个 Session（TCP 连接）关联

**验证规则**:
- `session_id` 必须是有效的 UUID 格式
- `name` 不能为空（默认基于时间生成）
- `created_at` <= `updated_at` <= `last_accessed`
- `message_count` >= 0
- 归档策略：超过 30 天未访问自动归档

**会话命名策略**:
- 默认名称：创建时间（如 "2025-12-29 10:30"）
- AI 自动命名：在第 3 轮对话后，使用 LLM 分析对话主题生成名称
- 手动重命名：未来支持用户自定义名称

### 3.2. SessionManager (会话管理器)

**描述**: 多会话管理核心组件

```python
@dataclass
class SessionManager:
    """会话管理器"""
    sessions: Dict[str, ConversationSession]  # 活跃会话
    current_session_id: str | None = None     # 当前活跃会话 ID
    storage_dir: str = "storage/history"      # 存储目录
    archive_dir: str = "storage/history/archive"  # 归档目录
    llm_provider: LLMProvider | None = None   # LLM Provider（用于自动命名）

    def create_session(self) -> str:
        """创建新会话

        Returns:
            会话 ID
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        session = ConversationSession(
            session_id=session_id,
            name=now.strftime("%Y-%m-%d %H:%M"),
            created_at=now,
            updated_at=now,
            last_accessed=now,
            message_count=0
        )
        self.sessions[session_id] = session
        self.current_session_id = session_id
        return session_id

    def switch_session(self, session_id: str) -> bool:
        """切换会话

        Args:
            session_id: 目标会话 ID

        Returns:
            是否切换成功
        """
        if session_id not in self.sessions:
            return False
        self.current_session_id = session_id
        self.sessions[session_id].last_accessed = datetime.now()
        return True

    def list_sessions(self) -> List[SessionInfo]:
        """列出所有会话

        Returns:
            会话信息列表
        """
        return [
            SessionInfo(
                session_id=s.session_id,
                name=s.name,
                message_count=s.message_count,
                last_accessed=s.last_accessed,
                is_current=(s.session_id == self.current_session_id)
            )
            for s in self.sessions.values()
        ]

    def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 要删除的会话 ID

        Returns:
            是否删除成功
        """
        if session_id not in self.sessions:
            return False
        del self.sessions[session_id]
        if self.current_session_id == session_id:
            self.current_session_id = None
        return True

    def auto_name_session(self, session_id: str, conversation_history: ConversationHistory):
        """AI 自动命名会话

        Args:
            session_id: 会话 ID
            conversation_history: 对话历史

        在第 3 轮对话后自动调用
        """
        if session_id not in self.sessions:
            return

        if not self.llm_provider:
            return

        # 获取前几轮对话
        context = conversation_history.get_context(max_turns=3)
        if len(context) < 4:  # 至少 2 轮对话
            return

        # 构建 LLM 提示
        messages = [
            {"role": "system", "content": "你是一个会话命名助手。根据对话内容，生成一个简洁的会话名称（不超过 10 个字）。仅返回名称，不要其他内容。"},
            {"role": "user", "content": "\n".join([m.content for m in context])}
        ]

        try:
            name = self.llm_provider.chat(messages=messages, temperature=0.5).strip()
            if len(name) > 20:
                name = name[:20] + "..."
            self.sessions[session_id].name = name
            self.sessions[session_id].updated_at = datetime.now()
        except Exception:
            pass  # 保持默认名称

    def archive_old_sessions(self, days: int = 30) -> int:
        """归档旧会话

        Args:
            days: 归档天数阈值

        Returns:
            归档的会话数量
        """
        to_archive = [
            s for s in self.sessions.values()
            if s.should_archive(days)
        ]

        for session in to_archive:
            self._archive_session(session)

        return len(to_archive)

    def _archive_session(self, session: ConversationSession):
        """归档单个会话

        Args:
            session: 要归档的会话
        """
        archive_month = session.created_at.strftime("%Y-%m")
        archive_dir = os.path.join(self.archive_dir, archive_month)
        os.makedirs(archive_dir, exist_ok=True)

        # 移动会话文件
        src_path = os.path.join(self.storage_dir, f"session_{session.created_at.strftime('%Y%m%d')}_{session.session_id[:8]}.json")
        dst_path = os.path.join(archive_dir, os.path.basename(src_path))

        if os.path.exists(src_path):
            os.rename(src_path, dst_path)
            session.archived = True
            session.archive_path = dst_path

        # 从活跃会话中移除
        del self.sessions[session.session_id]
```

**关系**:
- 管理多个 ConversationSession
- 使用 LLMProvider 生成会话名称
- 协调 ConversationHistory 的加载和保存

**验证规则**:
- `current_session_id` 必须在 `sessions` 中（或为 None）
- 归档目录按月组织（格式：YYYY-MM）
- 归档后的会话从活跃会话中移除

### 3.3. SessionInfo (会话信息)

**描述**: 会话列表显示信息

```python
@dataclass
class SessionInfo:
    """会话信息（用于会话列表显示）"""
    session_id: str          # 会话 ID
    name: str                # 会话名称
    message_count: int       # 消息数量
    last_accessed: datetime  # 最后访问时间
    is_current: bool         # 是否为当前会话
```

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
# TCP 连接层
Session (1) ----< (N) Message
  |
  +---- (1) ConversationSession  # 关联持久化对话会话

# 多会话管理层
SessionManager ----< (N) ConversationSession
                        |
                        +---- (1) ConversationHistory
                                  |
                                  +---- (N) ChatMessage
                                           |
                                           +---- (N) ToolCall

# 文件与检索层
UploadedFile (1) ---- (1) VectorIndex
  |
  +---- (N) Chunk

# 文件传输层
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
│   ├── session_20251228_abc123.json  # 活跃会话
│   │   {
│     "session_id": "...",
│     "name": "系统监控",
│     "messages": [
│       {"role": "user", "content": "...", "timestamp": "..."},
│       {"role": "assistant", "content": "...", "timestamp": "..."}
│     ],
│     "created_at": "...",
│     "updated_at": "...",
│     "message_count": 15
│   }
│   └── session_20251229_def456.json
├── archive/
│   ├── 2024-12/               # 按月归档
│   │   ├── session_20241101_xxx.json
│   │   └── session_20241115_yyy.json
│   └── 2025-01/
│       └── session_20250105_zzz.json
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
