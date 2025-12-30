# 任务: 文件操作工具集成到 Agent

**输入**: 来自 `/specs/003-file-tools-integration/` 的设计文档
**前置条件**: plan.md(必需)、spec.md(用户故事必需)、research.md、data-model.md、contracts/

**组织结构**: 任务按用户故事分组，以便每个故事能够独立实施和测试

**注意**: 本功能复用大量现有基础设施，部分任务已标记为[已完成]。

## 格式: `[ID] [P?] [Story] 描述`
- **[P]**: 可以并行运行(不同文件，无依赖关系)
- **[Story]**: 此任务属于哪个用户故事(例如: US1、US2、US3)
- **[已完成]**: 任务已在现有代码中实现
- 在描述中包含确切的文件路径

## 路径约定
- **工具实现**: `src/tools/`
- **Agent更新**: `src/server/agent.py`
- **测试**: `tests/unit/tools/`、`tests/integration/`
- **日志**: `logs/file_operations.log`

---

## 阶段 1: 设置(共享基础设施)

**目的**: 项目初始化和基本结构

**状态**: 大部分已完成，仅需补充文件操作相关配置

- [x] T001 [已完成] 验证 Python 3.11 环境已配置
- [x] T002 [已完成] 使用 uv 管理虚拟环境
- [x] T003 [已完成] 验证 zai-sdk 依赖已安装（src/llm/zhipu.py存在）
- [x] T004 [已完成] 验证日志目录 logs/ 已存在
- [ ] T005 在 logs/file_operations.log 中创建文件操作日志文件（遵循章程：文档与可追溯性）
- [x] T006 [已完成] 验证所有现有代码注释使用中文
- [x] T007 [已完成] 验证现有错误消息和日志使用中文

---

## 阶段 1.5: 版本控制检查点

**目的**: 确保设置阶段完成

- [ ] T008 验证环境设置：检查Python版本、uv、zai-sdk（遵循章程：测试真实性）
- [ ] T009 验证日志配置：检查logs/目录存在且可写

---

## 阶段 2: 基础(阻塞前置条件)

**目的**: 在任何用户故事可以实施之前必须完成的核心基础设施

**状态**: 大部分已完成，仅需补充文件操作特定组件

**已完成的**:
- [x] T010 [已完成] 工具基类已实现（src/tools/base.py：Tool、ToolExecutionResult）
- [x] T011 [已完成] 路径验证器已实现（src/utils/path_validator.py）
- [x] T012 [已完成] 向量存储已实现（src/storage/vector_store.py）
- [x] T013 [已完成] 索引管理器已实现（src/storage/index_manager.py）
- [x] T014 [已完成] UploadedFile数据类已实现（src/storage/files.py）
- [x] T015 [已完成] NPLT协议已支持文件传输（src/protocols/nplt.py：DOWNLOAD_OFFER、FILE_DATA、FILE_METADATA）
- [x] T016 [已完成] ReAct Agent已实现（src/server/agent.py，支持工具注册和ReAct循环）
- [x] T017 [已完成] 智谱API key验证机制已存在

**需要完成的**:
- [ ] T018 在 src/utils/config.py 中验证 file_access 配置包含 allowed_paths 和 forbidden_patterns（遵循章程：安全第一原则）
- [ ] T019 [P] 在 src/utils/path_validator.py 中验证路径白名单支持 glob 模式（如 /var/log/*.log）（遵循章程：安全第一原则）
- [ ] T020 [P] 在 src/utils/path_validator.py 中验证路径黑名单保护敏感文件（.env、.ssh/*、/etc/passwd）（遵循章程：安全第一原则）
- [ ] T021 [P] 在 src/storage/index_manager.py 中验证懒加载策略避免重复索引（遵循章程：自动化与按需索引）
- [ ] T022 [P] 在 src/storage/files.py 中验证文件类型和大小限制验证（≤10MB）（遵循章程：多层防御策略）
- [ ] T023 配置文件操作审计日志到 logs/file_operations.log（遵循章程：可审计性与透明性）

---

## 阶段 2.5: 版本控制检查点

**目的**: 确保基础设施阶段完成并通过验证

- [ ] T024 验证所有基础设施组件：检查PathValidator、VectorStore、IndexManager、UploadedFile、NPLT协议
- [ ] T025 验证配置完整性：检查config.yaml包含file_access配置
- [ ] T026 提交基础设施验证代码，清晰描述"文件操作基础设施验证完成"（遵循章程：版本控制与测试纪律）

**检查点**: 基础就绪 - 现在可以开始实施用户故事

---

## 阶段 3: 用户故事 1 - 文件上传功能 (优先级: P1) 🎯 MVP

**目标**: 实现文件上传工具，支持文件类型验证、大小限制、自动索引

**独立测试**: 用户可以独立上传文件并验证Agent接收文件，无需依赖其他功能

### 用户故事 1 的实施

- [ ] T027 [P] [US1] 在 src/tools/file_upload.py 中创建 FileUploadTool 类，继承 Tool 基类
- [ ] T028 [P] [US1] 在 src/tools/file_upload.py 中实现 validate_args() 验证文件名（无路径遍历字符）
- [ ] T029 [P] [US1] 在 src/tools/file_upload.py 中实现 validate_args() 验证文件大小（≤10MB）
- [ ] T030 [P] [US1] 在 src/tools/file_upload.py 中实现 validate_args() 验证内容类型（仅文本文件）
- [ ] T031 [US1] 在 src/tools/file_upload.py 中实现 execute() 方法，使用 UploadedFile.create_from_content() 保存文件
- [ ] T032 [US1] 在 src/tools/file_upload.py 中实现自动索引：调用 IndexManager.ensure_indexed() 建立向量索引
- [ ] T033 [US1] 在 src/tools/file_upload.py 中添加文件上传日志记录到 logs/file_operations.log（遵循章程：可审计性与透明性）
- [ ] T034 [US1] 在 src/tools/file_upload.py 中实现错误处理：文件过大、类型不支持、路径遍历等

---

## 阶段 3.5: 版本控制检查点

**目的**: 确保用户故事 1 完成并通过验证

- [ ] T035 在 tests/unit/tools/test_file_upload.py 中编写单元测试验证文件上传工具
- [ ] T036 运行文件上传工具单元测试，验证所有验证规则和错误处理（遵循章程：版本控制与测试纪律）
- [ ] T037 提交用户故事 1 代码，清晰描述"FileUploadTool实现完成"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 此时，用户故事 1（文件上传）应该完全功能化且可独立测试

---

## 阶段 4: 用户故事 2 - 文件下载功能 (优先级: P1)

**目标**: 实现文件下载工具，支持路径白名单验证、下载提议

**独立测试**: 用户可以请求下载文件并验证文件成功传输

### 用户故事 2 的实施

- [ ] T038 [P] [US2] 在 src/tools/file_download.py 中创建 FileDownloadTool 类，继承 Tool 基类
- [ ] T039 [P] [US2] 在 src/tools/file_download.py 中实现 validate_args() 使用 PathValidator.is_allowed() 验证路径
- [ ] T040 [P] [US2] 在 src/tools/file_download.py 中实现 validate_args() 验证文件存在性
- [ ] T041 [P] [US2] 在 src/tools/file_download.py 中实现 validate_args() 路径规范化（防止../）
- [ ] T042 [US2] 在 src/tools/file_download.py 中实现 execute() 方法，使用 NPLT 协议发送 DOWNLOAD_OFFER
- [ ] T043 [US2] 在 src/tools/file_download.py 中实现等待用户确认后发送 FILE_DATA（分块传输）
- [ ] T044 [US2] 在 src/tools/file_download.py 中添加文件下载日志记录到 logs/file_operations.log（遵循章程：可审计性与透明性）
- [ ] T045 [US2] 在 src/tools/file_download.py 中实现错误处理：文件不存在、路径越界、黑名单匹配

---

## 阶段 4.5: 版本控制检查点

**目的**: 确保用户故事 2 完成并通过验证

- [ ] T046 在 tests/unit/tools/test_file_download.py 中编写单元测试验证文件下载工具
- [ ] T047 运行文件下载工具单元测试，验证路径验证和错误处理（遵循章程：版本控制与测试纪律）
- [ ] T048 提交用户故事 2 代码，清晰描述"FileDownloadTool实现完成"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 此时，用户故事 1 和 2（上传+下载）都应该独立运行

---

## 阶段 5: 用户故事 3 - 语义检索文件功能 (优先级: P1)

**目标**: 实现文件语义检索工具，支持自然语言查询

**独立测试**: 用户可以用自然语言搜索文件内容，验证Agent能够找到正确文件

### 用户故事 3 的实施

- [ ] T049 [P] [US3] 在 src/tools/file_search.py 中创建 FileSemanticSearchTool 类，继承 Tool 基类
- [ ] T050 [P] [US3] 在 src/tools/file_search.py 中实现 validate_args() 验证查询非空
- [ ] T051 [P] [US3] 在 src/tools/file_search.py 中实现 validate_args() 验证 top_k 范围（1-10）
- [ ] T052 [US3] 在 src/tools/file_search.py 中实现 execute() 方法，复用 RAGTool 的检索逻辑
- [ ] T053 [US3] 在 src/tools/file_search.py 中实现 execute() 调用 VectorStore.search_all() 执行语义检索
- [ ] T054 [US3] 在 src/tools/file_search.py 中实现格式化输出：文件名、路径、相似度、内容片段
- [ ] T055 [US3] 在 src/tools/file_search.py 中添加语义检索日志记录到 logs/file_operations.log（遵循章程：可审计性与透明性）
- [ ] T056 [US3] 在 src/tools/file_search.py 中实现错误处理：无索引文件、未找到结果、API失败

---

## 阶段 5.5: 版本控制检查点

**目的**: 确保用户故事 3 完成并通过验证

- [ ] T057 在 tests/unit/tools/test_file_search.py 中编写单元测试验证语义检索工具
- [ ] T058 运行语义检索工具单元测试，验证检索逻辑和错误处理（遵循章程：版本控制与测试纪律）
- [ ] T059 提交用户故事 3 代码，清晰描述"FileSemanticSearchTool实现完成"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 此时，P1组核心功能测试（US1、US2、US3）应该全部完成

---

## 阶段 6: 用户故事 4 - 串行工具调用功能 (优先级: P2)

**目标**: 更新Agent提示词，支持文件操作的串行工具调用

**独立测试**: 用户可以发出"把关于性能分析的报告发给我"的请求，验证Agent先搜索再下载

### 用户故事 4 的实施

- [ ] T060 [P] [US4] 在 src/server/agent.py 的 __post_init__ 中注册 file_upload 工具到 self.tools
- [ ] T061 [P] [US4] 在 src/server/agent.py 的 __post_init__ 中注册 file_download 工具到 self.tools
- [ ] T062 [P] [US4] 在 src/server/agent.py 的 __post_init__ 中注册 file_semantic_search 工具到 self.tools
- [ ] T063 [US4] 在 src/server/agent.py 的 _think_and_decide() 系统提示词中添加"文件操作场景"部分
- [ ] T064 [US4] 在系统提示词中添加文件上传示例（用户说"上传文件"→file_upload）
- [ ] T065 [US4] 在系统提示词中添加文件下载示例（用户说"发给我"→file_download）
- [ ] T066 [US4] 在系统提示词中添加语义检索示例（用户说"搜索XX文件"→file_semantic_search）
- [ ] T067 [US4] 在系统提示词中添加串行调用示例（先file_semantic_search再file_download）
- [ ] T068 [US4] 验证ReAct循环支持串行调用（current_message传递工具结果）

---

## 阶段 6.5: 版本控制检查点

**目的**: 确保用户故事 4 完成并通过验证

- [ ] T069 在 tests/integration/test_file_tools_integration.py 中编写集成测试验证串行工具调用
- [ ] T070 运行集成测试验证"搜索+下载"串行调用流程（遵循章程：版本控制与测试纪律）
- [ ] T071 提交用户故事 4 代码，清晰描述"串行工具调用功能实现完成"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 此时，P1+P2核心功能测试（US1-US4）应该全部完成

---

## 阶段 7: 用户故事 5 - 文件管理功能 (优先级: P3)

**目标**: 实现文件列表、删除等管理操作

**独立测试**: 用户可以查看文件列表、删除文件并验证结果

### 用户故事 5 的实施

- [ ] T072 [P] [US5] 在 src/tools/file_manage.py 中创建 FileManageTool 类，继承 Tool 基类
- [ ] T073 [P] [US5] 在 src/tools/file_manage.py 中实现 list_files() 操作，列出已上传文件
- [ ] T074 [P] [US5] 在 src/tools/file_manage.py 中实现 delete_file() 操作，删除文件和索引
- [ ] T075 [P] [US5] 在 src/tools/file_manage.py 中实现 reindex_file() 操作，重新建立索引
- [ ] T076 [US5] 在 src/tools/file_manage.py 中添加文件管理日志记录到 logs/file_operations.log（遵循章程：可审计性与透明性）
- [ ] T077 [US5] 在 src/server/agent.py 的 __post_init__ 中注册 file_manage 工具到 self.tools
- [ ] T078 [US5] 在 _think_and_decide() 系统提示词中添加文件管理示例（"查看文件"、"删除文件"）

---

## 阶段 7.5: 版本控制检查点

**目的**: 确保用户故事 5 完成并通过验证

- [ ] T079 在 tests/unit/tools/test_file_manage.py 中编写单元测试验证文件管理工具
- [ ] T080 运行文件管理工具单元测试，验证列表、删除、重新索引功能（遵循章程：版本控制与测试纪律）
- [ ] T081 提交用户故事 5 代码，清晰描述"FileManageTool实现完成"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 所有用户故事（P1、P2、P3）现在应该全部完成并通过验证

---

## 阶段 8: 完善与横切关注点

**目的**: 生成汇总文档，更新文档，确保整体质量

- [ ] T082 [P] 生成汇总测试报告，包含所有工具的测试结果
- [ ] T083 [P] 分析所有文件操作的性能指标，验证是否符合目标（上传≤30s、下载≤20s、检索≤3s）
- [ ] T084 [P] 更新 README.md 或相关文档，说明如何使用文件操作工具（参考 quickstart.md）
- [ ] T085 [P] 代码清理和重构，确保工具代码质量符合项目规范
- [ ] T086 运行 quickstart.md 中的所有示例命令，验证文档准确性（遵循章程：版本控制与测试纪律）
- [ ] T087 在 logs/file_operations.log 中记录所有测试执行的汇总日志

---

## 阶段 8.5: 最终版本控制检查点

**目的**: 确保所有工作完成并通过最终验证后进行版本提交

- [ ] T088 运行所有文件工具的单元测试和集成测试，确保100%通过（遵循所有成功标准）
- [ ] T089 验证所有5个工具已集成到Agent并正常工作
- [ ] T090 验证文件操作性能指标符合所有目标（SC-001到SC-010）
- [ ] T091 验证安全机制：路径白名单、黑名单、文件类型验证、大小限制全部生效
- [ ] T092 提交最终代码，清晰描述"文件操作工具集成到Agent功能全部完成"和完整测试结果（遵循章程：版本控制与测试纪律）

---

## 依赖关系与执行顺序

### 阶段依赖关系

- **设置(阶段 1)**: 依赖现有基础设施 - 立即可开始
- **基础(阶段 2)**: 依赖设置完成 - 验证现有组件
- **用户故事(阶段 3-7)**: 都依赖于基础验证完成
  - 用户故事 1-3(P1) 可以并行开发（不同工具）
  - 用户故事 4(P2) 依赖用户故事 1-3（需要工具已实现）
  - 用户故事 5(P3) 可以与用户故事 1-3 并行开发
- **完善(阶段 8)**: 依赖所有用户故事完成

### 用户故事依赖关系

- **用户故事 1-3(P1)**: 三个核心工具（上传、下载、检索）可以独立并行开发
- **用户故事 4(P2)**: 依赖用户故事 1-3（需要工具已注册到Agent）
- **用户故事 5(P3)**: 独立于其他用户故事（文件管理功能）
- **用户故事独立性**: 每个工具可以独立开发和测试

### 每个用户故事内部

- 验证规则按顺序实现（文件名→大小→类型）
- validate_args() 可以并行实现（不同验证规则）
- execute() 在 validate_args() 之后实现
- 日志记录与 execute() 并行实现

### 并行机会

- 阶段 2: 4个并行任务（T019、T020、T021、T022）
- 用户故事 1: 4个并行验证任务（T028、T029、T030+未列出的其他）
- 用户故事 2: 4个并行验证任务（T039、T040、T041+未列出的其他）
- 用户故事 3: 2个并行验证任务（T050、T051）
- 用户故事 4: 3个并行注册任务（T060、T061、T062）
- 用户故事 5: 4个并行操作任务（T073、T074、T075+未列出的其他）
- 阶段 8: 4个并行任务（T082、T083、T084、T086）

---

## 并行示例: 用户故事 1（文件上传功能）

```bash
# 一起启动用户故事 1 的所有验证任务（并行实现）:
T028: 实现文件名验证（无路径遍历）
T029: 实现文件大小验证（≤10MB）
T030: 实现内容类型验证（仅文本文件）

# 验证任务完成后，按顺序执行:
T031: 实现execute()方法（保存文件）
T032: 实现自动索引（调用IndexManager）
T033: 添加日志记录
T034: 实现错误处理
```

---

## 实施策略

### 仅 MVP（仅用户故事 1-3，P1功能）

1. 完成阶段 1: 设置（日志配置）
2. 完成阶段 2: 基础（验证现有组件）
3. 完成阶段 3-5: 用户故事 1-3(P1核心工具)
4. **停止并验证**: 运行所有P1工具测试，确认MVP达成
5. 生成汇总报告，验证P1功能100%通过

### 增量交付（推荐）

1. 完成设置 + 基础 → 基础设施验证
2. 添加用户故事 1-3(P1) → 独立测试 → 提交版本（核心MVP!）
3. 添加用户故事 4(P2) → 集成测试 → 提交版本（串行调用）
4. 添加用户故事 5(P3) → 单元测试 → 提交版本（文件管理）
5. 完善与横切关注点 → 最终验证 → 提交版本
6. 每个阶段在不破坏先前测试的情况下增加价值

---

## 任务汇总

- **总任务数**: 92
- **设置任务数**: 9（T001-T009）
- **基础任务数**: 17（T010-T026）
- **用户故事任务数**: 52（T027-T081）
  - US1(P1): 8个任务（文件上传工具）
  - US2(P1): 8个任务（文件下载工具）
  - US3(P1): 8个任务（语义检索工具）
  - US4(P2): 9个任务（串行工具调用）
  - US5(P3): 10个任务（文件管理）
- **完善任务数**: 14（T082-T092）

### 已完成任务统计

- **已完成**: 17个任务（T001-T017，基础设施）
- **待完成**: 75个任务（T018-T092）
- **完成率**: 18.5%

### 识别的并行机会

- **阶段 2**: 4个并行任务（验证配置）
- **用户故事阶段**: 每个用户故事有2-4个并行验证/操作任务
- **总体**: 约30%的任务（28个）可并行执行

### 每个用户故事的独立测试标准

- **US1(文件上传)**: 运行test_file_upload.py，验证文件接收、验证、索引功能
- **US2(文件下载)**: 运行test_file_download.py，验证路径验证、下载提议、文件传输
- **US3(语义检索)**: 运行test_file_search.py，验证查询处理、检索结果、错误处理
- **US4(串行调用)**: 运行test_file_tools_integration.py，验证"搜索+下载"串行流程
- **US5(文件管理)**: 运行test_file_manage.py，验证列表、删除、重新索引功能

### 建议的 MVP 范围

**MVP = 用户故事 1-3(P1核心工具) + 用户故事 4(P2串行调用)**

- T001-T026: 设置和基础验证（26个任务，其中17个已完成）
- T027-T068: 用户故事 1-4（42个任务）
- **总计**: 68个任务（其中17个已完成）
- **新增任务**: 51个任务
- **预计工作量**: 核心文件操作工具（上传、下载、检索）+ 串行调用

**MVP达成标准**:
- 所有P1工具（US1-US3）通过单元测试
- US4（串行调用）通过集成测试
- 工具已注册到Agent并可通过自然语言调用
- 验证SC-001到SC-010成功标准

---

## 注意事项

- [P] 任务 = 不同文件，无依赖关系，可并行执行
- [Story] 标签将任务映射到特定用户故事以实现可追溯性
- 每个用户故事测试应该独立可运行和可验证
- 测试必须使用真实的智谱API和真实文件（遵循章程：测试真实性）
- 在每个检查点停止以独立验证故事
- 所有测试代码注释和错误消息使用中文（遵循章程：语言规范）
- 避免模糊任务、相同文件冲突、破坏独立性的跨故事依赖
- **[已完成]** 任务已在现有代码中实现，但仍需验证
