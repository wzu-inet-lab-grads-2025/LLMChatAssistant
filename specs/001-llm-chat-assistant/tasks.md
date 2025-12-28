# 任务: 智能网络运维助手

**输入**: 来自 `/specs/001-llm-chat-assistant/` 的设计文档

**前置条件**: plan.md(必需)、spec.md(用户故事必需)、research.md、data-model.md、contracts/

**测试**: 测试是必需的，遵循章程要求（真实测试，不允许 mock）

**组织结构**: 任务按用户故事分组，以便每个故事能够独立实施和测试

## 格式: `[ID] [P?] [Story] 描述`
- **[P]**: 可以并行运行（不同文件，无依赖关系）
- **[Story]**: 此任务属于哪个用户故事（例如：US1、US2、US3）
- 在描述中包含确切的文件路径

## 路径约定

- **单一项目**: 仓库根目录下的 `src/`、`tests/`
- 以下显示的路径基于 plan.md 中定义的项目结构

---

## 阶段 1: 设置(共享基础设施)

**目的**: 项目初始化和基本结构

- [X] T001 创建项目目录结构 src/, tests/, logs/, storage/
- [X] T002 使用 uv 和 Python 3.11 初始化项目 (遵循章程: 开发环境标准)
- [X] T003 [P] 配置 pyproject.toml，添加 zai-sdk、rich、numpy 依赖 (遵循章程: 真实集成)
- [X] T004 [P] 在 logs 文件夹中创建 server.log 和 client.log (遵循章程: 文档与可追溯性)
- [X] T005 [P] 创建 storage 目录结构 storage/vectors/, storage/history/, storage/uploads/ (遵循章程: 数据持久化)
- [X] T006 [P] 在 src/utils/config.py 中实现配置管理，验证 ZHIPU_API_KEY (遵循章程: 测试真实性)
- [X] T007 [P] 在 src/utils/logger.py 中实现日志配置，支持中文日志 (遵循章程: 语言规范)

---

## 阶段 1.5: 版本控制检查点

**目的**: 确保设置阶段完成并通过测试后进行版本提交

- [X] T008 验证项目结构和配置文件正确性
- [X] T009 提交设置阶段代码，描述项目初始化和配置 (遵循章程: 版本控制与测试纪律)

---

## 阶段 2: 基础(阻塞前置条件)

**目的**: 在任何用户故事可以实施之前必须完成的核心基础设施

**⚠️ 关键**: 在此阶段完成之前，无法开始任何用户故事工作

### 2.1 协议层实现

- [X] T010 在 src/protocols/nplt.py 中实现 NPLTMessage 类，包含编码/解码方法 (参考 contracts/nplt-protocol.md)
- [X] T011 在 src/protocols/nplt.py 中实现 MessageType 枚举 (CHAT_TEXT, AGENT_THOUGHT, DOWNLOAD_OFFER)
- [X] T012 [P] 在 src/protocols/rdt.py 中实现 RDTPacket 类，包含校验和计算 (参考 contracts/rdt-protocol.md)
- [X] T013 [P] 在 src/protocols/rdt.py 中实现 ACKPacket 类

### 2.2 LLM Provider 抽象层

- [X] T014 在 src/llm/base.py 中定义 LLMProvider 抽象接口 (chat, embed, validate_api_key) (遵循章程: LLM Provider 扩展)
- [X] T015 在 src/llm/zhipu.py 中实现 ZhipuProvider，使用 zai-sdk 集成智谱 API (遵循章程: 真实集成)
- [X] T016 在 src/llm/zhipu.py 中实现模型切换底层功能，支持运行时在 glm-4-flash 和 glm-4.5-flash 之间切换（不涉及用户界面）
- [X] T017 在 src/llm/models.py 中定义模型配置常量 (DEFAULT_CHAT_MODEL, AVAILABLE_MODELS, EMBED_MODEL)

### 2.3 存储层实现

- [X] T018 在 src/storage/vector_store.py 中实现 VectorIndex 类，包含 search 方法 (参考 data-model.md)
- [X] T019 在 src/storage/vector_store.py 中实现向量索引持久化 (保存到 storage/vectors/)
- [X] T020 在 src/storage/history.py 中实现 ConversationHistory 类，支持 add_message 和 get_context (参考 data-model.md)
- [X] T021 在 src/storage/history.py 中实现对话历史持久化 (保存到 storage/history/)
- [X] T022 [P] 在 src/storage/files.py 中实现 UploadedFile 类，包含文件大小验证 (10MB 限制)

### 2.4 工具层实现

- [X] T023 在 src/tools/base.py 中定义 Tool 基类 (execute 方法)
- [X] T024 [P] 在 src/tools/command.py 中实现 CommandTool，白名单命令执行 (ls, cat, grep 等)
- [X] T025 [P] 在 src/tools/monitor.py 中实现 MonitorTool，系统监控 (CPU、内存、磁盘)
- [X] T026 在 src/tools/rag.py 中实现 RAGTool，向量检索功能

### 2.5 Agent 实现

- [X] T027 在 src/server/agent.py 中实现 ReActAgent 类，支持最多 5 轮工具调用
- [X] T028 在 src/server/agent.py 中实现工具调用超时控制 (5 秒超时)
- [X] T029 在 src/server/agent.py 中实现 API 失败降级到本地命令执行

### 2.6 网络通信基础

- [ ] T030 在 src/server/nplt_server.py 中实现 NPLT 服务器端协议处理
- [ ] T031 在 src/server/nplt_server.py 中实现 TCP 心跳机制 (90 秒间隔)
- [ ] T032 在 src/server/nplt_server.py 中实现会话管理 (Session 类)
- [ ] T033 在 src/server/rdt_server.py 中实现 RDT 发送方，滑动窗口 N=5 (参考 contracts/rdt-protocol.md)
- [ ] T034 在 src/server/rdt_server.py 中实现超时重传机制 (仅对 SendBase 计时)

### 2.7 客户端基础

- [ ] T035 在 src/client/ui.py 中实现 Rich UI 组件 (启动画面、Spinner、Markdown 渲染)
- [ ] T036 在 src/client/nplt_client.py 中实现 NPLT 客户端端协议处理
- [ ] T037 在 src/client/nplt_client.py 中实现 TCP 连接管理和重连 (最多 3 次)
- [ ] T038 在 src/client/main.py 中实现客户端主循环和命令解析 (/upload, /model, /quit)

---

## 阶段 2.5: 版本控制检查点

**目的**: 确保基础设施阶段完成并通过测试后进行版本提交

- [ ] T039 运行所有基础设施阶段的测试，确保协议、LLM、存储、工具测试通过 (遵循章程: 版本控制与测试纪律)
- [ ] T040 提交基础设施阶段代码，描述基础设施实现和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 基础就绪 - 现在可以开始并行实施用户故事

---

## 阶段 3: 用户故事 1 - CLI客户端基础对话 (优先级: P1)🎯 MVP

**目标**: 实现客户端与服务器的基础 TCP 长连接对话功能，Agent 调用系统监控工具返回信息

**独立测试**: 启动客户端、建立 TCP 连接、发送查询、接收 AI 回复和工具状态

### 用户故事 1 的测试(必需)⚠️

**注意: 先编写这些测试，确保在实施前它们失败**

- [ ] T041 [P] [US1] 在 tests/contract/test_nplt.py 中编写 NPLT 协议编解码测试
- [ ] T042 [P] [US1] 在 tests/integration/test_client_server.py 中编写客户端-服务器连接测试
- [ ] T043 [US1] 在 tests/integration/test_agent.py 中编写 Agent 工具调用测试 (使用真实智谱 API)
- [ ] T043a [P] [US1] 在 tests/contract/test_nplt_wire_format.py 中编写 NPLT 协议字节格式测试（验证字段长度、字节序等）
- [ ] T043b [P] [US1] 在 tests/contract/test_rdt_wire_format.py 中编写 RDT 协议字节格式测试（验证字段长度、校验和计算等）

### 用户故事 1 的实施

- [ ] T044 [US1] 在 src/server/main.py 中实现服务器入口和启动逻辑
- [ ] T045 [US1] 在 src/server/main.py 中集成 ReActAgent 和 NPLT 服务器
- [ ] T046 [US1] 在 src/server/nplt_server.py 中处理 CHAT_TEXT 和 AGENT_THOUGHT 消息
- [ ] T047 [US1] 在 src/client/main.py 中实现用户输入循环和消息发送
- [ ] T048 [US1] 在 src/client/ui.py 中实现流式 Markdown 渲染和 Agent 思考过程显示
- [ ] T049 [US1] 为用户故事 1 添加日志记录 (logs/client.log 和 logs/server.log)

---

## 阶段 3.5: 版本控制检查点

**目的**: 确保用户故事 1 完成并通过测试后进行版本提交

- [ ] T050 [US1] 运行用户故事 1 的所有测试，确保测试通过 (遵循章程: 版本控制与测试纪律)
- [ ] T051 [US1] 提交用户故事 1 代码，描述基础对话功能和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 此时，用户故事 1 应该完全功能化且可独立测试

---

## 阶段 4: 用户故事 2 - 文件上传与RAG检索 (优先级: P2)

**目标**: 实现文件上传功能，向量索引建立，基于文件内容的 RAG 检索

**独立测试**: 上传配置文件、建立向量索引、查询文件内容相关问题

### 用户故事 2 的测试(必需)⚠️

- [ ] T052 [P] [US2] 在 tests/unit/test_storage.py 中编写向量索引测试
- [ ] T053 [P] [US2] 在 tests/integration/test_rag.py 中编写 RAG 检索集成测试 (使用真实智谱 API)

### 用户故事 2 的实施

- [ ] T054 [US2] 在 src/client/main.py 中实现 /upload 命令解析和文件读取
- [ ] T055 [US2] 在 src/client/main.py 中实现上传进度条显示 (Rich Progress)
- [ ] T056 [US2] 在 src/client/nplt_client.py 中实现文件数据分块发送 (NPLT 协议)
- [ ] T057 [US2] 在 src/server/nplt_server.py 中实现文件数据接收和组装
- [ ] T058 [US2] 在 src/server/nplt_server.py 中调用 storage.files 保存文件到 storage/uploads/
- [ ] T059 [US2] 在 src/server/agent.py 中集成 RAGTool，自动调用检索上传文件
- [ ] T060 [US2] 在 src/storage/files.py 中实现文件大小验证 (10MB 限制，拒绝超限文件)
- [ ] T061 [US2] 在 src/storage/vector_store.py 中实现文件文本分块 (500 字分块，50 字重叠)
- [ ] T062 [US2] 在 src/storage/vector_store.py 中实现 Embedding 向量计算 (使用智谱 embedding-3-pro)
- [ ] T063 [US2] 在 src/storage/vector_store.py 中实现向量索引持久化到 storage/vectors/

---

## 阶段 4.5: 版本控制检查点

**目的**: 确保用户故事 2 完成并通过测试后进行版本提交

- [ ] T064 [US2] 运行用户故事 2 的所有测试，确保测试通过 (遵循章程: 版本控制与测试纪律)
- [ ] T065 [US2] 提交用户故事 2 代码，描述文件上传和 RAG 功能及测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 此时，用户故事 1 和 2 都应该独立运行

---

## 阶段 5: 用户故事 3 - RDT可靠文件传输 (优先级: P3)

**目标**: 实现基于 UDP 的可靠文件传输，滑动窗口机制，可视化传输过程

**独立测试**: AI 发送文件提议、用户确认接收、UDP 传输、文件完整性验证

### 用户故事 3 的测试(必需)⚠️

- [ ] T066 [P] [US3] 在 tests/contract/test_rdt.py 中编写 RDT 协议编解码测试
- [ ] T067 [P] [US3] 在 tests/contract/test_rdt.py 中编写滑动窗口机制测试
- [ ] T068 [US3] 在 tests/integration/test_rdt.py 中编写文件传输集成测试 (模拟丢包)

### 用户故事 3 的实施

- [ ] T069 [US3] 在 src/protocols/rdt.py 中实现 RDTSession 类，管理传输状态
- [ ] T070 [US3] 在 src/server/rdt_server.py 中实现文件发送逻辑 (读取文件、分片、发送)
- [ ] T071 [US3] 在 src/server/rdt_server.py 中实现下载令牌生成和关联 (TCP 提议 → UDP 传输)
- [ ] T072 [US3] 在 src/server/nplt_server.py 中实现 DOWNLOAD_OFFER 消息发送
- [ ] T073 [US3] 在 src/client/rdt_client.py 中实现 RDT 接收方逻辑
- [ ] T074 [US3] 在 src/client/rdt_client.py 中实现 ACK 发送和序列号管理
- [ ] T075 [US3] 在 src/client/rdt_client.py 中实现数据包组装和文件写入
- [ ] T076 [US3] 在 src/client/main.py 中实现下载确认提示 (显示文件名、大小，等待用户输入 y/n)
- [ ] T077 [US3] 在 src/client/ui.py 中实现窗口状态可视化 (显示当前窗口包: [0] [1] [2] [3] [4])
- [ ] T078 [US3] 在 src/client/ui.py 中实现传输进度条、速度和重传统计显示
- [ ] T079 [US3] 在 src/client/rdt_client.py 中实现文件完整性验证 (CRC32 校验和)

---

## 阶段 5.5: 版本控制检查点

**目的**: 确保用户故事 3 完成并通过测试后进行版本提交

- [ ] T080 [US3] 运行用户故事 3 的所有测试，确保测试通过 (遵循章程: 版本控制与测试纪律)
- [ ] T081 [US3] 提交用户故事 3 代码，描述 RDT 文件传输功能和测试结果 (遵循章程: 版本控制与测试纪律)

**检查点**: 所有用户故事现在应该独立功能化

---

## 阶段 N: 完善与横切关注点

**目的**: 影响多个用户故事的改进

- [ ] T082 在 src/client/main.py 中实现 /model 命令，调用 T016 实现的底层切换功能，提供用户界面（如 /model glm-4.5-flash）
- [ ] T083 在 src/client/main.py 中实现 /history 命令，查看对话历史
- [ ] T084 在 src/client/main.py 中实现 /clear 命令，清空当前会话历史
- [ ] T085 在 src/server/main.py 中实现优雅关闭 (Ctrl+C 处理)
- [ ] T086 [P] 在 tests/unit/test_tools.py 中添加工具单元测试 (CommandTool、MonitorTool、RAGTool)
- [ ] T087 [P] 在 tests/unit/test_llm.py 中添加 LLM Provider 单元测试 (ZhipuProvider、模型切换)
- [ ] T088 代码清理和重构，确保所有代码注释使用中文 (遵循章程: 语言规范)
- [ ] T088a [P] 在 tests/performance/test_client_memory.py 中编写客户端长期运行测试（100+ 轮对话，验证内存泄漏和性能）
- [ ] T088b 在 T088a 测试基础上，优化客户端 UI 渲染性能（如有内存泄漏或性能下降）
- [ ] T089 性能优化，验证 AI 工具调用响应时间 < 2s (参考 SC-002)
- [ ] T090 安全加固，确保命令黑名单字符过滤生效 (测试 ;、&、>、|)
- [ ] T091 运行 quickstart.md 验证，确保所有示例可执行
- [ ] T091a [P] 在 tests/contract/test_nplt_wire_format.py 中编写 NPLT 协议字节格式测试（验证与 contracts/nplt-protocol.md 规范一致性）
- [ ] T091b [P] 在 tests/contract/test_rdt_wire_format.py 中编写 RDT 协议字节格式测试（验证与 contracts/rdt-protocol.md 规范一致性）

---

## 阶段 N.5: 版本控制检查点

**目的**: 确保完善阶段完成并通过测试后进行最终版本提交

- [ ] T092 运行所有测试，包括完善和横切关注点的测试、性能测试（T088a）和协议格式测试（T091a, T091b），确保测试通过 (遵循章程: 版本控制与测试纪律)
- [ ] T093 提交完善阶段代码，描述完善工作和最终的测试结果 (遵循章程: 版本控制与测试纪律)

---

## 依赖关系与执行顺序

### 阶段依赖关系

- **设置(阶段 1)**: 无依赖关系 - 可立即开始
- **基础(阶段 2)**: 依赖于设置完成 - 阻塞所有用户故事
- **用户故事(阶段 3-5)**: 都依赖于基础阶段完成
  - 然后用户故事可以并行进行(如果有人员)
  - 或按优先级顺序进行(P1 → P2 → P3)
- **完善(最终阶段)**: 依赖于所有期望的用户故事完成

### 用户故事依赖关系

- **用户故事 1(P1)**: 可在基础(阶段 2)后开始 - 无其他故事依赖
- **用户故事 2(P2)**: 可在基础(阶段 2)后开始 - 可与 US1 集成但应独立可测试
- **用户故事 3(P3)**: 可在基础(阶段 2)后开始 - 可与 US1/US2 集成但应独立可测试

### 每个用户故事内部

- 测试(包含)必须在实施前编写并失败
- 协议实现在工具层之前
- 工具层在 Agent 之前
- Agent 在服务器集成之前
- 服务器集成在客户端集成之前
- 故事完成后才移至下一个优先级

### 并行机会

- 阶段 1 中的所有 [P] 任务可以并行运行
- 阶段 2.1 (协议层) 中的所有 [P] 任务可以并行运行
- 阶段 2.2 (LLM 层) 和 2.3 (存储层) 可以并行运行
- 阶段 2.4 (工具层) 中的所有 [P] 任务可以并行运行
- 所有测试用例中的 [P] 任务可以并行编写
- 不同用户故事可以由不同团队成员并行处理

---

## 并行示例: 用户故事 1 测试编写

```bash
# 一起启动用户故事 1 的所有测试编写:
pytest tests/contract/test_nplt.py --fixtures-only  # 生成测试框架
pytest tests/integration/test_client_server.py --fixtures-only
pytest tests/integration/test_agent.py --fixtures-only
```

---

## 实施策略

### 仅 MVP(仅用户故事 1)

1. 完成阶段 1: 设置
2. 完成阶段 2: 基础(关键 - 阻塞所有故事)
3. 完成阶段 3: 用户故事 1
4. **停止并验证**: 独立测试用户故事 1
5. 如准备好则部署/演示

### 增量交付

1. 完成设置 + 基础 → 基础就绪
2. 添加用户故事 1 → 独立测试 → 部署/演示(MVP!)
3. 添加用户故事 2 → 独立测试 → 部署/演示
4. 添加用户故事 3 → 独立测试 → 部署/演示
5. 每个故事在不破坏先前故事的情况下增加价值

### 并行团队策略

有多个开发人员时:

1. 团队一起完成设置 + 基础
2. 基础完成后:
   - 开发人员 A: 用户故事 1
   - 开发人员 B: 用户故事 2
   - 开发人员 C: 用户故事 3
3. 故事独立完成和集成

---

## 注意事项

- [P] 任务 = 不同文件，无依赖关系
- [Story] 标签将任务映射到特定用户故事以实现可追溯性
- 每个用户故事应该独立可完成和可测试
- 在实施前验证测试失败
- 在每个任务或逻辑组后提交
- 在任何检查点停止以独立验证故事
- 避免: 模糊任务、相同文件冲突、破坏独立性的跨故事依赖
