# 任务: Agent功能全面验证测试

**输入**: 来自 `/specs/002-agent-validation-test/` 的设计文档
**前置条件**: plan.md(必需)、spec.md(用户故事必需)、research.md、data-model.md、contracts/

**测试**: 本功能为测试框架，所有任务都是测试相关。

**组织结构**: 任务按用户故事分组，以便每个故事能够独立实施和测试。

## 格式: `[ID] [P?] [Story] 描述`
- **[P]**: 可以并行运行(不同文件，无依赖关系)
- **[Story]**: 此任务属于哪个用户故事(例如: US1、US2、US3...)
- 在描述中包含确切的文件路径

## 路径约定
- **测试项目**: 仓库根目录下的 `tests/validation/`
- **报告输出**: `specs/002-agent-validation-test/reports/`

---

## 阶段 1: 设置(共享基础设施)

**目的**: 测试框架初始化和基本结构

- [ ] T001 创建 tests/validation/ 目录结构(__init__.py, conftest.py, test_framework.py, test_reporter.py, test_agent_validation.py)
- [ ] T002 在 tests/validation/conftest.py 中配置pytest fixtures，包括auto_confirm命令行参数
- [ ] T003 [P] 在 tests/validation/conftest.py 中实现fresh_agent fixture，为每个测试创建新的ReActAgent实例
- [ ] T004 [P] 在 tests/validation/conftest.py 中实现fresh_history fixture，为每个测试创建新的ConversationHistory
- [ ] T005 [P] 在 tests/validation/conftest.py 中实现clean_test_environment autouse fixture，确保测试数据隔离
- [ ] T006 [P] 在 logs/test_validation.log 中创建测试日志文件(遵循章程: 文档与可追溯性)
- [ ] T007 [P] 验证ZHIPU_API_KEY环境变量已配置，在conftest.py中实现pytest_configure钩子检查(遵循章程: 测试真实性)
- [ ] T008 [P] 确保所有测试代码注释使用中文(遵循章程: 语言规范)
- [ ] T009 [P] 确保所有测试错误消息和日志使用中文(遵循章程: 语言规范)

---

## 阶段 1.5: 版本控制检查点

**目的**: 确保设置阶段完成并通过测试后进行版本提交

- [ ] T010 运行pytest --collect-only tests/validation/，验证测试框架结构正确(遵循章程: 版本控制与测试纪律)
- [ ] T011 提交设置阶段代码，清晰描述"测试框架基础设施搭建完成"和验证结果(遵循章程: 版本控制与测试纪律)

---

## 阶段 2: 基础(测试框架核心)

**目的**: 实现测试框架核心类和数据模型，阻塞所有用户故事

**⚠️ 关键**: 在此阶段完成之前，无法开始任何用户故事测试

- [ ] T012 在 tests/validation/test_framework.py 中实现TestCase数据类(id, name, priority, description, user_story, acceptance_scenarios)
- [ ] T013 [P] 在 tests/validation/test_framework.py 中实现AcceptanceScenario数据类(given, when, then, passed)
- [ ] T014 [P] 在 tests/validation/test_framework.py 中实现PerformanceMetrics数据类(总响应时间、工具调用次数、执行时间等)
- [ ] T015 [P] 在 tests/validation/test_framework.py 中实现ValidationResult数据类(场景验证结果)
- [ ] T016 [P] 在 tests/validation/test_framework.py 中实现TestResult数据类(测试结果记录)
- [ ] T017 [P] 在 tests/validation/test_framework.py 中实现TestSuite数据类(测试套件管理)
- [ ] T018 在 tests/validation/test_reporter.py 中实现TestReporter类，包含generate_markdown()方法
- [ ] T019 [P] 在 tests/validation/test_reporter.py 中实现格式化工具调用详情的方法(_format_tool_call)
- [ ] T020 [P] 在 tests/validation/test_reporter.py 中实现格式化性能指标的方法(_format_performance_metrics)
- [ ] T021 [P] 在 tests/validation/test_reporter.py 中实现格式化验收结果的方法(_format_validation_results)
- [ ] T022 在 tests/validation/test_reporter.py 中实现save()方法，保存报告到specs/002-agent-validation-test/reports/
- [ ] T023 [P] 创建specs/002-agent-validation-test/reports/目录，确保测试报告输出路径存在
- [ ] T024 在tests/validation/中实现性能指标收集辅助函数，使用time.perf_counter()记录时间
- [ ] T025 在tests/validation/中实现测试执行辅助类，集成TestRunner和TestReporter

---

## 阶段 2.5: 版本控制检查点

**目的**: 确保测试框架核心完成并通过验证后进行版本提交

- [ ] T026 编写基础单元测试验证TestReporter能够生成符合contracts/test-report-schema.md格式的报告
- [ ] T027 运行所有测试框架单元测试，确保数据模型和报告生成器正常工作(遵循章程: 版本控制与测试纪律)
- [ ] T028 提交测试框架核心代码，清晰描述"测试框架核心实现完成"和测试结果(遵循章程: 版本控制与测试纪律)

**检查点**: 测试框架就绪 - 现在可以开始编写用户故事测试

---

## 阶段 3: 用户故事 1 - 基础对话功能验证(优先级: P1) 🎯 MVP

**目标**: 验证Agent能够进行基础对话，无需调用任何工具

**独立测试**: 运行test_t001_basic_conversation，验证Agent返回友好问候且未调用工具

### 用户故事 1 的测试实现

- [ ] T029 [P] [US1] 在tests/validation/test_agent_validation.py中定义test_t001_basic_conversation测试函数
- [ ] T030 [P] [US1] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent已初始化，当用户发送"你好"，那么返回问候且不调用工具
- [ ] T031 [P] [US1] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent已初始化，当用户问"你是什么？"，那么自我介绍
- [ ] T032 [P] [US1] 在tests/validation/test_agent_validation.py中实现场景3测试：给定Agent已初始化，当用户发送"谢谢"，那么礼貌回应
- [ ] T033 [US1] 在tests/validation/test_agent_validation.py中实现验收逻辑，验证tool_calls为空列表
- [ ] T034 [US1] 在tests/validation/test_agent_validation.py中实现性能指标收集，记录总响应时间
- [ ] T035 [US1] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T001报告
- [ ] T036 [US1] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过
- [ ] T037 [US1] 在tests/validation/test_agent_validation.py中实现验证结果记录，验证SC-001、SC-002、SC-005
- [ ] T037-1 [US1] 在tests/validation/test_agent_validation.py中实现边界测试：给定Agent已初始化，当用户发送空字符串""，那么Agent返回友好提示要求输入有效问题
- [ ] T037-2 [US1] 在tests/validation/test_agent_validation.py中实现边界测试：给定Agent已初始化，当用户发送无意义消息（如乱码"asdfgh"），那么Agent尝试理解并礼貌回应

---

## 阶段 3.5: 版本控制检查点

**目的**: 确保用户故事 1 完成并通过真实API测试后进行版本提交

- [ ] T038 运行test_t001_basic_conversation测试，使用真实智谱API验证Agent基础对话功能(遵循章程: 版本控制与测试纪律)
- [ ] T039 查看生成的报告specs/002-agent-validation-test/reports/T001-基础对话.md，验证报告格式完整
- [ ] T040 提交用户故事 1 代码，清晰描述"T001基础对话功能验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

**检查点**: 此时，用户故事 1(T001)应该完全功能化且可独立测试

---

## 阶段 4: 用户故事 2 - 系统监控工具验证(优先级: P1)

**目标**: 验证Agent正确调用sys_monitor工具，获取CPU、内存、磁盘使用情况

**独立测试**: 运行test_t002_system_monitor，验证Agent调用sys_monitor工具并返回系统状态

### 用户故事 2 的测试实现

- [ ] T041 [P] [US2] 在tests/validation/test_agent_validation.py中定义test_t002_system_monitor测试函数
- [ ] T042 [P] [US2] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent配置sys_monitor工具，当用户问"查看CPU使用率"，那么调用工具参数{"metric": "cpu"}
- [ ] T043 [P] [US2] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent配置sys_monitor工具，当用户问"系统状态如何？"，那么调用工具参数{"metric": "all"}
- [ ] T044 [P] [US2] 在tests/validation/test_agent_validation.py中实现场景3测试：给定Agent配置sys_monitor工具，当用户问"内存使用情况"，那么返回内存信息
- [ ] T045 [US2] 在tests/validation/test_agent_validation.py中实现工具调用验证，检查tool_calls[0].tool_name == "sys_monitor"
- [ ] T046 [US2] 在tests/validation/test_agent_validation.py中实现工具参数验证，检查工具参数符合预期
- [ ] T047 [US2] 在tests/validation/test_agent_validation.py中实现工具执行时间验证，检查duration < 5.0s(符合SC-003)
- [ ] T048 [US2] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T002报告
- [ ] T049 [US2] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过
- [ ] T050 [US2] 在tests/validation/test_agent_validation.py中实现验证结果记录，验证SC-003、SC-004、SC-009

---

## 阶段 4.5: 版本控制检查点

**目的**: 确保用户故事 2 完成并通过真实API测试后进行版本提交

- [ ] T051 运行test_t002_system_monitor测试，使用真实智谱API验证系统监控工具调用(遵循章程: 版本控制与测试纪律)
- [ ] T052 查看生成的报告specs/002-agent-validation-test/reports/T002-系统监控.md，验证工具链调用详情完整
- [ ] T053 提交用户故事 2 代码，清晰描述"T002系统监控工具验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

**检查点**: 此时，用户故事 1 和 2 都应该独立运行

---

## 阶段 5: 用户故事 3 - 命令执行工具验证(优先级: P1)

**目标**: 验证Agent能够安全地执行系统命令(ls, cat, grep等)

**独立测试**: 运行test_t003_command_executor，验证Agent调用command_executor工具并执行命令

### 用户故事 3 的测试实现

- [ ] T054 [P] [US3] 在tests/validation/test_agent_validation.py中定义test_t003_command_executor测试函数
- [ ] T055 [P] [US3] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent配置command_executor工具，当用户问"列出当前目录文件"，那么调用ls命令
- [ ] T056 [P] [US3] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent配置command_executor工具，当用户问"查看README文件内容"，那么调用cat命令
- [ ] T057 [P] [US3] 在tests/validation/test_agent_validation.py中实现场景3测试：给定Agent配置command_executor工具，当用户请求"rm -rf /"，那么工具拒绝执行或返回错误
- [ ] T058 [US3] 在tests/validation/test_agent_validation.py中实现路径白名单验证，检查CommandTool使用PathValidator
- [ ] T059 [US3] 在tests/validation/test_agent_validation.py中实现命令黑名单验证，检查黑名单命令被正确拒绝(遵循章程: 安全第一原则)
- [ ] T060 [US3] 在tests/validation/test_agent_validation.py中实现命令输出限制验证，检查输出不超过100KB(遵循章程: 多层防御策略)
- [ ] T061 [US3] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T003报告
- [ ] T062 [US3] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过
- [ ] T063 [US3] 在tests/validation/test_agent_validation.py中实现验证结果记录，验证安全合规需求(FR-025到FR-030)

---

## 阶段 5.5: 版本控制检查点

**目的**: 确保用户故事 3 完成并通过真实API测试后进行版本提交

- [ ] T064 运行test_t003_command_executor测试，使用真实智谱API验证命令执行工具调用和安全机制(遵循章程: 版本控制与测试纪律)
- [ ] T065 查看生成的报告specs/002-agent-validation-test/reports/T003-命令执行.md，验证安全测试结果
- [ ] T066 提交用户故事 3 代码，清晰描述"T003命令执行工具验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

**检查点**: 此时，P1组核心功能测试(US1, US2, US3)应该全部完成

---

## 阶段 6: 用户故事 4 - 测试报告生成验证(优先级: P1)

**目标**: 验证测试报告生成功能，包含完整的测试信息

**独立测试**: 运行test_t004_report_generation，验证报告包含所有必需字段

### 用户故事 4 的测试实现

- [ ] T067 [P] [US4] 在tests/validation/test_agent_validation.py中定义test_t004_report_generation测试函数
- [ ] T068 [P] [US4] 在tests/validation/test_agent_validation.py中实现场景1测试：给定测试执行完成，当生成报告，那么报告包含测试编号、名称、输入、工具链、结果、时间、状态
- [ ] T069 [P] [US4] 在tests/validation/test_agent_validation.py中实现场景2测试：给定工具被调用，当生成报告，那么报告记录工具名称、参数、结果、状态、时间
- [ ] T070 [P] [US4] 在tests/validation/test_agent_validation.py中实现场景3测试：给定测试失败，当生成报告，那么报告明确说明失败原因和错误信息
- [ ] T071 [US4] 在tests/validation/test_agent_validation.py中实现报告结构验证，使用正则表达式或Markdown解析器验证格式
- [ ] T072 [US4] 在tests/validation/test_agent_validation.py中实现报告字段完整性验证，检查所有必需字段存在
- [ ] T073 [US4] 在tests/validation/test_agent_validation.py中实现报告文件验证，检查文件保存到正确路径
- [ ] T074 [US4] 在tests/validation/test_agent_validation.py中实现验证结果记录，验证FR-003、FR-004、FR-014、FR-015

---

## 阶段 6.5: 版本控制检查点

**目的**: 确保用户故事 4 完成并通过验证后进行版本提交

- [ ] T075 运行test_t004_report_generation测试，验证测试报告生成功能(遵循章程: 版本控制与测试纪律)
- [ ] T076 查看生成的报告specs/002-agent-validation-test/reports/T004-测试报告.md，验证报告格式符合contracts/test-report-schema.md
- [ ] T077 提交用户故事 4 代码，清晰描述"T004测试报告生成验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

**检查点**: 此时，所有P1测试(US1, US2, US3, US4)应该完成并通过，MVP达成！

---

## 阶段 7: 用户故事 5 - 多轮工具调用验证(优先级: P2)

**目标**: 验证Agent能够在一次对话中进行多轮工具调用(ReAct循环)

**独立测试**: 运行test_t005_multi_tool_calls，验证Agent执行多轮工具调用并整合结果

### 用户故事 5 的测试实现

- [ ] T078 [P] [US5] 在tests/validation/test_agent_validation.py中定义test_t005_multi_tool_calls测试函数
- [ ] T079 [P] [US5] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent配置所有工具，当用户请求"检查系统状态并列出文件"，那么调用多个工具
- [ ] T080 [P] [US5] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent配置max_tool_rounds=5，当多步骤任务，那么工具调用次数≤5
- [ ] T081 [P] [US5] 在tests/validation/test_agent_validation.py中实现场景3测试：给定某个工具失败，当Agent继续执行，那么尝试其他方法或提示用户
- [ ] T082 [US5] 在tests/validation/test_agent_validation.py中实现ReAct循环验证，检查tool_calls数量符合预期
- [ ] T083 [US5] 在tests/validation/test_agent_validation.py中实现工具调用顺序验证，检查工具调用逻辑合理
- [ ] T084 [US5] 在tests/validation/test_agent_validation.py中实现结果整合验证，检查最终回复包含所有工具结果
- [ ] T085 [US5] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T005报告
- [ ] T086 [US5] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过

---

## 阶段 7.5: 版本控制检查点

**目的**: 确保用户故事 5 完成并通过真实API测试后进行版本提交

- [ ] T087 运行test_t005_multi_tool_calls测试，使用真实智谱API验证多轮工具调用(遵循章程: 版本控制与测试纪律)
- [ ] T088 查看生成的报告specs/002-agent-validation-test/reports/T005-多轮工具调用.md，验证ReAct循环记录完整
- [ ] T089 提交用户故事 5 代码，清晰描述"T005多轮工具调用验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

---

## 阶段 8: 用户故事 6 - RAG检索工具验证(优先级: P2)

**目标**: 验证Agent能够使用RAG工具在已索引文件中进行语义检索

**独立测试**: 运行test_t006_rag_search，验证Agent调用rag_search工具并基于检索结果回答

### 用户故事 6 的测试实现

- [ ] T090 [P] [US6] 在tests/validation/test_agent_validation.py中定义test_t006_rag_search测试函数
- [ ] T091 [P] [US6] 在tests/validation/test_agent_validation.py中准备测试数据，在白名单目录创建示例文本文件
- [ ] T092 [P] [US6] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent配置rag_search工具且文件已索引，当用户询问文档问题，那么调用rag_search
- [ ] T093 [P] [US6] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent配置rag_search工具，当查询内容在索引文件中，那么返回相关文档片段
- [ ] T094 [P] [US6] 在tests/validation/test_agent_validation.py中实现场景3测试：给定没有索引文件，当用户询问，那么Agent提示先索引文件
- [ ] T095 [US6] 在tests/validation/test_agent_validation.py中实现自动索引验证，检查RAGTool的execute_async自动创建索引
- [ ] T096 [US6] 在tests/validation/test_agent_validation.py中实现懒加载验证，检查索引不会重复创建(遵循章程: 自动化与按需索引)
- [ ] T097 [US6] 在tests/validation/test_agent_validation.py中实现文件类型验证，检查仅索引文本文件(遵循章程: 多层防御策略)
- [ ] T098 [US6] 在tests/validation/test_agent_validation.py中实现文件大小验证，检查文件大小≤10MB(遵循章程: 多层防御策略)
- [ ] T099 [US6] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T006报告
- [ ] T100 [US6] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过

---

## 阶段 8.5: 版本控制检查点

**目的**: 确保用户故事 6 完成并通过真实API测试后进行版本提交

- [ ] T101 运行test_t006_rag_search测试，使用真实智谱API验证RAG检索功能(遵循章程: 版本控制与测试纪律)
- [ ] T102 清理测试数据，删除测试创建的索引文件和临时文件
- [ ] T103 查看生成的报告specs/002-agent-validation-test/reports/T006-RAG检索.md，验证RAG功能测试结果
- [ ] T104 提交用户故事 6 代码，清晰描述"T006 RAG检索工具验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

---

## 阶段 9: 用户故事 7 - 对话上下文验证(优先级: P2)

**目标**: 验证Agent能够维护对话历史，理解上下文中的引用

**独立测试**: 运行test_t007_conversation_context，验证Agent记住之前的对话内容

### 用户故事 7 的测试实现

- [ ] T105 [P] [US7] 在tests/validation/test_agent_validation.py中定义test_t007_conversation_context测试函数
- [ ] T106 [P] [US7] 在tests/validation/test_agent_validation.py中实现场景1测试：给定第一轮用户说"我的名字是张三"，当第二轮用户问"我叫什么名字？"，那么回答"张三"
- [ ] T107 [P] [US7] 在tests/validation/test_agent_validation.py中实现场景2测试：给定对话历史，当用户使用代词"它"，那么Agent正确理解并回答
- [ ] T108 [P] [US7] 在tests/validation/test_agent_validation.py中实现场景3测试：给定对话历史，当用户询问之前的工具调用结果，那么Agent回忆并说明
- [ ] T109 [US7] 在tests/validation/test_agent_validation.py中实现ConversationHistory验证，检查max_turns=5限制
- [ ] T110 [US7] 在tests/validation/test_agent_validation.py中实现上下文传递验证，检查history正确传递给Agent
- [ ] T111 [US7] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T007报告
- [ ] T112 [US7] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过

---

## 阶段 9.5: 版本控制检查点

**目的**: 确保用户故事 7 完成并通过真实API测试后进行版本提交

- [ ] T113 运行test_t007_conversation_context测试，使用真实智谱API验证对话上下文管理(遵循章程: 版本控制与测试纪律)
- [ ] T114 查看生成的报告specs/002-agent-validation-test/reports/T007-对话上下文.md，验证上下文测试结果
- [ ] T115 提交用户故事 7 代码，清晰描述"T007对话上下文验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

---

## 阶段 10: 用户故事 8 - 工具超时和错误处理验证(优先级: P2)

**目标**: 验证Agent能够正确处理工具执行超时和错误情况

**独立测试**: 运行test_t008_timeout_error_handling，验证Agent优雅处理异常

### 用户故事 8 的测试实现

- [ ] T116 [P] [US8] 在tests/validation/test_agent_validation.py中定义test_t008_timeout_error_handling测试函数
- [ ] T117 [P] [US8] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent配置tool_timeout=5s，当工具执行时间>5s，那么标记为超时
- [ ] T118 [P] [US8] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent已初始化，当调用不存在的工具，那么返回"工具不存在"提示
- [ ] T119 [P] [US8] 在tests/validation/test_agent_validation.py中实现场景3测试：给定工具执行失败，当Agent继续，那么记录失败状态并尝试其他方法
- [ ] T120 [US8] 在tests/validation/test_agent_validation.py中实现超时验证，检查tool_calls中status == "timeout"
- [ ] T121 [US8] 在tests/validation/test_agent_validation.py中实现错误处理验证，检查Agent不崩溃且返回明确错误消息
- [ ] T122 [US8] 在tests/validation/test_agent_validation.py中实现降级验证，检查工具失败后的降级逻辑
- [ ] T123 [US8] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T008报告
- [ ] T124 [US8] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过

---

## 阶段 10.5: 版本控制检查点

**目的**: 确保用户故事 8 完成并通过真实API测试后进行版本提交

- [ ] T125 运行test_t008_timeout_error_handling测试，验证超时和错误处理(遵循章程: 版本控制与测试纪律)
- [ ] T126 查看生成的报告specs/002-agent-validation-test/reports/T008-错误处理.md，验证错误处理测试结果
- [ ] T127 提交用户故事 8 代码，清晰描述"T008工具超时和错误处理验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

---

## 阶段 11: 用户故事 9 - 模型切换功能验证(优先级: P2)

**目标**: 验证Agent的模型切换功能，能够在运行时动态切换大模型

**独立测试**: 运行test_t009_model_switch，验证模型确实切换成功并生效

### 用户故事 9 的测试实现

- [ ] T128 [P] [US9] 在tests/validation/test_agent_validation.py中定义test_t009_model_switch测试函数
- [ ] T129 [P] [US9] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent初始化使用glm-4-flash，当调用set_model切换到glm-4.5-flash，那么current_model更新
- [ ] T130 [P] [US9] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent已切换模型，当进行后续对话，那么使用新模型生成回复
- [ ] T131 [P] [US9] 在tests/validation/test_agent_validation.py中实现场景3测试：给定Agent初始化，当尝试切换到不存在的模型，那么抛出ValueError并保持当前模型
- [ ] T132 [US9] 在tests/validation/test_agent_validation.py中实现模型切换验证，检查llm_provider.current_model属性
- [ ] T133 [US9] 在tests/validation/test_agent_validation.py中实现聊天验证，检查使用新模型生成的回复
- [ ] T134 [US9] 在tests/validation/test_agent_validation.py中实现无效模型验证，检查ValueError异常
- [ ] T135 [US9] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T009报告
- [ ] T136 [US9] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过

---

## 阶段 11.5: 版本控制检查点

**目的**: 确保用户故事 9 完成并通过真实API测试后进行版本提交

- [ ] T137 运行test_t009_model_switch测试，使用真实智谱API验证模型切换功能(遵循章程: 版本控制与测试纪律)
- [ ] T138 查看生成的报告specs/002-agent-validation-test/reports/T009-模型切换.md，验证模型切换测试结果
- [ ] T139 提交用户故事 9 代码，清晰描述"T009模型切换功能验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

---

## 阶段 12: 用户故事 10 - API失败降级验证(优先级: P3)

**目标**: 验证当智谱API调用失败时，Agent能够降级到本地工具模式

**独立测试**: 运行test_t010_api_fallback，验证降级机制工作正常

### 用户故事 10 的测试实现

- [ ] T140 [P] [US10] 在tests/validation/test_agent_validation.py中定义test_t010_api_fallback测试函数
- [ ] T141 [P] [US10] 在tests/validation/test_agent_validation.py中实现场景1测试：给定Agent配置无效API Key，当用户请求系统监控，那么降级到本地模式
- [ ] T142 [P] [US10] 在tests/validation/test_agent_validation.py中实现场景2测试：给定Agent在降级模式，当API不可用，那么返回包含"[本地模式]"标记的回复
- [ ] T143 [P] [US10] 在tests/validation/test_agent_validation.py中实现场景3测试：给定Agent在降级模式，当用户请求超出本地工具能力，那么提示API不可用
- [ ] T144 [US10] 在tests/validation/test_agent_validation.py中实现降级验证，检查回复包含"[本地模式]"标记
- [ ] T145 [US10] 在tests/validation/test_agent_validation.py中实现本地工具验证，检查降级后直接调用工具
- [ ] T146 [US10] 在tests/validation/test_agent_validation.py中实现TestReport生成，调用TestReporter生成T010报告
- [ ] T147 [US10] 在tests/validation/test_agent_validation.py中实现用户确认逻辑，等待用户输入[Y/n]确认测试通过

---

## 阶段 12.5: 版本控制检查点

**目的**: 确保用户故事 10 完成并通过验证后进行版本提交

- [ ] T148 运行test_t010_api_fallback测试，验证API失败降级机制(遵循章程: 版本控制与测试纪律)
- [ ] T149 查看生成的报告specs/002-agent-validation-test/reports/T010-API降级.md，验证降级测试结果
- [ ] T150 提交用户故事 10 代码，清晰描述"T010 API失败降级验证完成"和测试结果(遵循章程: 版本控制与测试纪律)

**检查点**: 所有用户故事(P1, P2, P3)现在应该全部完成并通过验证

---

## 阶段 13: 完善与横切关注点

**目的**: 生成汇总报告，更新文档，确保整体质量

- [ ] T151 [P] 生成汇总报告specs/002-agent-validation-test/reports/汇总报告.md，包含所有测试的通过率和统计信息
- [ ] T152 分析所有测试的性能指标，生成性能分析报告
- [ ] T153 [P] 更新README.md或相关文档，说明如何运行验证测试(参考quickstart.md)
- [ ] T154 [P] 代码清理和重构，确保测试代码质量符合项目规范
- [ ] T155 运行quickstart.md验证，确保文档中的所有命令可执行(遵循章程: 版本控制与测试纪律)
- [ ] T156 [P] 在logs/test_validation.log中记录所有测试执行的汇总日志

---

## 阶段 13.5: 最终版本控制检查点

**目的**: 确保所有工作完成并通过最终验证后进行版本提交

- [ ] T157 运行所有10个测试用例，确保100%通过(遵循SC-001)
- [ ] T158 验证所有10个测试报告生成且格式正确
- [ ] T159 验证性能指标符合所有成功标准(SC-002到SC-010)
- [ ] T160 提交最终代码，清晰描述"Agent功能验证测试全部完成"和完整测试结果(遵循章程: 版本控制与测试纪律)

---

## 依赖关系与执行顺序

### 阶段依赖关系

- **设置(阶段 1)**: 无依赖关系 - 可立即开始
- **基础(阶段 2)**: 依赖于设置完成 - 阻塞所有用户故事测试
- **用户故事(阶段 3-12)**: 都依赖于基础阶段完成
  - 然后用户故事可以按优先级顺序进行(P1 → P2 → P3)
  - 或在基础完成后并行进行(如果有多个开发者)
- **完善(阶段 13)**: 依赖于所有用户故事完成

### 用户故事依赖关系

- **用户故事 1-4(P1)**: MVP核心功能，必须在P2/P3之前完成
- **用户故事 5-9(P2)**: 进阶功能，可在P1完成后独立测试
- **用户故事 10(P3)**: 边缘场景，可在P1完成后独立测试
- **用户故事独立性**: 每个用户故事测试应该独立可运行，不依赖于其他用户故事测试

### 每个用户故事内部

- 场景测试按顺序实现(场景1 → 场景2 → 场景3)
- 场景测试可以并行实现(标记为[P])
- 验收逻辑在所有场景测试之后
- TestReport生成在验收逻辑之后
- 用户确认在报告生成之后

### 并行机会

- 所有标记为 [P] 的设置任务可以并行运行
- 所有标记为 [P] 的基础任务可以并行运行(在阶段 2 内)
- 基础阶段完成后，不同优先级的用户故事可以并行开始(推荐按优先级顺序)
- 用户故事中所有标记为 [P] 的场景测试可以并行编写
- 不同用户故事可以由不同团队成员并行处理(如果有多个开发者)

---

## 并行示例: 用户故事 1(基础对话功能验证)

```bash
# 一起启动用户故事 1 的所有场景测试(并行编写):
T030: 实现场景1测试："你好"问候
T031: 实现场景2测试："你是什么？"自我介绍
T032: 实现场景3测试："谢谢"礼貌回应

# 场景测试完成后，按顺序执行:
T033: 实现验收逻辑(验证无工具调用)
T034: 实现性能指标收集
T035: 实现TestReport生成
T036: 实现用户确认逻辑
T037: 实现验证结果记录
```

---

## 实施策略

### 仅 MVP(仅用户故事 1-4，P1测试)

1. 完成阶段 1: 设置(测试框架基础结构)
2. 完成阶段 2: 基础(测试框架核心)
3. 完成阶段 3-6: 用户故事 1-4(P1核心测试)
4. **停止并验证**: 运行所有P1测试，确认MVP达成
5. 生成汇总报告，验证P1测试100%通过(SC-001)

### 增量交付(推荐)

1. 完成设置 + 基础 → 测试框架就绪
2. 添加用户故事 1-4(P1) → 独立测试 → 提交版本(MVP! )
3. 添加用户故事 5-9(P2) → 独立测试 → 提交版本
4. 添加用户故事 10(P3) → 独立测试 → 提交版本
5. 完善与横切关注点 → 最终验证 → 提交版本
6. 每个阶段在不破坏先前测试的情况下增加价值

### 并行团队策略

有多个开发人员时:

1. 团队一起完成设置 + 基础(阶段 1-2)
2. 基础完成后:
   - 开发人员 A: 用户故事 1-2(P1 - 基础对话和系统监控)
   - 开发人员 B: 用户故事 3-4(P1 - 命令执行和报告生成)
   - 开发人员 C: 用户故事 5-6(P2 - 多轮调用和RAG)
3. P1完成后:
   - 开发人员 A: 用户故事 7-8(P2 - 上下文和错误处理)
   - 开发人员 B: 用户故事 9(P2 - 模型切换)
   - 开发人员 C: 用户故事 10(P3 - API降级)
4. 每个用户故事独立完成和集成

---

## 任务汇总

- **总任务数**: 162
- **设置任务数**: 11(T001-T011)
- **基础任务数**: 17(T012-T028)
- **用户故事任务数**: 116(T029-T147)
  - US1(P1): 11个任务（包含2个边界测试）
  - US2(P1): 10个任务
  - US3(P1): 10个任务
  - US4(P1): 8个任务
  - US5(P2): 9个任务
  - US6(P2): 12个任务
  - US7(P2): 8个任务
  - US8(P2): 9个任务
  - US9(P2): 9个任务
  - US10(P3): 8个任务
- **完善任务数**: 12(T150-T162)

### 识别的并行机会

- **阶段 1**: 7个并行任务(T003-T009)
- **阶段 2**: 10个并行任务(T013-T022, T023)
- **用户故事阶段**: 每个用户故事有3-4个并行场景测试任务
- **总体**: 约41%的任务(66个)可并行执行

### 每个用户故事的独立测试标准

- **US1(基础对话)**: 运行test_t001_basic_conversation，验证Agent返回问候且tool_calls为空
- **US2(系统监控)**: 运行test_t002_system_monitor，验证Agent调用sys_monitor且参数正确
- **US3(命令执行)**: 运行test_t003_command_executor，验证Agent调用命令且安全机制有效
- **US4(测试报告)**: 运行test_t004_report_generation，验证报告包含所有必需字段
- **US5(多轮调用)**: 运行test_t005_multi_tool_calls，验证工具调用次数≤max_rounds
- **US6(RAG检索)**: 运行test_t006_rag_search，验证RAG工具调用且自动索引工作
- **US7(对话上下文)**: 运行test_t007_conversation_context，验证Agent记住之前对话
- **US8(错误处理)**: 运行test_t008_timeout_error_handling，验证超时和错误被优雅处理
- **US9(模型切换)**: 运行test_t009_model_switch，验证模型切换成功且新模型生效
- **US10(API降级)**: 运行test_t010_api_fallback，验证降级到本地模式

### 建议的 MVP 范围

**MVP = 用户故事 1-4(P1核心测试)**

- T001-T011: 设置(11个任务)
- T012-T028: 基础(17个任务)
- T029-T079: 用户故事 1-4(39个任务)
- **总计**: 67个任务
- **预计工作量**: 核心测试框架和P1测试验证

**MVP达成标准**:
- 所有P1测试(US1-US4)通过
- 生成4个完整的测试报告(T001-T004)
- 验证SC-001、SC-002、SC-003、SC-005

---

## 注意事项

- [P] 任务 = 不同文件，无依赖关系，可并行执行
- [Story] 标签将任务映射到特定用户故事以实现可追溯性
- 每个用户故事测试应该独立可运行和可验证
- 测试必须使用真实智谱API，不允许mock(遵循章程: 测试真实性)
- 在每个用户故事测试后等待用户确认(遵循FR-013)
- 在任何检查点停止以独立验证故事
- 所有测试代码注释和错误消息使用中文(遵循章程: 语言规范)
- 避免模糊任务、相同文件冲突、破坏独立性的跨故事依赖
