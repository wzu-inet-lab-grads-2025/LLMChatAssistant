# 测试合同: 测试全面重构与实现验证

**功能分支**: `001-test-overhaul-validation`
**生成日期**: 2025-12-29
**状态**: 阶段 1 输出

## 概述

本文档定义了测试重构项目的测试合同，包括测试接口规范、前置条件、验收标准和错误处理规范。

## 测试接口规范

### 1. 单元测试接口

#### 1.1 NPLT 协议测试

```python
# test_nplt.py

class TestNPLTEncoding:
    """NPLT 协议编码测试"""

    def test_encode_chat_text_message(self):
        """测试 CHAT_TEXT 消息编码"""
        # 输入：消息类型、序列号、内容
        # 输出：编码后的字节流
        # 验证：符合 NPLT 协议规范
        pass

    def test_encode_agent_thought_message(self):
        """测试 AGENT_THOUGHT 消息编码"""
        pass

    def test_encode_download_offer_message(self):
        """测试 DOWNLOAD_OFFER 消息编码"""
        pass

    def test_decode_message(self):
        """测试消息解码"""
        # 输入：字节流
        # 输出：消息对象
        # 验证：正确解析所有字段
        pass


class TestNPLTValidation:
    """NPLT 协议验证测试"""

    def test_max_payload_size(self):
        """测试最大负载大小（255 字节）"""
        # 验证：超过 255 字节的消息被拒绝
        pass

    def test_invalid_message_type(self):
        """测试无效消息类型处理"""
        # 验证：返回错误并不断开连接
        pass

    def test_checksum_validation(self):
        """测试校验和验证"""
        # 验证：损坏的数据包被检测并拒绝
        pass
```

#### 1.2 RDT 协议测试

```python
# test_rdt.py

class TestRDTSlidingWindow:
    """RDT 滑动窗口测试"""

    def test_window_size(self):
        """测试窗口大小（N=5）"""
        # 验证：窗口大小正确设置为 5
        pass

    def test_window_advancement(self):
        """测试窗口滑动"""
        # 验证：收到 ACK 后窗口正确滑动
        pass

    def test_timeout_retransmission(self):
        """测试超时重传"""
        # 验证：未收到 ACK 时数据包重传
        # 验证：仅对 SendBase 包计时
        pass


class TestRDTReliability:
    """RDT 可靠性测试"""

    def test_packet_loss_recovery(self):
        """测试丢包恢复"""
        # 模拟：10% 丢包率
        # 验证：所有数据包最终成功传输
        pass

    def test_duplicate_acks(self):
        """测试重复 ACK 处理"""
        # 验证：重复 ACK 不导致重复发送
        pass

    def test_max_retransmit_limit(self):
        """测试最大重传次数限制（10 次）"""
        # 验证：超过 10 次后中止传输
        pass
```

#### 1.3 LLM Provider 测试

```python
# test_llm.py

@pytest.mark.requires_api_key
class TestZhipuProvider:
    """智谱 Provider 测试"""

    @pytest.mark.asyncio
    async def test_chat_completion(self, validated_api_key):
        """测试聊天补全"""
        # 输入：消息列表
        # 输出：生成的文本
        # 验证：响应包含相关内容
        pass

    @pytest.mark.asyncio
    async def test_embedding(self, validated_api_key):
        """测试向量嵌入"""
        # 输入：文本列表
        # 输出：向量列表
        # 验证：向量维度正确（1024）
        pass

    def test_model_switching(self, validated_api_key):
        """测试模型切换"""
        # 输入：目标模型（glm-4.5-flash）
        # 验证：模型成功切换
        # 验证：切换失败时保持当前模型
        pass
```

### 2. 集成测试接口

#### 2.1 客户端-服务器通信测试

```python
# test_client_server.py

@pytest.mark.integration
@pytest.mark.requires_api_key
class TestClientServerCommunication:
    """客户端-服务器通信集成测试"""

    @pytest.mark.asyncio
    async def test_tcp_connection(self):
        """测试 TCP 连接建立"""
        # 前置条件：服务器已启动
        # 操作：客户端连接到服务器
        # 验证：连接成功建立
        pass

    @pytest.mark.asyncio
    async def test_chat_message_flow(self):
        """测试聊天消息流程"""
        # 操作：客户端发送聊天消息
        # 验证：服务器接收并处理
        # 验证：客户端接收 AI 回复
        pass

    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self):
        """测试心跳机制"""
        # 操作：客户端发送心跳包
        # 验证：服务器返回心跳响应
        # 验证：超时未心跳时连接断开
        pass
```

#### 2.2 文件上传和 RAG 测试

```python
# test_file_upload.py

@pytest.mark.integration
@pytest.mark.requires_api_key
class TestFileUploadAndRAG:
    """文件上传和 RAG 集成测试"""

    @pytest.mark.asyncio
    async def test_file_upload(self):
        """测试文件上传"""
        # 输入：测试文件（< 10MB）
        # 验证：文件成功上传
        # 验证：进度条正确显示
        pass

    @pytest.mark.asyncio
    async def test_rag_indexing(self):
        """测试 RAG 索引"""
        # 前置条件：文件已上传
        # 验证：向量索引已创建
        # 验证：Embedding 向量正确存储
        pass

    @pytest.mark.asyncio
    async def test_rag_retrieval(self):
        """测试 RAG 检索"""
        # 前置条件：文件已索引
        # 输入：查询问题
        # 验证：返回相关文档片段
        # 验证：语义相关性 > 80%
        pass
```

#### 2.3 会话管理测试

```python
# test_session_management.py

@pytest.mark.integration
class TestSessionManagement:
    """会话管理集成测试"""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """测试创建会话"""
        # 操作：创建新会话
        # 验证：会话 ID 返回
        # 验证：会话持久化到 storage/history/
        pass

    @pytest.mark.asyncio
    async def test_switch_session(self):
        """测试切换会话"""
        # 前置条件：存在多个会话
        # 操作：切换到另一个会话
        # 验证：上下文正确加载
        # 验证：上下文压缩触发（如果消息过多）
        pass

    @pytest.mark.asyncio
    async def test_auto_naming(self):
        """测试自动命名"""
        # 前置条件：新会话已创建
        # 操作：进行 3 轮对话
        # 验证：AI 自动生成会话名称
        pass

    @pytest.mark.asyncio
    async def test_archive_session(self):
        """测试归档会话"""
        # 前置条件：会话超过 30 天未访问
        # 操作：触发归档
        # 验证：会话移动到 storage/history/archive/
        pass
```

### 3. 端到端测试接口

#### 3.1 完整对话流程测试

```python
# test_conversation.py

@pytest.mark.e2e
@pytest.mark.requires_api_key
class TestConversationFlow:
    """完整对话流程测试"""

    @pytest.mark.asyncio
    async def test_simple_conversation(self):
        """测试简单对话流程"""
        # 流程：
        # 1. 启动服务器
        # 2. 启动客户端并连接
        # 3. 发送聊天消息
        # 4. 接收 AI 回复
        # 5. 验证回复相关性
        # 6. 断开连接
        pass

    @pytest.mark.asyncio
    async def test_tool_calling_conversation(self):
        """测试工具调用对话流程"""
        # 流程：
        # 1. 发送需要工具调用的消息（如"检查系统状态"）
        # 2. 验证 AGENT_THOUGHT 消息显示
        # 3. 验证工具执行（如 sys_monitor）
        # 4. 验证最终回复包含工具结果
        pass

    @pytest.mark.asyncio
    async def test_long_conversation(self):
        """测试长对话流程（100+ 轮）"""
        # 流程：
        # 1. 进行 100 轮对话
        # 2. 验证上下文压缩触发
        # 3. 验证对话连贯性保持
        # 4. 验证内存无泄漏
        pass
```

#### 3.2 文件传输流程测试

```python
# test_file_transfer.py

@pytest.mark.e2e
@pytest.mark.requires_api_key
class TestFileTransferFlow:
    """文件传输流程测试"""

    @pytest.mark.asyncio
    async def test_udp_file_transfer(self):
        """测试 UDP 文件传输流程"""
        # 流程：
        # 1. AI 决定发送文件
        # 2. 客户端接收 DOWNLOAD_OFFER
        # 3. 客户端确认接收
        # 4. UDP 传输开始
        # 5. 验证滑动窗口显示
        # 6. 验证传输进度条
        # 7. 验证文件完整性
        pass

    @pytest.mark.asyncio
    async def test_file_transfer_with_packet_loss(self):
        """测试丢包场景下的文件传输"""
        # 流程：
        # 1. 模拟 10% 丢包率
        # 2. 启动文件传输
        # 3. 验证重传机制
        # 4. 验证最终成功传输
        pass
```

#### 3.3 多会话管理流程测试

```python
# test_multi_session.py

@pytest.mark.e2e
@pytest.mark.requires_api_key
class TestMultiSessionFlow:
    """多会话管理流程测试"""

    @pytest.mark.asyncio
    async def test_multi_session_workflow(self):
        """测试多会话工作流"""
        # 流程：
        # 1. 创建会话 A
        # 2. 进行对话
        # 3. 创建会话 B
        # 4. 切换到会话 A
        # 5. 验证上下文正确加载
        # 6. 切换到会话 B
        # 7. 验证上下文隔离
        pass

    @pytest.mark.asyncio
    async def test_session_persistence(self):
        """测试会话持久化"""
        # 流程：
        # 1. 创建会话并对话
        # 2. 关闭客户端
        # 3. 重启客户端
        # 4. 验证会话历史恢复
        # 5. 验证可以继续对话
        pass
```

## 测试前置条件

### 1. 全局前置条件

所有测试运行前必须满足：

1. **Python 环境准备**
   ```bash
   # 检查 Python 版本
   python --version  # 必须是 3.11

   # 激活 uv 虚拟环境
   source .venv/bin/activate  # Linux/macOS
   # 或
   .venv\Scripts\activate  # Windows

   # 验证依赖已安装
   uv pip list
   ```

2. **配置文件准备**
   ```bash
   # 验证 config.yaml 存在
   test -f config.yaml

   # 验证 .env 文件存在
   test -f .env

   # 验证 API key 已设置
   grep ZHIPU_API_KEY .env
   ```

3. **目录结构准备**
   ```bash
   # 验证必需目录存在
   test -d logs
   test -d storage
   test -d storage/vectors
   test -d storage/history
   test -d storage/uploads
   ```

### 2. API 测试前置条件

涉及真实 API 调用的测试必须满足：

1. **API Key 验证**
   ```python
   # API key 格式检查
   assert "." in os.getenv("ZHIPU_API_KEY")

   # API key 功能验证（可选，由测试自动执行）
   # 调用轻量级 embedding API 验证
   ```

2. **网络连接检查**
   ```python
   # 验证可以访问智谱 API
   import socket
   socket.create_connection(("open.bigmodel.cn", 443), timeout=5)
   ```

3. **配额检查**
   ```python
   # 验证账户有可用配额
   # （可选，通过 API 调用检查）
   ```

### 3. 性能测试前置条件

性能测试必须满足：

1. **系统资源检查**
   ```bash
   # 验证 CPU 可用性
   # 验证内存可用性（> 2GB 空闲）
   # 验证磁盘可用性（> 1GB 空闲）
   ```

2. **环境一致性**
   ```bash
   # 关闭其他占用资源的程序
   # 使用相同的网络环境
   # 使用相同的测试数据
   ```

## 测试验收标准

### 1. 功能验收标准

#### 1.1 服务器启动验收

| 验收标准 | 描述 | 验证方法 |
|----------|------|----------|
| SC-SRV-001 | 服务器在 10 秒内完成启动 | 计时 `python -m src.server.main` |
| SC-SRV-002 | 服务器监听在配置的端口 | 检查 `netstat -an | grep 9999` |
| SC-SRV-003 | 配置加载无错误 | 检查日志无配置相关错误 |
| SC-SRV-004 | LLM Provider 初始化成功 | 检查日志显示"LLM Provider 已初始化" |
| SC-SRV-005 | 存储层初始化成功 | 检查 storage/ 目录已创建 |

#### 1.2 测试覆盖验收

| 验收标准 | 描述 | 目标值 |
|----------|------|--------|
| SC-COV-001 | 整体代码覆盖率 | > 90% |
| SC-COV-002 | 核心功能覆盖率 | 100% |
| SC-COV-003 | 协议实现覆盖率 | 100% |
| SC-COV-004 | LLM 集成覆盖率 | > 85% |

#### 1.3 性能验收

| 验收标准 | 描述 | 阈值 |
|----------|------|------|
| SC-PERF-001 | AI 工具调用响应时间 | < 2 秒 |
| SC-PERF-002 | 文件上传进度 | 实时更新 |
| SC-PERF-003 | UDP 文件传输吞吐量（0% 丢包） | > 1 MB/s |
| SC-PERF-004 | UDP 文件传输成功率（10% 丢包） | 100% |
| SC-PERF-005 | 上下文压缩耗时（100 轮对话） | < 50 ms |

### 2. 质量验收标准

#### 2.1 真实性验收

| 验收标准 | 描述 | 验证方法 |
|----------|------|----------|
| SC-QLT-001 | 所有测试使用真实 API | 搜索测试代码无 `mock` 关键字 |
| SC-QLT-002 | 无虚假实现 | 扫描代码无 `pass`/`TODO` 占位符 |
| SC-QLT-003 | 所有功能可演示 | 运行端到端测试成功 |

#### 2.2 稳定性验收

| 验收标准 | 描述 | 验证方法 |
|----------|------|----------|
| SC-STB-001 | 服务器稳定运行 1 小时 | 长时间运行测试 |
| SC-STB-002 | 客户端无内存泄漏 | 长对话测试后内存稳定 |
| SC-STB-003 | 错误处理优雅 | 异常场景有清晰错误消息 |

### 3. 文档验收标准

| 验收标准 | 描述 | 验证方法 |
|----------|------|----------|
| SC-DOC-001 | 所有测试使用中文注释 | 检查测试文件注释 |
| SC-DOC-002 | 错误消息使用中文 | 检查日志和错误提示 |
| SC-DOC-003 | quickstart.md 准确 | 按指南操作成功 |

## 错误处理规范

### 1. 测试失败处理

#### 1.1 失败报告格式

```python
class TestFailureReport:
    """测试失败报告"""

    def generate_failure_report(
        self,
        test_name: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> str:
        """
        生成标准化的失败报告

        格式：
        ========================================
        ❌ 测试失败: {test_name}
        ========================================

        错误类型: {error_type}
        错误消息: {error_message}

        📍 位置:
          文件: {file_path}
          行号: {line_number}
          函数: {function_name}

        📋 上下文:
          {context_details}

        📚 堆栈跟踪:
          {stack_trace}

        💡 修复建议:
          {fix_suggestions}

        ========================================
        """
        pass
```

#### 1.2 常见错误处理

| 错误类型 | 处理方式 | 修复建议 |
|----------|----------|----------|
| `AssertionError` | 记录断言表达式和实际/期望值 | 检查断言逻辑 |
| `ZaiError (401)` | 标记测试跳过，提示 API key 无效 | 检查 API key 配置 |
| `TimeoutError` | 记录超时时间，建议增加超时 | 检查网络连接 |
| `ConnectionError` | 标记测试跳过，提示网络问题 | 检查代理和 VPN |
| `ImportError` | 记录缺失的依赖，建议安装 | 运行 `uv pip install` |

### 2. API 调用失败处理

#### 2.1 失败重试策略

```python
@pytest.fixture
def llm_provider_with_retry(api_key):
    """带重试的 LLM Provider"""

    from tenacity import retry, stop_after_attempt, wait_exponential

    class RetryableZhipuProvider(ZhipuProvider):
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10)
        )
        async def chat_with_retry(self, messages, **kwargs):
            try:
                return await self.chat(messages, **kwargs)
            except ZaiError as e:
                # 记录失败
                logger.warning(f"API 调用失败，重试中: {e}")
                raise

    return RetryableZhipuProvider(api_key=api_key)
```

#### 2.2 降级策略

```python
class APICallStrategy:
    """API 调用策略"""

    async def call_with_fallback(
        self,
        operation: str,
        primary: Callable,
        fallback: Callable,
        *args,
        **kwargs
    ):
        """
        带降级的 API 调用

        Args:
            operation: 操作名称
            primary: 主要方法（真实 API）
            fallback: 降级方法（本地实现）
        """
        try:
            return await primary(*args, **kwargs)
        except ZaiError as e:
            logger.warning(f"{operation} API 调用失败，降级到本地模式: {e}")
            return await fallback(*args, **kwargs)
```

### 3. 配置验证失败处理

```python
class ConfigValidationError(Exception):
    """配置验证错误"""

    def __init__(self, field: str, message: str, fix_suggestion: str):
        self.field = field
        self.message = message
        self.fix_suggestion = fix_suggestion
        super().__init__(f"配置验证失败: {field} - {message}")

    def __str__(self):
        return (
            f"❌ {self.message}\n"
            f"字段: {self.field}\n"
            f"修复建议: {self.fix_suggestion}"
        )


# 使用示例
try:
    validate_config(config)
except ConfigValidationError as e:
    print(e)
    # 输出:
    # ❌ API key 格式无效（应为 id.secret）
    # 字段: llm.api_key
    # 修复建议: 请检查 .env 文件中的 ZHIPU_API_KEY 格式
```

## 总结

本文档定义了测试重构项目的完整测试合同，包括：

1. **测试接口规范**: 单元测试、集成测试、端到端测试接口
2. **测试前置条件**: 全局条件、API 测试条件、性能测试条件
3. **测试验收标准**: 功能标准、质量标准、文档标准
4. **错误处理规范**: 失败报告、重试策略、降级策略

所有测试必须严格遵守此合同，确保测试的真实性、可靠性和可维护性。
