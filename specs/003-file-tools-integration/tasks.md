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

## 阶段 3: 用户故事 1 - 语义检索功能 (优先级: P1) 🎯 MVP

**目标**: 实现统一的语义检索工具（合并RAG和file_semantic_search），支持混合检索策略（精确→模糊→语义）

**独立测试**: 用户可以用自然语言搜索文件内容，验证Agent能够找到正确文件

**设计原则**: 遵循章程 v1.5.1 - 工具职责单一原则、混合检索策略原则

### 用户故事 1 的实施

- [ ] T027 [P] [US1] 在 src/tools/semantic_search.py 中创建 SemanticSearchTool 类，继承 Tool 基类（合并RAG和FileSemanticSearch）
- [ ] T028 [P] [US1] 在 src/tools/semantic_search.py 中实现 validate_args() 验证查询非空、top_k范围（1-10）、scope参数（all/system/uploads）
- [ ] T029 [P] [US1] 在 src/tools/semantic_search.py 中实现 _is_exact_filename() 判断查询是否为精确文件名（如config.yaml）
- [ ] T030 [P] [US1] 在 src/tools/semantic_search.py 中实现 _search_exact_filename() 精确文件名匹配（similarity=1.0，match_type为exact_filename）
- [ ] T031 [P] [US1] 在 src/tools/semantic_search.py 中实现 _search_fuzzy_filename() 模糊匹配（关键词/前缀/通配符，match_type为fuzzy_filename）
- [ ] T032 [US1] 在 src/tools/semantic_search.py 中实现 _search_semantic() 向量语义检索（match_type为semantic，作为兜底策略）
- [ ] T033 [US1] 在 src/tools/semantic_search.py 中实现 execute() 方法，按优先级执行三层检索（精确→模糊→语义）
- [ ] T034 [US1] 在 src/tools/semantic_search.py 中实现结果合并和去重逻辑，按相似度排序返回top_k结果
- [ ] T035 [US1] 在 src/tools/semantic_search.py 中实现格式化输出：文件名、路径、相似度、match_type、内容片段
- [ ] T036 [US1] 在 src/tools/semantic_search.py 中添加语义检索日志记录到 logs/file_operations.log（遵循章程：可审计性与透明性）
- [ ] T037 [US1] 在 src/tools/semantic_search.py 中实现错误处理：无索引文件、未找到结果、API失败（返回ToolExecutionResult格式）
- [ ] T038 [US1] 删除 src/tools/rag.py（RAGTool已合并到SemanticSearchTool）
- [ ] T039 [US1] 删除 src/tools/file_search.py（FileSemanticSearchTool已合并到SemanticSearchTool）

---

## 阶段 3.5: 版本控制检查点

**目的**: 确保用户故事 1 完成并通过验证

- [ ] T040 在 tests/unit/tools/test_semantic_search.py 中编写单元测试验证语义检索工具
- [ ] T041 运行语义检索工具单元测试，验证三层检索策略（精确→模糊→语义）和错误处理（遵循章程：版本控制与测试纪律）
- [ ] T042 提交用户故事 1 代码，清晰描述"SemanticSearchTool实现完成（混合检索策略）"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 此时，用户故事 1（语义检索）应该完全功能化且可独立测试

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

## 阶段 5: 用户故事 3 - 文件索引管理功能 (优先级: P1)

**目标**: 重新定义file_upload为文件索引和上下文管理工具，支持代词引用（"这个文件"、"之前上传的"）

**独立测试**: 用户可以通过代词引用上传的文件，验证Agent能够正确定位文件

**设计原则**: 遵循章程 v1.5.1 - 协议层分离原则（Agent不处理实际文件上传，协议层处理）

### 用户故事 3 的实施

- [ ] T049 [P] [US3] 扩展 Session 类（src/server/nplt_server.py），添加 uploaded_files 字段（List[Dict]），记录文件元数据
- [ ] T050 [P] [US3] 扩展 Session 类，添加 upload_state 字段（Dict），跟踪当前上传状态
- [ ] T051 [P] [US3] 在 Session 类中实现 get_last_uploaded_file() 方法，获取最后上传的文件
- [ ] T052 [P] [US3] 在 Session 类中实现 get_uploaded_file(file_id) 方法，根据file_id获取文件信息
- [ ] T053 [US3] 在 src/tools/file_upload.py 中重新定义 FileUploadTool 类为文件索引管理工具（不处理文件上传）
- [ ] T054 [US3] 在 src/tools/file_upload.py 中实现 list_files(action, reference, file_type, count, time_range) 方法
- [ ] T055 [US3] 在 src/tools/file_upload.py 中实现代词引用解析（"this"→最新1个，"these"→最新N个，"previous"→之前，"all"→全部）
- [ ] T056 [US3] 在 src/tools/file_upload.py 中实现时间范围过滤（recent、before、today）
- [ ] T057 [US3] 在 src/tools/file_upload.py 中实现文件类型过滤（file_type参数，如"log"、"yaml"）
- [ ] T058 [US3] 在 src/server/nplt_server.py 的 _handle_file_data() 中，保存文件后记录到 session.uploaded_files
- [ ] T059 [US3] 在 src/server/nplt_server.py 中实现 extract_file_reference(text) 解析文件引用标记 [file_ref:{file_id}]
- [ ] T060 [US3] 在 src/server/nplt_server.py 的 _handle_chat_text() 中，检测文件引用并附加到对话历史
- [ ] T061 [US3] 在 src/tools/file_upload.py 中添加文件索引日志记录到 logs/file_operations.log（遵循章程：可审计性与透明性）
- [ ] T062 [US3] 在 src/tools/file_upload.py 中实现错误处理：无上传文件、引用失败、file_id无效（返回ToolExecutionResult格式）

---

## 阶段 5.5: 版本控制检查点

**目的**: 确保用户故事 3 完成并通过验证

- [ ] T063 在 tests/unit/tools/test_file_upload.py 中编写单元测试验证文件索引管理工具
- [ ] T064 运行文件索引管理工具单元测试，验证代词引用、时间范围、文件类型过滤（遵循章程：版本控制与测试纪律）
- [ ] T065 提交用户故事 3 代码，清晰描述"FileUploadTool重新定义为文件索引管理工具"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 此时，P1组核心功能测试（US1、US2、US3）应该全部完成

---

## 阶段 6: 用户故事 4 - Agent工具集成 (优先级: P1)

**目标**: 更新Agent工具注册和系统提示词，集成5个工具（sys_monitor、command_executor、semantic_search、file_download、file_upload）

**独立测试**: 用户可以通过自然语言调用所有工具，验证Agent能够正确选择和执行工具

**设计原则**: 遵循章程 v1.5.1 - Agent工具清单规范（5-7个工具）

### 用户故事 4 的实施

- [ ] T066 [P] [US4] 在 src/server/agent.py 的 __post_init__ 中注册 semantic_search 工具（合并后的统一检索工具）
- [ ] T067 [P] [US4] 在 src/server/agent.py 的 __post_init__ 中注册 file_download 工具
- [ ] T068 [P] [US4] 在 src/server/agent.py 的 __post_init__ 中注册 file_upload 工具（重新定义为索引管理工具）
- [ ] T069 [P] [US4] 在 src/server/agent.py 中验证 sys_monitor 和 command_executor 工具已注册（现有工具，保持不变）
- [ ] T070 [US4] 在 _think_and_decide() 系统提示词中更新"工具使用示例"部分，反映新的5个工具清单
- [ ] T071 [US4] 在系统提示词中添加 semantic_search 示例（"搜索配置说明"→semantic_search，"找一下日志文件"→semantic_search）
- [ ] T072 [US4] 在系统提示词中添加 file_download 示例（"下载config.yaml"→semantic_search定位→file_download准备下载）
- [ ] T073 [US4] 在系统提示词中添加 file_upload 示例（"这个文件里数据库端口是多少？"→file_upload.list_files引用→读取文件并回答）
- [ ] T074 [US4] 在系统提示词中添加混合检索策略说明（精确匹配优先→模糊匹配→语义检索兜底）
- [ ] T075 [US4] 在系统提示词中添加串行调用示例（semantic_search定位文件→file_download准备下载）
- [ ] T076 [US4] 在系统提示词中添加文件上传场景示例（刚上传文件+用户文本→Agent自动检测session.uploaded_files→分析文件）
- [ ] T077 [US4] 验证ReAct循环支持串行调用（current_message传递工具结果）
- [ ] T078 [US4] 移除系统提示词中所有关于RAG和file_semantic_search的示例（已合并到semantic_search）

---

## 阶段 6.5: 版本控制检查点

**目的**: 确保用户故事 4 完成并通过验证

- [ ] T079 在 tests/integration/test_agent_tools.py 中编写集成测试验证工具注册和调用
- [ ] T080 运行集成测试验证Agent能够正确选择5个工具（遵循章程：版本控制与测试纪律）
- [ ] T081 提交用户故事 4 代码，清晰描述"Agent工具集成完成（5个工具）"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 此时，P1核心功能测试（US1-US4）应该全部完成，Agent已集成5个工具

---

## 阶段 7: 综合功能测试 (优先级: P0) 🎯 必需

**目标**: 使用真实智谱API对每个功能进行不少于8个模拟用户输入的测试，验证完整的工具调用链

**设计原则**: 遵循章程 v1.5.1 - 测试真实性原则（绝对不允许mock，必须使用真实智谱API）

### 测试要求

- 每个功能（工具）不少于8个测试用例
- 必须使用真实的智谱API（glm-4-flash或glm-4.5-flash免费模型）
- 必须记录所有输入输出、工具/工具链调用情况
- 必须验证工具选择准确率、调用成功率、结果准确性

### 综合测试实施

#### 语义检索功能测试（semantic_search）

- [ ] T082 [P] [测试] 编写测试用例1：精确文件名查询（"config.yaml"）→ 验证精确匹配（similarity=1.0，match_type=exact_filename）
- [ ] T083 [P] [测试] 编写测试用例2：模糊文件名查询（"config"）→ 验证模糊匹配（返回config.yaml、config.json、config.yml，match_type=fuzzy_filename）
- [ ] T084 [P] [测试] 编写测试用例3：自然语言查询（"数据库配置在哪里"）→ 验证语义检索（match_type=semantic）
- [ ] T085 [P] [测试] 编写测试用例4：系统文档查询（"搜索README中的安装说明"）→ 验证scope=system检索
- [ ] T086 [P] [测试] 编写测试用例5：用户文件查询（"我上传的日志文件"）→ 验证scope=uploads检索
- [ ] T087 [P] [测试] 编写测试用例6：全局查询（"所有关于性能的文档"）→ 验证scope=all检索
- [ ] T088 [P] [测试] 编写测试用例7：混合检索优先级（"config.yaml"）→ 验证精确匹配优先，不走向量检索
- [ ] T089 [P] [测试] 编写测试用例8：无结果处理（"不存在的文件xyz123"）→ 验证友好的错误消息
- [ ] T090 [测试] 运行所有semantic_search测试用例，使用真实智谱API
- [ ] T091 [测试] 记录所有测试的输入输出、工具调用情况、match_type分布

#### 文件下载功能测试（file_download）

- [ ] T092 [P] [测试] 编写测试用例1：精确文件下载（"下载config.yaml"）→ 验证semantic_search定位→file_download准备下载
- [ ] T093 [P] [测试] 编写测试用例2：模糊文件下载（"下载配置文件"）→ 验证semantic_search模糊匹配→file_download准备下载
- [ ] T094 [P] [测试] 编写测试用例3：语义查询下载（"下载数据库配置"）→ 验证semantic_search语义检索→file_download准备下载
- [ ] T095 [P] [测试] 编写测试用例4：路径白名单验证（"下载/etc/passwd"）→ 验证路径被拒绝，返回明确错误消息
- [ ] T096 [P] [测试] 编写测试用例5：黑名单验证（"下载.env文件"）→ 验证黑名单文件被拒绝
- [ ] T097 [P] [测试] 编写测试用例6：文件不存在（"下载不存在的文件.txt"）→ 验证友好错误消息
- [ ] T098 [P] [测试] 编写测试用例7：串行调用（"把关于性能分析的报告发给我"）→ 验证semantic_search→file_download完整调用链
- [ ] T099 [P] [测试] 编写测试用例8：大文件下载（"下载大文件"）→ 验证分块传输（如果有测试大文件）
- [ ] T100 [测试] 运行所有file_download测试用例，使用真实智谱API
- [ ] T101 [测试] 记录所有测试的输入输出、工具调用链、成功率

#### 文件索引管理功能测试（file_upload - 重新定义）

- [ ] T102 [P] [测试] 编写测试用例1：代词引用"这个文件"（刚上传文件后问"这个文件的内容是什么？"）→ 验证file_upload.list_files(reference="this")
- [ ] T103 [P] [测试] 编写测试用例2：代词引用"这些文件"（上传多个文件后问"对比这些文件"）→ 验证file_upload.list_files(reference="these", count=2)
- [ ] T104 [P] [测试] 编写测试用例3：代词引用"之前上传的"（上传新文件后问"之前上传的日志文件"）→ 验证file_upload.list_files(reference="previous", file_type="log")
- [ ] T105 [P] [测试] 编写测试用例4：时间范围过滤（"我刚才上传的文件"）→ 验证time_range="recent"
- [ ] T106 [P] [测试] 编写测试用例5：文件类型过滤（"我上传的YAML文件"）→ 验证file_type="yaml"
- [ ] T106b [P] [测试] 编写测试用例6：Session隔离（上传文件到会话A，切换会话B后问"这个文件"）→ 验证不会返回会话A的文件
- [ ] T106c [P] [测试] 编写测试用例7：无文件引用（未上传文件直接问"这个文件"）→ 验证友好错误消息
- [ ] T106d [P] [测试] 编写测试用例8：上传+分析（上传config.yaml + "分析这个配置文件"）→ 验证协议层上传→session记录→Agent分析完整流程
- [ ] T107 [测试] 运行所有file_upload测试用例，使用真实智谱API
- [ ] T108 [测试] 记录所有测试的输入输出、代词解析结果、Session状态

#### 系统工具测试（sys_monitor + command_executor）

- [ ] T109 [P] [测试] 编写测试用例1：系统监控（"CPU使用率是多少？"）→ 验证sys_monitor正确返回CPU使用率
- [ ] T110 [P] [测试] 编写测试用例2：内存监控（"内存使用情况如何？"）→ 验证sys_monitor正确返回内存使用率
- [ ] T111 [P] [测试] 编写测试用例3：简单命令（"执行ls -la"）→ 验证command_executor正确执行并返回结果
- [ ] T112 [P] [测试] 编写测试用例4：命令黑名单（"执行rm -rf /"）→ 验证黑名单命令被拒绝
- [ ] T113 [P] [测试] 编写测试用例5：命令白名单（"执行cat config.yaml"）→ 验证白名单命令允许执行
- [ ] T114 [P] [测试] 编写测试用例6：命令超时（"执行sleep 100"）→ 验证超时机制生效
- [ ] T115 [P] [测试] 编写测试用例7：命令输出限制（"执行cat largefile.log"）→ 验证输出大小限制100KB
- [ ] T116 [P] [测试] 编写测试用例8：串行命令（"先ls再grep"）→ 验证多次command_executor调用
- [ ] T117 [测试] 运行所有系统工具测试用例，使用真实智谱API
- [ ] T118 [测试] 记录所有测试的输入输出、命令执行结果、安全验证

---

## 阶段 7.5: 版本控制检查点

**目的**: 确保所有综合测试完成并通过验证

- [ ] T119 [测试] 统计所有测试用例的通过率（目标：≥95%，40/42以上通过）
- [ ] T120 [测试] 分析失败用例的根本原因（工具选择错误、参数错误、执行错误、结果不符）
- [ ] T121 [测试] 生成完整测试报告，包含所有输入输出、工具/工具链调用情况（遵循章程：可审计性与透明性）
- [ ] T122 [测试] 提交测试代码和测试报告，清晰描述"综合功能测试完成"和测试结果（遵循章程：版本控制与测试纪律）

**检查点**: 所有功能的综合测试应该全部完成，每个功能≥8个测试用例，使用真实智谱API

---

## 阶段 8: 完善与横切关注点

**目的**: 生成汇总文档，更新文档，确保整体质量

- [ ] T123 [P] 生成汇总测试报告，包含所有5个工具的测试结果（semantic_search、file_download、file_upload、sys_monitor、command_executor）
- [ ] T124 [P] 分析所有文件操作的性能指标，验证是否符合目标（检索≤3s、下载≤20s）
- [ ] T125 [P] 更新 docs/agent_complete_specification.md，反映最终的5个工具设计和混合检索策略
- [ ] T126 [P] 在 docs/ 目录添加工具设计规范文档，详细说明5个工具的职责边界、输入输出格式、调用链路
- [ ] T127 [P] 代码清理和重构，确保工具代码质量符合项目规范，代码重复率≤20%
- [ ] T128 [P] 验证所有设计文档、代码、测试符合constitution v1.5.1的所有原则
- [ ] T129 在 logs/file_operations.log 中记录所有测试执行的汇总日志

---

## 阶段 8.5: 最终版本控制检查点

**目的**: 确保所有工作完成并通过最终验证后进行版本提交

- [ ] T130 运行所有文件工具的单元测试和集成测试，确保≥95%通过率（遵循所有成功标准）
- [ ] T131 验证所有5个工具已集成到Agent并正常工作（sys_monitor、command_executor、semantic_search、file_download、file_upload）
- [ ] T132 验证混合检索策略正确实施（精确匹配→模糊匹配→语义检索三层）
- [ ] T133 验证安全机制：路径白名单、黑名单、文件类型验证、大小限制、命令白名单黑名单全部生效
- [ ] T134 验证Session扩展正确实施（uploaded_files、upload_state字段、文件引用解析）
- [ ] T135 验证协议层分离原则：file_upload不处理实际文件上传，协议层处理上传/下载
- [ ] T136 提交最终代码，清晰描述"5个Agent工具实现完成（Constitution v1.5.1）"和完整测试结果（遵循章程：版本控制与测试纪律）

---

## 依赖关系与执行顺序

### 阶段依赖关系

- **设置(阶段 1)**: 依赖现有基础设施 - 立即可开始
- **基础(阶段 2)**: 依赖设置完成 - 验证现有组件
- **用户故事(阶段 3-6)**: 都依赖于基础验证完成
  - 用户故事 1(语义检索) 优先级最高（其他工具依赖它）
  - 用户故事 2(文件下载) 可以并行开发
  - 用户故事 3(文件索引管理) 可以并行开发
  - 用户故事 4(Agent集成) 依赖用户故事 1-3（需要工具已实现）
- **综合测试(阶段 7)**: 依赖所有用户故事完成
- **完善(阶段 8)**: 依赖所有测试完成

### 用户故事依赖关系

- **用户故事 1(语义检索)**: 最高优先级，是file_download的前置依赖
- **用户故事 2(文件下载)**: 依赖用户故事 1（需要semantic_search定位文件）
- **用户故事 3(文件索引管理)**: 独立于用户故事 1-2（Session扩展可独立开发）
- **用户故事 4(Agent集成)**: 依赖用户故事 1-3（需要所有工具已实现）
- **用户故事独立性**: 每个工具可以独立开发和测试（除了依赖关系）

### 每个用户故事内部

- 语义检索：精确匹配→模糊匹配→语义检索按顺序实现
- 文件下载：路径验证→下载准备→错误处理按顺序实现
- 文件索引管理：Session扩展→文件引用解析→代词解析按顺序实现
- Agent集成：工具注册→提示词更新→验证测试按顺序实现

### 并行机会

- 阶段 2: 4个并行任务（T019、T020、T021、T022）
- 用户故事 1: 3个并行检索实现任务（T030、T031、T032）
- 用户故事 2: 3个并行验证任务（T039、T040、T041）
- 用户故事 3: 4个并行Session扩展任务（T049、T050、T051、T052）
- 用户故事 4: 3个并行工具注册任务（T066、T067、T068）
- 阶段 7(测试): 所有测试用例编写可以并行（T082-T089, T092-T099, T102-T106d, T109-T116）
- 阶段 8: 4个并行文档任务（T123、T124、T125、T126）

---

## 并行示例: 用户故事 1（语义检索功能）

```bash
# 一起启动用户故事 1 的所有检索实现任务（并行实现）:
T029: 实现_is_exact_filename()判断（精确文件名识别）
T030: 实现_search_exact_filename()（精确匹配，similarity=1.0）
T031: 实现_search_fuzzy_filename()（模糊匹配，关键词/前缀/通配符）
T032: 实现_search_semantic()（向量语义检索，兜底策略）

# 检索实现完成后，按顺序执行:
T033: 实现execute()方法（按优先级执行三层检索）
T034: 实现结果合并和去重逻辑
T035: 实现格式化输出（match_type字段）
T036: 添加日志记录
T037: 实现错误处理
```

---

## 实施策略

### 仅 MVP（仅用户故事 1-4，P1功能）

1. 完成阶段 1: 设置（日志配置）
2. 完成阶段 2: 基础（验证现有组件）
3. 完成阶段 3-6: 用户故事 1-4(P1核心工具 + Agent集成)
4. **停止并验证**: 运行所有P1工具测试，确认MVP达成
5. 生成汇总报告，验证P1功能100%通过

### 增量交付（推荐）

1. 完成设置 + 基础 → 基础设施验证
2. 添加用户故事 1-3(P1) → 独立测试 → 提交版本（核心工具: semantic_search、file_download、file_upload）
3. 添加用户故事 4(P1) → 集成测试 → 提交版本（Agent工具集成）
4. 添加阶段 7(P0) → 综合测试 → 提交版本（42个测试用例，真实智谱API）
5. 完善与横切关注点 → 最终验证 → 提交版本
6. 每个阶段在不破坏先前测试的情况下增加价值

---

## 任务汇总

- **总任务数**: 136（更新后）
- **设置任务数**: 9（T001-T009）
- **基础任务数**: 17（T010-T026）
- **用户故事任务数**: 55（T027-T081）
  - US1(P1): 13个任务（semantic_search工具，合并RAG+FileSearch，实施混合检索策略）
  - US2(P1): 8个任务（file_download工具）
  - US3(P1): 14个任务（file_upload重新定义 + Session扩展）
  - US4(P1): 13个任务（Agent工具集成 + 系统提示词更新）
- **综合测试任务数**: 41（T082-T122）
  - semantic_search: 10个任务（8个测试用例 + 运行 + 记录）
  - file_download: 10个任务（8个测试用例 + 运行 + 记录）
  - file_upload: 7个任务（8个测试用例 + 运行 + 记录）
  - sys_monitor + command_executor: 10个任务（8个测试用例 + 运行 + 记录）
  - 测试汇总和分析: 4个任务
- **完善任务数**: 14（T123-T136）

### 已完成任务统计

- **已完成**: 17个任务（T001-T017，基础设施）
- **待完成**: 119个任务（T018-T136）
- **完成率**: 12.5%

### 识别的并行机会

- **阶段 2**: 4个并行任务（验证配置）
- **用户故事阶段**: 每个用户故事有2-4个并行验证/操作任务
- **综合测试阶段**: 所有42个测试用例编写可以并行
- **总体**: 约35%的任务（48个）可并行执行

### 每个用户故事的独立测试标准

- **US1(语义检索)**: 运行test_semantic_search.py，验证混合检索策略（精确→模糊→语义）、scope过滤、match_type字段
- **US2(文件下载)**: 运行test_file_download.py，验证路径验证、下载准备、错误处理
- **US3(文件索引管理)**: 运行test_file_upload.py，验证代词引用、时间范围、文件类型过滤、Session隔离
- **US4(Agent集成)**: 运行test_agent_tools.py，验证5个工具注册、工具选择准确率、串行调用

### 综合测试标准（阶段 7）

- **semantic_search**: 8个测试用例，验证精确匹配、模糊匹配、语义检索、scope过滤、优先级、错误处理
- **file_download**: 8个测试用例，验证精确/模糊/语义下载、路径白名单黑名单、串行调用
- **file_upload**: 8个测试用例，验证代词引用、时间范围、文件类型、Session隔离、上传+分析流程
- **sys_monitor + command_executor**: 8个测试用例，验证系统监控、命令执行、白名单黑名单、超时、输出限制
- **测试要求**: 必须使用真实智谱API（glm-4-flash或glm-4.5-flash），禁止mock
- **目标通过率**: ≥95%（40/42以上通过）

### 建议的 MVP 范围

**MVP = 用户故事 1-4(P1核心工具 + Agent集成) + 阶段 7 综合测试**

- T001-T026: 设置和基础验证（26个任务，其中17个已完成）
- T027-T081: 用户故事 1-4（55个任务）
- T082-T122: 综合测试（41个任务，42个测试用例）
- **总计**: 122个任务（其中17个已完成）
- **新增任务**: 105个任务
- **预计工作量**: 5个核心工具（semantic_search、file_download、file_upload、sys_monitor、command_executor）+ 42个综合测试用例

**MVP达成标准**:
- 所有P1工具（US1-US4）通过单元测试
- 5个工具已注册到Agent并可通过自然语言调用
- 混合检索策略正确实施（精确→模糊→语义）
- Session扩展正确实施（uploaded_files、upload_state）
- 42个综合测试用例≥95%通过率（真实智谱API）
- 验证constitution v1.5.1的所有设计原则

---

## 关键设计原则（Constitution v1.5.1）

### 工具职责单一原则
- 每个工具只做一件事并做好一件事
- 功能相同的工具必须合并（RAG + FileSemanticSearch → semantic_search）
- 代码重复率必须控制在20%以下

### 协议层分离原则
- Agent工具不处理实际数据传输（上传/下载由协议层处理）
- file_upload重新定义为文件索引管理工具
- Agent负责决策和协调，协议层负责数据传输

### 混合检索策略原则（v1.5.1新增，强制性）
- 文件检索必须实施三层策略：精确匹配→模糊匹配→语义检索
- 精确匹配优先（"config.yaml" → similarity=1.0）
- 模糊匹配次之（"config" → config.yaml、config.json、config.yml）
- 语义检索兜底（"数据库配置在哪里" → 向量检索）
- 结果必须包含match_type字段（exact_filename/fuzzy_filename/semantic）

### Agent工具清单规范
- 工具总数应控制在5-7个范围内
- 当前设计：5个工具（sys_monitor、command_executor、semantic_search、file_download、file_upload）

---

## 注意事项

- [P] 任务 = 不同文件，无依赖关系，可并行执行
- [Story] 标签将任务映射到特定用户故事以实现可追溯性
- 每个用户故事测试应该独立可运行和可验证
- **测试必须使用真实的智谱API**（glm-4-flash或glm-4.5-flash免费模型），绝对不允许mock（遵循章程：测试真实性）
- 在每个检查点停止以独立验证故事
- 所有测试代码注释和错误消息使用中文（遵循章程：语言规范）
- 避免模糊任务、相同文件冲突、破坏独立性的跨故事依赖
- **[已完成]** 任务已在现有代码中实现，但仍需验证
- **混合检索策略是强制性要求**（constitution v1.5.1），必须实施精确→模糊→语义三层检索
- **Session扩展是必需的**，uploaded_files和upload_state字段必须实现
- **file_upload已重新定义**，不再处理文件上传，而是管理文件索引和上下文
