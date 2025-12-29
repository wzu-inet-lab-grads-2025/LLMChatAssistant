# 实施任务: 测试全面重构与实现验证

**功能分支**: `001-test-overhaul-validation`
**生成日期**: 2025-12-29
**规范**: [spec.md](./spec.md)
**计划**: [plan.md](./plan.md)

## 概述

本任务文档将测试重构与验证项目分解为可执行的、按依赖关系排序的任务。基于实现状态分析，项目已完成 92% 的核心功能（23/25），主要任务集中在：

1. 修复服务器启动问题（P0）
2. 重新生成全面的测试套件（P1）
3. 验证功能真实实现（P1）
4. 验证项目可交付性（P2）

## 任务统计

- **总任务数**: 45 个
- **用户故事**: 4 个
- **阶段**: 7 个
- **并行机会**: 15 个任务可并行执行

## 实现策略

**MVP 优先**: 用户故事 1（修复服务器启动）是 MVP，必须首先完成才能进行其他工作。

**增量交付**: 每个用户故事完成后立即进行测试和提交，确保持续可交付。

**测试驱动**: 所有任务完成后运行完整测试套件，确保质量标准。

## 阶段 1: 设置与配置修复 (P0 - 阻塞)

**目标**: 修复服务器启动问题，确保基础环境可用。

**验收标准**: 服务器能在 10 秒内启动，监听 9999 端口，无配置错误。

**任务**:
- [X] T001 修复 config.yaml 中的字段名（llm.model → llm.chat_model，确认 llm.max_tokens=128000） ✅
- [X] T002 修复 src/server/main.py:72-77 中的 ZhipuProvider 初始化参数（移除 temperature 和 max_tokens，使用 chat_model） ✅
- [X] T003 删除 src/llm/zhipu.py:107-142 中的重复代码块 ✅
- [X] T004 验证 .env 文件存在且包含 ZHIPU_API_KEY ✅
- [X] T005 验证 config.yaml 格式正确（运行 `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`） ✅
- [X] T006 测试服务器启动（运行 `python -m src.server.main`，验证监听 0.0.0.0:9999） ✅
- [X] T007 修复 NPLT 协议长度限制（uint8 → uint16，支持最大 64KB 消息） ✅
  - 修改 src/protocols/nplt.py: MAX_DATA_LENGTH (255 → 65535)
  - 修改 src/protocols/nplt.py: HEADER_FORMAT (">BHB" → ">BHH")
  - 更新 specs/001-llm-chat-assistant/contracts/nplt-protocol.md (v2.0)
  - 运行 test_protocol_fix.py 验证修复（5/5 测试通过）
- [ ] T008 测试客户端连接（启动客户端，验证能成功连接到服务器并进行对话）

**检查点**: ✅ 服务器成功启动，客户端能连接

---

## 阶段 2: 基础设施 - 测试框架搭建 (P0 - 阻塞)

**目标**: 搭建测试基础设施，准备测试套件生成。

**验收标准**: pytest 配置完成，conftest.py 和测试辅助工具就绪。

**任务**:
- [ ] T10 创建 tests/conftest.py，定义全局 fixtures（api_key, llm_provider, event_loop）
- [ ] T010 创建 tests/helpers/api_validation.py，实现 APIKeyValidator 类
- [ ] T011 创建 tests/helpers/error_reporting.py，实现 TestFailureReporter 类
- [ ] T10 在项目根目录创建 pytest.ini，配置测试发现、标记、日志
- [ ] T10 在项目根目录创建 .coveragerc，配置覆盖率目标（> 90%）
- [ ] T10 添加测试依赖到 pyproject.toml（pytest, pytest-cov, pytest-asyncio, pytest-timeout）
- [ ] T10 运行 `uv sync` 同步新依赖

**检查点**: ✅ 测试框架配置完成

---

## 阶段 3: 用户故事 1 - 修复服务器启动问题 (US1, P1)

**故事目标**: 确保服务器能够正常启动并接受客户端连接。

**独立测试标准**: 启动服务器进程，验证服务器在 9999 端口监听，客户端能建立连接。

**任务**:
- [ ] T10 [P] 在 tests/unit/test_config.py 中实现配置加载测试（验证 YAML 解析、环境变量读取）
- [ ] T10 [P] 在 tests/unit/test_config.py 中实现配置验证测试（验证必需字段、端口范围、API key 格式）
- [ ] T10 [US1] 在 src/utils/config.py 中增强配置验证（添加 validate_config() 函数）
- [ ] T10 [US1] 在 src/server/main.py 中添加启动前配置验证（调用 validate_config()）
- [ ] T020 [US1] 在 tests/integration/test_server_startup.py 中实现服务器启动集成测试
- [ ] T021 [US1] 在 tests/integration/test_client_connection.py 中实现客户端连接集成测试

**并行执行示例**:
```bash
# T10 和 T10 可并行（不同测试文件）
pytest tests/unit/test_config.py -v

# T10 和 T10 必须顺序执行（T10 修改配置，T10 使用）
```

**检查点**: ✅ US1 完成 - 服务器启动成功，所有测试通过

---

## 阶段 4: 用户故事 2 - 重新生成全面的测试套件 (US2, P1)

**故事目标**: 生成全面的单元测试、集成测试和端到端测试，覆盖所有核心功能。

**独立测试标准**: 运行测试套件，验证：1) 无 mock 2) 覆盖所有核心功能 3) 能检测虚假实现。

**任务**:
- [ ] T021 [P] 删除 tests/ 目录下所有现有测试文件（保留 conftest.py 和 helpers/）
- [ ] T10 [P] [US2] 在 tests/unit/test_nplt.py 中实现 NPLT 协议编码/解码测试
- [ ] T10 [P] [US2] 在 tests/unit/test_rdt.py 中实现 RDT 协议滑动窗口和重传测试
- [ ] T10 [P] [US2] 在 tests/unit/test_llm.py 中实现 LLM Provider 单元测试（chat, embed, model_switching）
- [ ] T10 [P] [US2] 在 tests/unit/test_storage.py 中实现存储层单元测试（history, vector_store）
- [ ] T10 [P] [US2] 在 tests/integration/test_client_server.py 中实现客户端-服务器通信集成测试
- [ ] T10 [P] [US2] 在 tests/integration/test_file_upload.py 中实现文件上传和 RAG 集成测试
- [ ] T10 [P] [US2] 在 tests/integration/test_session_management.py 中实现会话管理集成测试
- [ ] T10 [US2] 在 tests/e2e/test_conversation.py 中实现完整对话流程端到端测试
- [ ] T030 [US2] 在 tests/e2e/test_file_transfer.py 中实现文件传输流程端到端测试
- [ ] T031 [US2] 在 tests/e2e/test_multi_session.py 中实现多会话管理流程端到端测试
- [ ] T10 [US2] 运行 `pytest --cov=src --cov-report=html` 生成覆盖率报告
- [ ] T10 [US2] 验证覆盖率 > 90%，查看 htmlcov/index.html 补充遗漏的测试

**并行执行示例**:
```bash
# T10-T031 可并行生成（不同测试文件）
# 然后运行完整测试套件
pytest -v --cov=src
```

**检查点**: ✅ US2 完成 - 测试套件生成完成，覆盖率达标

---

## 阶段 5: 用户故事 3 - 验证所有功能的真实实现 (US3, P1)

**故事目标**: 扫描源代码，验证所有功能都有真实实现（无占位符）。

**独立测试标准**: 扫描代码无 pass/TODO/FIXME/NotImplementedError，端到端测试验证功能可用。

**任务**:
- [ ] T10 [P] [US3] 使用 grep 扫描 src/ 目录下的 pass、TODO、FIXME、NotImplementedError 关键字
- [ ] T10 [P] [US3] 使用 grep 扫描 src/ 目录下的 "raise Exception("未实现")" 模式
- [ ] T10 [P] [US3] 验证核心功能文件（src/server/main.py, src/llm/zhipu.py, src/protocols/nplt.py, src/protocols/rdt.py）
- [ ] T10 [P] [US3] 验证工具层文件（src/tools/command.py, src/tools/monitor.py, src/tools/rag.py）
- [ ] T10 [P] [US3] 验证存储层文件（src/storage/history.py, src/storage/vector_store.py）
- [ ] T10 [US3] 运行完整端到端测试套件（pytest tests/e2e/ -v）
- [ ] T040 [US3] 如果发现虚假实现，修复或删除并重新运行测试

**并行执行示例**:
```bash
# T10-T10 可并行扫描（不同文件）
grep -r "pass\|TODO\|FIXME" src/
grep -r "raise Exception" src/
```

**检查点**: ✅ US3 完成 - 无虚假实现，所有功能真实可用

---

## 阶段 6: 用户故事 4 - 验证项目可交付性 (US4, P2)

**故事目标**: 验证项目可以交付使用：服务器稳定、客户端完整、测试通过、文档完整。

**独立测试标准**: 全新环境安装成功，服务器稳定运行 1 小时，所有测试通过。

**任务**:
- [ ] T041 [P] [US4] 从全新环境按照 quickstart.md 安装项目（验证 10 分钟内完成）
- [ ] T10 [P] [US4] 运行完整测试套件（pytest -v，验证所有测试通过）
- [ ] T10 [US4] 运行稳定性测试（服务器运行 1 小时，客户端进行 10 轮对话，验证无崩溃）
- [ ] T10 [US4] 验证文档完整性（检查 README.md、quickstart.md、spec.md 准确反映实际功能）
- [ ] T10 [US4] 执行典型运维任务（系统监控、命令执行、文件上传、日志检索），验证功能可用

**并行执行示例**:
```bash
# T041 和 T10-T10 可在不同环境并行执行
# CI 环境: T10（测试）
# 本地环境: T10-T10（稳定性和功能验证）
```

**检查点**: ✅ US4 完成 - 项目可以交付使用

---

## 阶段 7: 完善与横切关注点

**目标**: 代码质量优化、文档完善、版本提交。

**验收标准**: 代码整洁，文档完整，已提交版本。

**任务**:
- [ ] T10 [P] 重构 src/llm/zhipu.py 中的代码重复（提取公共方法）
- [ ] T10 [P] 更新 README.md，添加项目状态说明和快速开始链接
- [ ] T10 [P] 创建 CHANGELOG.md，记录修复的问题和新增的功能
- [ ] T10 运行代码格式化（black、isort），确保代码风格一致
- [ ] T050 运行最终完整测试套件（pytest -v --cov=src），验证所有测试通过
- [ ] T051 提交阶段 1-6 的所有更改（git add . && git commit -m "fix: 修复服务器启动并完成测试重构"）
- [ ] T10 创建 git tag（git tag -a v1.0.0 -m "完成测试重构和验证，项目可交付"）

**并行执行示例**:
```bash
# T10-T10 可并行（不同文件）
# T10-T050 顺序执行
```

**检查点**: ✅ 项目完成 - 所有工作已提交和标记

---

## 依赖关系图

```
阶段 1 (T001-T10) [P0 - 阻塞]
    ↓
阶段 2 (T10-T10) [P0 - 基础设施]
    ↓
┌───────────────────────────────────────┐
│  并行执行用户故事                      │
├───────────────────────────────────────┤
│ 阶段 3 (T10-T020) [US1 - 修复服务器] │
│ 阶段 4 (T021-T10) [US2 - 测试套件]    │
│ 阶段 5 (T10-T040) [US3 - 验证实现]   │
│ 阶段 6 (T041-T10) [US4 - 可交付性]   │
└───────────────────────────────────────┘
    ↓
阶段 7 (T10-T10) [完善与提交]
```

**关键依赖**:
- 阶段 1 必须首先完成（修复服务器启动）
- 阶段 2 依赖于阶段 1（需要服务器启动才能测试）
- 阶段 3-6 可以部分并行（不同用户故事）
- 阶段 7 必须最后完成（需要所有功能就绪）

---

## 并行执行机会

| 阶段 | 可并行的任务 | 并行数量 |
|------|--------------|----------|
| 阶段 1 | T001-T10（不同文件修复） | 5 |
| 阶段 2 | T10-T10（不同配置文件） | 6 |
| 阶段 3 | T10-T10（不同测试文件） | 2 |
| 阶段 4 | T10-T031（不同测试文件） | 10 |
| 阶段 5 | T10-T10（不同源文件扫描） | 5 |
| 阶段 6 | T041-T10（不同验证任务） | 4 |
| 阶段 7 | T10-T10（代码和文档优化） | 3 |
| **总计** | | **35** |

**并行执行命令示例**:
```bash
# 使用 pytest-xdist 并行运行测试
pytest -n auto

# 使用 GNU parallel 并行扫描文件
parallel grep -r "TODO" ::: src/client src/server src/protocols
```

---

## 独立测试标准总结

| 用户故事 | 独立测试标准 | 测试文件 |
|----------|--------------|----------|
| US1 - 修复服务器启动 | 服务器启动成功，客户端能连接 | tests/integration/test_server_startup.py, tests/integration/test_client_connection.py |
| US2 - 测试套件生成 | 无 mock，覆盖率 > 90%，覆盖所有核心功能 | tests/unit/, tests/integration/, tests/e2e/ |
| US3 - 验证真实实现 | 代码扫描无占位符，端到端测试通过 | grep 扫描，pytest tests/e2e/ |
| US4 - 项目可交付性 | 全新环境安装成功，稳定运行 1 小时 | 完整安装流程，稳定性测试 |

---

## 建议的 MVP 范围

**MVP**: 阶段 1 + 阶段 2 + 阶段 3（用户故事 1）

**理由**:
- 修复服务器启动问题是阻塞所有其他工作的前置条件
- 搭建测试基础设施是后续测试生成的基础
- 用户故事 1 完成后即可进行其他用户故事

**MVP 验收标准**:
- ✅ 服务器能在 10 秒内启动
- ✅ 客户端能成功连接到服务器
- ✅ 测试框架配置完成
- ✅ 配置验证测试通过

**后续增量**:
- **增量 1**: 用户故事 2（测试套件生成）
- **增量 2**: 用户故事 3（验证真实实现）
- **增量 3**: 用户故事 4（可交付性验证）
- **增量 4**: 完善与提交（代码质量和文档）

---

## 下一步行动

1. **立即开始**: 执行 T001-T10（阶段 1），修复服务器启动问题
2. **验证修复**: 运行 `python -m src.server.main` 和客户端连接测试
3. **生成测试**: 执行 T021-T10（阶段 4），生成完整测试套件
4. **验证质量**: 执行 T10-T040（阶段 5），确保无虚假实现
5. **交付使用**: 执行 T041-T10（阶段 6），验证可交付性
6. **完善提交**: 执行 T10-T10（阶段 7），完成项目

**记住**: 每个用户故事完成后立即运行测试并提交版本，确保持续可交付。
