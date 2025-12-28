# 研究文档: 智能网络运维助手

**功能**: 001-llm-chat-assistant | **日期**: 2025-12-28

## 概述

本文档记录智能网络运维助手的技术选择、最佳实践和设计决策研究。

## 技术选择研究

### 1. 异步网络框架: asyncio

**决策**: 使用 Python 标准库 `asyncio` 而非第三方框架（如 Trio、Curio）

**理由**:
- asyncio 是 Python 3.11 标准库的一部分，无需额外依赖
- 完善的 TCP/UDP 协议支持（`asyncio.start_server`、`DatagramProtocol`）
- 与 Rich 库的异步渲染良好兼容
- 社区成熟，文档完善

**替代方案考虑**:
- **Trio**: 更简洁的 API，但生态系统较小，需要额外依赖
- **Curio**: 更简单的并发模型，但维护不活跃

### 2. CLI UI 库: Rich

**决策**: 使用 Rich 库实现终端 UI

**理由**:
- 提供丰富的组件（Progress、Spinner、Markdown 渲染、Syntax 高亮）
- 支持实时更新和动画效果
- 良好的异步兼容性
- 中文显示支持良好

**替代方案考虑**:
- **Textual**: Rich 的升级版，但过于重量级，且需要终端支持高级特性
- **Click**: 专注于命令行参数解析，不适合沉浸式 UI
- **Prompt Toolkit**: 功能强大但 API 复杂，学习曲线陡峭

### 3. 向量存储: 文件系统 + NumPy

**决策**: 使用 NumPy 数组存储向量，持久化到文件系统

**理由**:
- 满足单用户场景需求
- 无需额外的数据库依赖
- NumPy 提供高效的向量计算（余弦相似度）
- 简单的序列化/反序列化（pickle 或 JSON）

**替代方案考虑**:
- **ChromaDB**: 功能完善但过度设计，需要额外依赖
- **FAISS**: 性能强大但需要编译，部署复杂
- **SQLite + sqlite-vss**: 轻量级，但向量检索性能不如内存计算

### 4. LLM Provider 抽象设计

**决策**: 定义抽象接口 `LLMProvider`，智谱作为第一个实现

**接口设计**:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Message], model: str, stream: bool = True) -> AsyncIterator[str]:
        """聊天接口，支持流式输出"""
        pass

    @abstractmethod
    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        """向量嵌入接口"""
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """验证 API key 有效性"""
        pass
```

**理由**:
- 符合开闭原则，方便扩展其他 provider（OpenAI、Claude）
- 统一的异步接口，适合网络 I/O 密集型场景
- 清晰的抽象边界，降低耦合度

**替代方案考虑**:
- **配置驱动的条件分支**: 简单但难以维护，违反开闭原则
- **LangChain**: 功能强大但过度设计，增加不必要的学习成本

### 5. TCP 长连接协议设计: NPLT

**决策**: 自定义简单的应用层协议 NPLT (Network Protocol for LLM Transport)

**协议格式**:

```
+-----+------+------+-------+
| Type| Seq  | Len  | Data  |
| 1B  | 2B   | 1B   | <=255B|
+-----+------+------+-------+
```

**消息类型**:
- `0x01` CHAT_TEXT: 聊天文本
- `0x0A` AGENT_THOUGHT: Agent 思考过程
- `0x0C` DOWNLOAD_OFFER: 文件下载提议

**理由**:
- 简单的二进制协议，易于实现
- 固定头部 + 可变负载，平衡灵活性和性能
- 序列号支持消息排序和丢失检测
- 满足功能需求，无需过度设计

**替代方案考虑**:
- **HTTP/REST**: 通用但 overhead 高，不适合长连接流式传输
- **WebSocket**: 支持双向流，但需要额外的握手和 HTTP 升级
- **gRPC**: 功能完善但复杂度太高，需要 Protobuf 定义

### 6. 配置管理策略: config.yaml + .env

**决策**: 使用分层配置策略，config.yaml 作为主配置文件，.env 存储敏感信息

**配置文件结构**:

```yaml
# config.yaml (项目根目录)
server:
  host: "0.0.0.0"
  port: 9999
  max_clients: 10
  heartbeat_interval: 90

llm:
  model: "glm-4-flash"  # 可被环境变量覆盖
  temperature: 0.7
  max_tokens: 2000
  timeout: 30

storage:
  storage_dir: "storage"
  logs_dir: "storage/logs"

logging:
  level: "INFO"
```

```bash
# .env (项目根目录，不提交到版本控制)
ZHIPU_API_KEY=your_api_key_here
```

**配置优先级**: 命令行参数 > 环境变量 > config.yaml

**理由**:
- 符合 12-factor app 最佳实践
- 敏感信息（API key）与配置分离
- 支持环境变量覆盖，便于不同环境部署
- config.yaml 可提交到版本控制，.env 在 .gitignore 中

**替代方案考虑**:
- **纯环境变量**: 简单但缺乏结构，不易管理
- **JSON 配置**: 不支持注释，可读性差
- **INI 配置**: 缺乏层次结构，不适合复杂配置

**实施细节**:
- 使用 PyYAML 解析 config.yaml
- 使用 python-dotenv 加载 .env
- 环境变量引用语法：`${ZHIPU_API_KEY}` 在 config.yaml 中
- 启动时验证配置文件存在且格式正确
- 配置优先级：命令行参数 > 环境变量 > config.yaml

**客户端配置**:
- 客户端使用独立的配置文件（如 config.client.yaml）
- 仅包含连接服务器所需的信息（host、port）

### 7. UDP 可靠传输: RDT 协议

**决策**: 实现基于滑动窗口的 RDT 3.0 协议

**协议格式**:

```
+------+------+--------+
| Seq  | Check| Data   |
| 2B   | 2B   | <=1024B|
+------+------+--------+
```

**关键特性**:
- 滑动窗口大小 N=5
- 超时重传机制（仅对 SendBase 计时）
- 校验和验证数据完整性

**理由**:
- 经典的可靠传输协议，教学价值高
- 平衡可靠性和性能
- 满足运维场景文件传输需求

**替代方案考虑**:
- **TCP**: 可靠但无法满足自定义协议需求
- **QUIC**: 现代但复杂，需要额外库
- **TFTP**: 简单但功能不足

## 最佳实践研究

### 1. ReAct Agent 实现

**模式**: 循环交互（Thought → Action → Observation → Thought）

**实现要点**:
- 最多 5 轮工具调用，避免无限循环
- 工具调用超时控制（5 秒）
- 降级模式：API 失败时切换到本地命令执行

**示例流程**:

```
用户: "帮我检查一下服务器内存"
  ↓
Agent Thought: "需要使用系统监控工具"
  ↓
Action: monitor_tool()
  ↓
Observation: "总内存: 16GB，已使用: 8.5GB (53%)"
  ↓
Response: 格式化结果返回给用户
```

### 2. 安全命令执行

**白名单策略**:

```python
ALLOWED_COMMANDS = {
    'ls', 'cat', 'grep', 'head', 'tail',
    'ps', 'pwd', 'whoami', 'df', 'free'
}
```

**安全措施**:
- 命令黑名单字符过滤（`;`、`&`、`>`、`|`）
- 参数验证（防止路径遍历）
- 使用 `subprocess.run` 而非 `os.system`
- 超时控制（5 秒）

### 3. 向量检索优化

**文本分块策略**:
- 按段落分块（约 500 字）
- 重叠窗口（50 字重叠）保持上下文
- 保留元数据（文件名、位置）

**相似度计算**:
- 余弦相似度
- 返回 Top 3 最相关片段
- 阈值过滤（相似度 < 0.3 不返回）

### 4. 日志与可追溯性

**日志结构**:

```
[2025-12-28 10:30:45] [INFO] [AGENT] 工具调用: monitor_tool
[2025-12-28 10:30:46] [DEBUG] [LLM] 模型: glm-4-flash, tokens: 150
[2025-12-28 10:30:47] [ERROR] [NETWORK] TCP 连接断开: ConnectionResetError
```

**日志配置**:
- 文件位置: `logs/server.log`、`logs/client.log`
- 格式: 纯文本（.log）
- 级别: DEBUG（开发）、INFO（生产）
- 轮转: 每日轮转，保留 7 天

### 5. 存储结构设计

**目录结构**:

```
storage/
├── vectors/             # 向量索引
│   ├── file_123.json    # 文件向量 {"chunks": [...], "embeddings": [[...]]}
│   └── index.json       # 全局索引 {"files": {"file.txt": "file_123.json"}}
├── history/             # 对话历史
│   ├── session_20251228.json  # 会话历史
│   └── current.json           # 当前会话
└── uploads/             # 上传文件
    ├── config.yaml
    └── error.log
```

**持久化策略**:
- 向量数据: 增量更新，服务器启动时加载
- 对话历史: 每次交互后追加
- 上传文件: 原始存储，保留元数据

## 性能优化研究

### 1. 异步并发模型

**客户端**: 单连接 + 异步消息处理
```python
async def handle_messages(reader, writer):
    async for message in reader:
        asyncio.create_task(process_message(message))
```

**服务器**: 每个连接独立任务
```python
async def handle_client(reader, writer):
    async with Session(conn_id) as session:
        async for message in reader:
            await process_message(session, message)
```

### 2. 流式响应优化

**策略**:
- 服务端流式生成（chunk 大小 100 字）
- 客户端实时渲染（Rich Markdown）
- 避免缓冲全部响应

### 3. 向量检索缓存

**策略**:
- LRU 缓存最近查询
- 缓存大小: 100 个查询
- TTL: 10 分钟

## 测试策略研究

### 1. 真实测试要求

**原则**: 不使用 mock，所有测试使用真实 API

**实现**:
- 智谱 API 测试: 需要有效的 API key
- 测试前验证: `pytest` fixture 检查环境变量
- 失败策略: API key 未配置时跳过测试

```python
@pytest.fixture
def zhipu_api_key():
    api_key = os.getenv('ZHIPU_API_KEY')
    if not api_key:
        pytest.skip("ZHIPU_API_KEY 未配置")
    return api_key
```

### 2. 协议测试

**NPLT 协议测试**:
- 正常流程: 发送/接收各类消息
- 边界条件: 最大负载 (255B)、序列号回绕
- 异常场景: 格式错误、未知消息类型

**RDT 协议测试**:
- 正常流程: 完整文件传输
- 丢包模拟: 人工丢弃 10% 数据包
- 超时重传: 模拟网络延迟

### 3. 集成测试场景

**场景 1: 完整对话流程**
1. 启动服务器
2. 客户端连接
3. 发送查询
4. Agent 调用工具
5. 接收响应
6. 断开连接

**场景 2: 文件上传与检索**
1. 上传测试文件
2. 验证向量索引创建
3. 基于文件内容查询
4. 验证检索结果准确性

**场景 3: RDT 文件传输**
1. AI 发送下载提议
2. 客户端确认接收
3. UDP 传输文件
4. 验证文件完整性（校验和）

## 安全性考虑

### 1. 命令注入防护

**措施**:
- 白名单命令
- 黑名单字符过滤
- 参数验证（正则表达式）
- 使用 `shlex.quote` 转义参数

### 2. API 密钥管理

**策略**:
- 环境变量: `ZHIPU_API_KEY`
- 启动验证: 拒绝未配置启动
- 不在日志中记录 API key
- 不在代码中硬编码

### 3. 网络安全

**当前阶段**: 本地可信网络
**未来增强**:
- TLS/SSL 加密（TCP）
- API 认证（Token）
- IP 白名单

## 未解决问题与后续研究

### 1. 对话历史保留策略

**当前状态**: 持久化所有对话
**待决策**:
- 保留期限？（30 天、永久）
- 清理策略？（手动、自动）
- 压缩归档？

**推荐**: 初期保留所有历史，后续根据实际使用情况优化

### 2. 并发客户端管理

**当前状态**: 单用户场景
**未来扩展**:
- 会话隔离（客户端 ID）
- 资源限制（并发数限制）
- 负载均衡

### 3. 大文件处理

**当前限制**: 10MB
**优化方向**:
- 流式 Embedding（边读边处理）
- 分块上传（进度条）
- 压缩存储

## 参考资料

- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html)
- [Rich 库文档](https://rich.readthedocs.io/)
- [智谱 AI API 文档](https://open.bigmodel.cn/dev/api)
- [ReAct Agent 论文](https://arxiv.org/abs/2210.03629)
- [RDT 协议经典实现](https://stanford.edu/class/cs144/)
