# 任务: 智能网络运维助手

**输入**: 来自 `/specs/001-llm-chat-assistant/` 的设计文档
**前置条件**: plan.md、spec.md、research.md、data-model.md、contracts/

**测试**: 所有测试必须使用真实API，不允许使用mock（遵循章程: 测试真实性）

**组织结构**: 任务按用户故事分组，以便每个故事能够独立实施和测试

## 格式: `[ID] [P?] [Story] 描述`
- **[P]**: 可以并行运行(不同文件，无依赖关系)
- **[Story]**: 此任务属于哪个用户故事(例如: US1、US2、US3、MS)
- 在描述中包含确切的文件路径

## 路径约定
- **单一项目**: 仓库根目录下的 `src/`、`tests/`

---

## 阶段 1: 设置(共享基础设施)

**目的**: 项目初始化和基本结构

- [X] T001 创建项目目录结构 (src/client/, src/server/, src/protocols/, src/llm/, src/storage/, src/tools/, src/utils/, tests/integration/, tests/unit/)
- [X] T002 使用 uv 和 Python 3.11 初始化项目，创建 pyproject.toml 依赖配置 (遵循章程: 开发环境标准)
- [X] T003 [P] 创建 config.yaml 配置文件模板（服务器、LLM、存储、日志配置）
- [X] T004 [P] 创建 .env 文件模板（ZHIPU_API_KEY 环境变量占位符）
- [X] T005 [P] 创建 logs/ 目录用于存储日志文件 (遵循章程: 文档与可追溯性)
- [X] T006 [P] 创建 storage/ 目录结构（storage/vectors/, storage/history/, storage/uploads/, storage/archive/）
- [X] T007 [P] 在 pyproject.toml 中配置依赖：zai-sdk、rich、faiss-cpu、pyyaml、pytest、pytest-asyncio
- [X] T008 [P] 确保所有代码注释使用中文 (遵循章程: 语言规范)
- [X] T009 [P] 确保错误消息和日志使用中文 (遵循章程: 语言规范)

---

## 阶段 1.5: 版本控制检查点

**目的**: 确保设置阶段完成并通过测试后进行版本提交

- [X] T010 运行 uv sync 确保依赖安装成功，验证项目结构正确
- [X] T011 提交设置阶段代码，清晰描述项目初始化工作 (遵循章程: 版本控制与测试纪律)

---

## 阶段 2: 基础(阻塞前置条件)

**目的**: 在任何用户故事可以实施之前必须完成的核心基础设施

**⚠️ 关键**: 在此阶段完成之前，无法开始任何用户故事工作

**验收标准**:

- 所有单元测试通过（协议编解码、LLM Provider 接口、VectorStore、配置加载）
- 协议层接口稳定（NPLT 和 RDT 协议完整实现）
- LLM 调用成功（使用真实 API 验证智谱集成）
- 存储层功能正常（向量存储和对话历史持久化）

### 协议层实现

- [X] T012 [P] 在 src/protocols/nplt.py 中实现 NPLT 协议（消息编码/解码、MessageType 枚举）
- [X] T013 [P] 在 src/protocols/rdt.py 中实现 RDT 协议（数据包编码/解码、CRC16 校验和）

### LLM 抽象层

- [X] T014 [P] 在 src/llm/base.py 中定义 LLMProvider 抽象接口（chat、embed、validate_api_key、set_model 方法）
- [X] T015 [P] 在 src/llm/zhipu.py 中实现 ZhipuProvider（集成 zai-sdk，支持 glm-4-flash、glm-4.5-flash、embedding-3-pro）

### 存储层

- [X] T016 [P] 在 src/storage/vector_store.py 中实现 VectorStore（FAISS 索引、add_file、search、list_files、load_all、save_all 方法）
- [X] T017 在 src/storage/history.py 中实现 ConversationHistory（add_message、get_context、save、load、create_new 方法）
- [X] T018 [P] 在 src/storage/history.py 中实现 ToolCall 和 ChatMessage 数据类（to_dict、from_dict 序列化）

### 工具基类

- [X] T019 [P] 在 src/tools/base.py 中实现 Tool 抽象基类和 ToolExecutionResult 数据类

### 配置管理

- [X] T020 在 src/utils/config.py 中实现配置加载（load_config 函数，支持 config.yaml 和 .env，环境变量覆盖）
- [X] T021 [P] 在 src/utils/logger.py 中实现日志管理（配置日志写入 logs/ 文件夹，纯文本格式，中文消息）

### 模型切换回调

- [X] T022 在 src/llm/zhipu.py 中添加 set_model 方法实现模型切换验证（ValueError for invalid models）

---

## 阶段 2.5: 版本控制检查点

**目的**: 确保基础设施阶段完成并通过测试后进行版本提交

- [X] T023 编写单元测试验证协议编解码、LLM Provider 接口、VectorStore、配置加载功能
- [X] T024 运行所有基础设施阶段的测试，确保测试通过 (遵循章程: 版本控制与测试纪律)
- [X] T025 提交基础设施阶段代码，清晰描述基础组件实现和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 基础就绪 - 现在可以开始并行实施用户故事

---

## 阶段 3: 用户故事 1 - CLI客户端基础对话(优先级: P1) 🎯 MVP

**目标**: 用户启动CLI客户端，通过TCP连接与AI助手实时对话，获得系统状态查询、日志分析等运维帮助

**独立测试**: 启动客户端、建立TCP连接、发送文本消息并接收AI回复，验证对话能力

### 用户故事 1 的集成测试(遵循章程: 测试真实性)

**注意: 先编写这些测试，确保在实施前它们失败**

- [X] T026 [P] [US1] 在 tests/integration/test_nplt_protocol.py 中编写 NPLT 协议通信测试（消息编码、解码、边界条件）
- [X] T027 [P] [US1] 在 tests/integration/test_agent.py 中编写 ReAct Agent 集成测试（工具调用循环、超时控制、降级模式）
- [X] T028 [P] [US1] 在 tests/integration/test_client.py 中编写客户端连接测试（TCP连接、心跳、断线重连）
- [X] T029 [P] [US1] 在 tests/integration/test_server.py 中编写服务器处理测试（消息接收、Agent调用、响应发送）

### 用户故事 1 的实施

#### 客户端组件

- [X] T030 [P] [US1] 在 src/client/nplt_client.py 中实现 NPLTClient（connect、send_message、receive_messages、heartbeat 方法）
- [X] T031 [P] [US1] 在 src/client/ui.py 中实现 Rich UI 组件（启动画面、Spinner、Markdown 渲染、进度条）
- [X] T032 [US1] 在 src/client/main.py 中实现客户端主程序（连接服务器、处理用户输入、显示AI回复、/model、/upload、/history、/clear 命令）

#### 服务器组件

- [X] T033 [P] [US1] 在 src/server/nplt_server.py 中实现 NPLTServer（handle_client、消息路由、心跳超时检测、model_switch_callback）
- [X] T034 [P] [US1] 在 src/server/agent.py 中实现 ReActAgent（react_loop、_think_and_decide、工具执行、降级模式）
- [X] T035 [US1] 在 src/server/main.py 中实现服务器主程序（NPLTServer 初始化、model_switch_callback 注册、启动 TCP 服务器）

#### Agent 工具实现

- [X] T036 [P] [US1] 在 src/tools/command.py 中实现 CommandTool（白名单验证、命令执行、安全过滤）
- [X] T037 [P] [US1] 在 src/tools/monitor.py 中实现 MonitorTool（CPU、内存、磁盘监控）
- [X] T038 [US1] 在 src/tools/rag.py 中实现 RAGTool（向量检索、结果格式化、get_help）

#### 模型切换功能

- [X] T039 [P] [US1] 在 src/server/nplt_server.py 中实现 handle_model_switch 处理（MODEL_SWITCH 消息类型、模型白名单验证、回调调用、错误响应）
- [X] T040 [P] [US1] 在 src/client/main.py 中实现 /model 命令（发送 MODEL_SWITCH 请求、处理响应、更新本地模型状态）

#### 消息类型扩展

- [X] T041 [US1] 在 src/protocols/nplt.py 中添加新的消息类型（MODEL_SWITCH 0x18）

---

## 阶段 3.5: 版本控制检查点

**目的**: 确保用户故事 1 完成并通过测试后进行版本提交

- [X] T042 运行用户故事 1 的所有集成测试，确保真实API调用成功、Agent工具调用正常、模型切换功能可用 (遵循章程: 版本控制与测试纪律)
- [X] T043 提交用户故事 1 代码，清晰描述CLI对话功能和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 此时，用户故事 1 应该完全功能化且可独立测试

---

## 阶段 4: 用户故事 2 - 文件上传与RAG检索(优先级: P2)

**目标**: 用户通过CLI上传文件，AI助手进行向量检索和语义搜索，基于文件内容回答问题

**独立测试**: 上传配置文件、询问文件内容相关问题，验证索引和检索流程

### 用户故事 2 的集成测试(遵循章程: 测试真实性)

- [X] T044 [P] [US2] 在 tests/integration/test_file_upload.py 中编写文件上传测试（小文件、大文件、超限文件、非文本文件）
- [X] T045 [P] [US2] 在 tests/integration/test_vector_store.py 中编写向量索引测试（文件索引、Embedding 计算、FAISS 检索）
- [X] T046 [P] [US2] 在 tests/integration/test_rag.py 中编写 RAG 检索测试（语义搜索、相似度排序、结果格式化）

### 用户故事 2 的实施

#### 客户端上传功能

- [X] T047 [P] [US2] 在 src/client/main.py 中实现 /upload 命令（文件选择、大小验证、进度条显示）
- [X] T048 [P] [US2] 在 src/client/nplt_client.py 中实现 send_file 方法（文件分块发送、NPLT 协议封装）

#### 服务器文件处理

- [X] T049 [P] [US2] 在 src/server/nplt_server.py 中实现文件上传处理（接收文件、保存到 storage/uploads/、大小验证、类型验证）
- [X] T050 [P] [US2] 在 src/server/nplt_server.py 中实现向量索引触发（小文件立即索引，大文件异步索引）
- [X] T051 [US2] 在 src/storage/vector_store.py 中实现 add_file 方法（文本分块、Embedding 计算、FAISS 索引创建、持久化）

#### 文件索引集成

- [X] T052 [P] [US2] 在 src/tools/rag.py 中集成 VectorStore（upload_file 通知、index_file 调用）
- [X] T053 [US2] 在 src/server/nplt_server.py 中集成文件上传到 RAGTool（文件路径传递、索引完成确认）

#### Embedding 批处理优化

- [X] T054 [P] [US2] 在 src/llm/zhipu.py 中实现批量 embed 方法（减少 API 调用次数）
- [X] T055 [US2] 在 src/storage/vector_store.py 中实现智能分块策略（500字/块，50字重叠，大文件后台处理）

#### 消息类型扩展

- [X] T056 [US2] 在 src/protocols/nplt.py 中添加新的消息类型（FILE_UPLOAD 0x0D、UPLOAD_ACK 0x0E）

---

## 阶段 4.5: 版本控制检查点

**目的**: 确保用户故事 2 完成并通过测试后进行版本提交

- [X] T057 运行用户故事 2 的所有集成测试，确保文件上传成功、向量索引正确、RAG 检索返回相关结果 (遵循章程: 版本控制与测试纪律)
- [X] T058 提交用户故事 2 代码，清晰描述文件上传和 RAG 检索功能和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 此时，用户故事 1 和 2 都应该独立运行

---

## 阶段 5: 用户故事 3 - RDT可靠文件传输(优先级: P3)

**目标**: AI助手通过UDP协议可靠传输文件，使用滑动窗口处理丢包和重传，可视化传输过程

**独立测试**: 请求AI发送日志文件、接受传输提议、观察UDP传输过程、验证文件完整性

### 用户故事 3 的集成测试(遵循章程: 测试真实性)

- [X] T059 [P] [US3] 在 tests/integration/test_rdt_protocol.py 中编写 RDT 协议测试（滑动窗口、超时重传、丢包模拟）
- [X] T060 [P] [US3] 在 tests/integration/test_rdt_server.py 中编写 RDT 服务器测试（文件发送、窗口管理、ACK 处理）
- [X] T061 [P] [US3] 在 tests/integration/test_rdt_client.py 中编写 RDT 客户端测试（文件接收、进度跟踪、完整性验证）

### 用户故事 3 的实施

#### RDT 协议实现

- [X] T062 [P] [US3] 在 src/protocols/rdt.py 中实现 RDTPacket 数据类（compute_checksum、validate 方法）
- [X] T063 [P] [US3] 在 src/protocols/rdt.py 中实现 RDTSession 数据类（滑动窗口、超时重传、窗口状态管理）
- [X] T064 [US3] 在 src/protocols/rdt.py 中实现发送方和接收方状态机（状态转换、超时处理）

#### RDT 服务器

- [X] T065 [P] [US3] 在 src/server/rdt_server.py 中实现 RDTServer（start_send、handle_ack、timeout_retransmit 方法）
- [X] T066 [US3] 在 src/server/rdt_server.py 中实现文件分块读取（1024字节/包、滑动窗口发送、SendBase 计时）

#### RDT 客户端

- [X] T067 [P] [US3] 在 src/client/rdt_client.py 中实现 RDTClient（start_receive、handle_packet、send_ack 方法）
- [X] T068 [US3] 在 src/client/rdt_client.py 中实现文件重组（数据包排序、完整性验证、校验和对比）

#### 文件传输集成

- [X] T069 [P] [US3] 在 src/server/nplt_server.py 中实现 handle_download_offer（生成下载令牌、发送 DOWNLOAD_OFFER 消息）
- [X] T070 [P] [US3] 在 src/server/nplt_server.py 中集成 RDTServer（创建 RDTSession、启动 UDP 发送）
- [X] T071 [US3] 在 src/client/main.py 中实现下载确认处理（显示文件信息、用户确认、启动 RDTClient）

#### 传输可视化

- [X] T072 [P] [US3] 在 src/client/ui.py 中实现 RDT 传输可视化（滑动窗口状态、传输进度条、速度显示、重传统计），验证窗口状态显示格式符合 spec.md:95 验收标准#3（如 "[101] [102] [103] [104] [105]" 格式）
- [X] T073 [US3] 在 src/client/rdt_client.py 中实现传输事件回调（进度更新、窗口状态、重传事件）

#### DownloadToken 管理

- [X] T074 [P] [US3] 在 src/server/nplt_server.py 中实现 DownloadToken 生成和验证（UUID、过期时间默认30分钟、文件映射），实现定期清理过期令牌机制（每次验证时清理或使用后台定时任务）

#### 消息类型扩展

- [X] T075 [US3] 在 src/protocols/nplt.py 中添加新的消息类型（DOWNLOAD_OFFER 0x0C 已定义）

---

## 阶段 5.5: 版本控制检查点

**目的**: 确保用户故事 3 完成并通过测试后进行版本提交

- [X] T076 运行用户故事 3 的所有集成测试，确保UDP传输可靠、滑动窗口正确、丢包重传成功、文件完整一致 (遵循章程: 版本控制与测试纪律)
- [X] T077 提交用户故事 3 代码，清晰描述RDT文件传输功能和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 所有用户故事现在应该独立功能化

---

## 阶段 6: 多会话管理功能(优先级: P1 扩展)

**目标**: 支持单用户多会话管理，用户可以创建、切换、删除会话，AI自动命名会话，自动归档旧会话

**独立测试**: 创建多个会话、切换会话、验证上下文隔离、测试会话命名和归档

### 多会话管理的集成测试(遵循章程: 测试真实性)

- [X] T078 [P] [MS] 在 tests/integration/test_session_manager.py 中编写会话管理测试（创建、切换、删除、归档）
- [X] T079 [P] [MS] 在 tests/integration/test_session_commands.py 中编写会话命令测试（/sessions、/switch、/new、/delete）

### 多会话管理的实施

#### 会话管理核心

- [X] T080 [P] [MS] 在 src/storage/history.py 中实现 ConversationSession 数据类（session_id、name、created_at、updated_at、last_accessed、message_count、archived、archive_path）
- [X] T081 [P] [MS] 在 src/storage/history.py 中实现 SessionManager 类（create_session、switch_session、list_sessions、delete_session、auto_name_session、archive_old_sessions）
- [X] T082 [P] [MS] 在 src/storage/history.py 中实现 SessionInfo 数据类（session_id、name、message_count、last_accessed、is_current）

#### 会话命名策略

- [X] T083 [MS] 在 src/storage/history.py 中实现 AI 自动命名（分析前 3 轮对话、生成标题、更新会话名称），触发时机：在会话第 3 轮对话完成后自动触发（配合 T091 集成）
- [X] T084 [P] [MS] 在 src/storage/history.py 中实现默认命名规则（基于时间格式：YYYY-MM-DD HH:MM）

#### 会话命令实现

- [X] T085 [P] [MS] 在 src/client/main.py 中实现 /sessions 命令（显示会话列表、当前会话标记）
- [X] T086 [P] [MS] 在 src/client/main.py 中实现 /switch <session_id> 命令（切换会话、加载上下文）
- [X] T087 [P] [MS] 在 src/client/main.py 中实现 /new 命令（创建新会话、切换到新会话）
- [X] T088 [P] [MS] 在 src/client/main.py 中实现 /delete <session_id> 命令（二次确认、删除会话、自动创建默认会话）

#### 服务器会话管理

- [X] T089 [P] [MS] 在 src/server/nplt_server.py 中实现会话管理消息处理（SESSION_LIST 0x14、SESSION_SWITCH 0x15、SESSION_NEW 0x16、SESSION_DELETE 0x17）
- [X] T090 [MS] 在 src/server/nplt_server.py 中集成 SessionManager（创建实例、注册回调、处理会话命令）
- [X] T091 [MS] 在 src/server/agent.py 中集成会话命名（在第 3 轮对话后触发 auto_name_session）

#### 上下文管理

- [X] T092 [MS] 在 src/server/nplt_server.py 中实现会话切换时的上下文加载（加载 ConversationHistory、恢复上下文窗口）
- [X] T093 [P] [MS] 在 src/storage/history.py 中实现会话归档（按月组织、移动文件、更新 archived 状态）

#### 存储结构更新

- [X] T094 [P] [MS] 更新 storage/history/ 目录结构（支持多个会话文件、session_YYYYMMDD_<id>.json 格式）
- [X] T095 [P] [MS] 创建 storage/archive/ 目录结构（按月组织：YYYY-MM/）

---

## 阶段 6.5: 版本控制检查点

**目的**: 确保多会话管理功能完成并通过测试后进行版本提交

- [X] T096 运行多会话管理的所有集成测试，确保会话创建、切换、删除、命名、归档功能正常 (遵循章程: 版本控制与测试纪律)
- [X] T097 提交多会话管理代码，清晰描述多会话功能和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 多会话管理功能完成，系统支持完整的会话生命周期管理

---

## 阶段 7: 完善与横切关注点

**目的**: 影响多个用户故事的改进

- [X] T098 [P] 创建 config.yaml 和 config.client.yaml 示例文件（包含所有配置项、环境变量引用、中文注释）
- [X] T099 [P] 创建 .env.example 文件（ZHIPU_API_KEY 占位符、配置说明）
- [X] T100 [P] 创建 README.md（项目概述、功能特性、安装步骤、使用方法、配置说明）
- [X] T101 代码清理和重构（移除调试代码、优化导入、统一命名规范）
- [X] T102 [P] 性能优化（异步并发优化、向量检索缓存、日志异步写入）
- [X] T103 [P] 在 tests/unit/ 中添加单元测试（协议编解码、工具执行、配置加载）
- [X] T104 安全加固（命令注入防护增强、路径遍历检查、输入验证完善）
- [X] T105 运行 quickstart.md 验证（从零开始安装、配置、运行、测试）

---

## 阶段 7.5: 版本控制检查点

**目的**: 确保完善阶段完成并通过测试后进行最终版本提交

- [X] T106 运行所有测试（单元测试、集成测试、端到端测试），确保测试通过率达到 100% (遵循章程: 版本控制与测试纪律)
- [X] T107 提交完善阶段代码，清晰描述完善工作和最终的测试结果 (遵循章程: 版本控制与测试纪律)

---

## 依赖关系与执行顺序

### 阶段依赖关系

- **设置(阶段 1)**: 无依赖关系 - 可立即开始
- **基础(阶段 2)**: 依赖于设置完成 - 阻塞所有用户故事
- **用户故事 1(阶段 3)**: 依赖于基础阶段完成 - 无其他故事依赖 (MVP)
- **用户故事 2(阶段 4)**: 依赖于基础阶段完成 - 可与 US1 并行开发
- **用户故事 3(阶段 5)**: 依赖于基础阶段完成 - 可与 US1/US2 并行开发
- **多会话管理(阶段 6)**: 依赖于用户故事 1 完成 - 扩展 US1 的会话功能
- **完善(阶段 7)**: 依赖于所有期望的用户故事完成

### 用户故事依赖关系

- **用户故事 1(P1)**: 可在基础(阶段 2)后开始 - 无其他故事依赖 (MVP)
- **用户故事 2(P2)**: 可在基础(阶段 2)后开始 - 可与 US1 集成但应独立可测试
- **用户故事 3(P3)**: 可在基础(阶段 2)后开始 - 可与 US1/US2 集成但应独立可测试
- **多会话管理**: 必须在用户故事 1 完成后开始 - 扩展会话管理功能

### 每个用户故事内部

- 集成测试必须在实施前编写并失败 (TDD 方法)
- 协议实现在服务器/客户端之前
- 基础组件在集成组件之前
- 核心实施在集成之前
- 故事完成后才移至下一个优先级

### 并行机会

- 所有标记为 [P] 的设置任务可以并行运行
- 所有标记为 [P] 的基础任务可以并行运行 (在阶段 2 内)
- 基础阶段完成后，所有用户故事可以并行开始 (如果团队容量允许)
- 用户故事中所有标记为 [P] 的测试可以并行运行
- 故事中标记为 [P] 的模型/工具可以并行运行
- 不同用户故事可以由不同团队成员并行处理

---

## 并行示例: 用户故事 1

```bash
# 一起启动用户故事 1 的所有集成测试:
任务 T026: "在 tests/integration/test_nplt_protocol.py 中编写 NPLT 协议通信测试"
任务 T027: "在 tests/integration/test_agent.py 中编写 ReAct Agent 集成测试"
任务 T028: "在 tests/integration/test_client.py 中编写客户端连接测试"
任务 T029: "在 tests/integration/test_server.py 中编写服务器处理测试"

# 一起启动用户故事 1 的所有客户端组件:
任务 T030: "在 src/client/nplt_client.py 中实现 NPLTClient"
任务 T031: "在 src/client/ui.py 中实现 Rich UI 组件"

# 一起启动用户故事 1 的所有 Agent 工具:
任务 T036: "在 src/tools/command.py 中实现 CommandTool"
任务 T037: "在 src/tools/monitor.py 中实现 MonitorTool"
任务 T038: "在 src/tools/rag.py 中实现 RAGTool"
```

---

## 实施策略

### 仅 MVP(仅用户故事 1)

1. 完成阶段 1: 设置 (T001-T011)
2. 完成阶段 2: 基础 (T012-T025)
3. 完成阶段 3: 用户故事 1 (T026-T043)
4. **停止并验证**: 独立测试用户故事 1
5. 如准备好则部署/演示

**MVP 交付内容**: CLI客户端可以连接服务器、发送消息、接收AI回复、使用工具查询系统状态、支持模型切换

### 增量交付

1. 完成设置 + 基础 → 基础就绪
2. 添加用户故事 1 → 独立测试 → 部署/演示 (MVP!)
3. 添加用户故事 2 → 独立测试 → 部署/演示
4. 添加用户故事 3 → 独立测试 → 部署/演示
5. 添加多会话管理 → 独立测试 → 部署/演示
6. 每个故事在不破坏先前故事的情况下增加价值

### 并行团队策略

有多个开发人员时:

1. 团队一起完成设置 + 基础
2. 基础完成后:
   - 开发人员 A: 用户故事 1 (CLI对话)
   - 开发人员 B: 用户故事 2 (文件上传与RAG)
   - 开发人员 C: 用户故事 3 (RDT文件传输)
3. 故事独立完成和集成
4. 开发人员 A/D: 多会话管理 (基于用户故事 1)

---

## 任务统计

- **总任务数**: 115 个任务
- **设置阶段**: 11 个任务 (T001-T011)
- **基础阶段**: 14 个任务 (T012-T025)
- **用户故事 1**: 18 个任务 (T026-T043，包含模型切换功能 T039-T040)
- **用户故事 2**: 15 个任务 (T044-T058)
- **用户故事 3**: 20 个任务 (T059-T077)
- **多会话管理**: 20 个任务 (T078-T097)
- **完善阶段**: 10 个任务 (T098-T107)
- **UI交互优化**: 8 个任务 (T108-T115)

**实施状态** (截至 2025-12-29):

- ✅ 所有 115 个基础任务已完成
- ✅ 模型切换功能已实现（T039-T040）
- ✅ 多会话管理功能已实现（T078-T097）
- ✅ UI交互优化已完成（T108-T115）
- ✅ 基于状态机的对话流程
- ✅ Spinner实时状态显示
- ✅ 209 个测试全部通过

### 并行任务统计

- **可并行任务**: 约 60% 的任务标记为 [P]
- **串行任务**: 约 40% 的任务有依赖关系

### 测试覆盖

- **集成测试**: 27 个测试任务
- **单元测试**: 1 个测试任务 (T103)
- **真实测试**: 所有测试使用真实API (无 mock)

---

## MVP 建议

**最小可行产品(MVP)**: 阶段 1 + 阶段 2 + 阶段 3

**MVP 任务**: T001-T043 (43 个任务)

**MVP 交付内容**:
- ✅ 项目初始化和基础架构
- ✅ NPLT 协议实现
- ✅ LLM Provider 抽象层 (智谱 AI)
- ✅ ReAct Agent (工具调用循环)
- ✅ CLI 客户端 (Rich UI)
- ✅ TCP 服务器 (消息处理)
- ✅ 系统监控工具
- ✅ 命令执行工具
- ✅ 模型切换功能

**后续增量**:
- 用户故事 2: 文件上传与 RAG 检索 (T044-T058)
- 用户故事 3: RDT 可靠文件传输 (T059-T077)
- 多会话管理: 会话生命周期管理 (T078-T097)

---

## 阶段 7: UI交互优化 (用户体验改进)

**目的**: 改进客户端UI交互体验，基于状态机实现流畅的对话流程

**改进内容**:

- [X] T108 [US1] 在 src/client/main.py 中实现状态机管理（waiting_for_response、response_event 状态变量）
- [X] T109 [US1] 在 src/client/main.py 中优化主循环逻辑（等待响应期间不显示输入提示符）
- [X] T110 [US1] 在 src/client/nplt_client.py 中添加响应回调机制（response_callback 字段）
- [X] T111 [US1] 在 src/client/nplt_client.py 中优化 CHAT_TEXT 消息处理（停止Spinner、触发回调）
- [X] T112 [US1] 在 src/client/nplt_client.py 中优化 AGENT_THOUGHT 消息处理（更新Spinner状态）
- [X] T113 [US1] 在 src/server/nplt_server.py 中添加发送错误处理（send_message try-except）
- [X] T114 [US1] 在 src/server/nplt_server.py 中添加空响应检查（避免发送空消息）
- [X] T115 [US1] 在 src/client/nplt_client.py 中优化连接错误提示（隐藏"0 bytes read"错误）

**验收标准**:

- 用户发送消息后显示 `⠋ [Agent] 正在分析意图...` Spinner
- 收到 AGENT_THOUGHT 时更新Spinner为 `⠙ [Tool: xxx] ...`
- 收到 CHAT_TEXT 时停止Spinner并显示AI回复
- 响应完成后才显示下一个输入提示符
- 超时保护（30秒）防止无限等待
- 连接关闭时不显示"0 bytes read"错误

**实施日期**: 2025-12-29

---

## 注意事项

- [P] 任务 = 不同文件，无依赖关系
- [Story] 标签将任务映射到特定用户故事以实现可追溯性
- 每个用户故事应该独立可完成和可测试
- 在实施前验证测试失败 (TDD)
- 在每个检查点提交代码 (版本控制纪律)
- 在任何检查点停止以独立验证故事
- 避免: 模糊任务、相同文件冲突、破坏独立性的跨故事依赖
- **遵循章程**: 所有测试必须使用真实API，不允许 mock
- **遵循章程**: 所有日志必须写入 logs/ 文件夹
- **遵循章程**: 所有用户回复、注释、文档使用中文
