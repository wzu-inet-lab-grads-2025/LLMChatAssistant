# 快速开始指南: Agent功能验证测试

**功能**: Agent功能全面验证测试
**目标用户**: 开发者、测试工程师、QA
**前置要求**: Python 3.11、uv、有效的智谱API Key

---

## 前置准备

### 1. 环境要求

- **Python版本**: 3.11
- **包管理器**: uv
- **操作系统**: Linux（推荐Ubuntu 20.04+）
- **网络**: 能够访问智谱AI API

### 2. 安装依赖

```bash
# 使用uv创建虚拟环境（如果还没有）
uv venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
uv sync
```

### 3. 配置API Key

**重要**: 测试必须使用真实的智谱API，不支持mock。

```bash
# 方法1: 导出环境变量（推荐）
export ZHIPU_API_KEY="your-api-key-here"

# 方法2: 在.env文件中配置
echo "ZHIPU_API_KEY=your-api-key-here" >> .env

# 验证配置
echo $ZHIPU_API_KEY
```

### 4. 验证环境

```bash
# 运行简单的验证测试
python -m pytest tests/integration/test_agent.py::TestAgentToolCalls::test_agent_initialization -v

# 如果测试通过，说明环境配置正确
```

---

## 运行测试

### 方式1: 运行所有验证测试（交互模式）

```bash
# 运行所有10个测试，每个测试后等待用户确认
python -m pytest tests/validation/test_agent_validation.py -v
```

**交互示例**:

```
==================== 测试报告 T001: 基础对话功能验证 ====================
... [报告内容] ...

测试完成。请确认是否通过？[Y/n]: y
✓ 用户确认测试通过

==================== 测试报告 T002: 系统监控工具验证 ====================
... [报告内容] ...

测试完成。请确认是否通过？[Y/n]: n
✗ 用户确认测试未通过
```

### 方式2: 运行所有测试（自动确认模式）

```bash
# 跳过用户确认，适用于CI/CD
python -m pytest tests/validation/test_agent_validation.py --auto-confirm -v
```

### 方式3: 运行特定优先级的测试

```bash
# 只运行P1测试（核心功能）
python -m pytest tests/validation/test_agent_validation.py::test_p1_tests -v

# 只运行P2测试（进阶功能）
python -m pytest tests/validation/test_agent_validation.py::test_p2_tests -v

# 只运行P3测试（边缘场景）
python -m pytest tests/validation/test_agent_validation.py::test_p3_tests -v
```

### 方式4: 运行单个测试

```bash
# 运行T001基础对话测试
python -m pytest tests/validation/test_agent_validation.py::test_t001_basic_conversation -v

# 运行T002系统监控测试
python -m pytest tests/validation/test_agent_validation.py::test_t002_system_monitor -v
```

### 方式5: 运行测试并生成详细日志

```bash
# 启用详细日志输出
python -m pytest tests/validation/test_agent_validation.py -v --log-cli-level=INFO

# 日志将保存到 logs/test_validation.log
```

---

## 查看测试报告

### 报告位置

测试报告自动保存到：
```
specs/002-agent-validation-test/reports/
├── T001-基础对话.md
├── T002-系统监控.md
├── T003-命令执行.md
├── T004-测试报告.md
├── T005-多轮工具调用.md
├── T006-RAG检索.md
├── T007-对话上下文.md
├── T008-错误处理.md
├── T009-模型切换.md
└── T010-API降级.md
```

### 查看报告

```bash
# 在终端查看（使用less或cat）
less specs/002-agent-validation-test/reports/T001-基础对话.md

# 在VSCode中打开
code specs/002-agent-validation-test/reports/T001-基础对话.md

# 在浏览器中查看（如果安装了Markdown预览工具）
firefox specs/002-agent-validation-test/reports/T001-基础对话.md
```

### 报告内容

每个报告包含：

1. **测试信息** - 编号、名称、优先级、状态
2. **测试输入** - 用户消息、对话历史
3. **工具链调用详情** - 每个工具的完整调用信息
4. **最终结果** - Agent的回复
5. **性能指标** - 响应时间、工具执行时间
6. **验收结果** - 每个场景的通过/失败状态
7. **测试结论** - 整体评估和判断依据

---

## 调试测试失败

### 1. 查看详细错误信息

```bash
# 显示完整的错误回溯
python -m pytest tests/validation/test_agent_validation.py::test_t001_basic_conversation -vv

# 显示print输出
python -m pytest tests/validation/test_agent_validation.py::test_t001_basic_conversation -v -s
```

### 2. 进入调试模式

```bash
# 在失败时进入pdb调试器
python -m pytest tests/validation/test_agent_validation.py::test_t001_basic_conversation --pdb

# 在第一个失败时进入pdb
python -m pytest tests/validation/test_agent_validation.py --pdb-trace
```

### 3. 查看日志

```bash
# 查看测试日志
tail -f logs/test_validation.log

# 搜索错误
grep "ERROR" logs/test_validation.log
grep "Exception" logs/test_validation.log
```

### 4. 常见问题排查

#### 问题1: API Key未配置

**错误信息**:
```
E           AssertionError: ZHIPU_API_KEY 环境变量未设置
```

**解决方法**:
```bash
export ZHIPU_API_KEY="your-api-key-here"
```

#### 问题2: API调用失败

**错误信息**:
```
E           zai_sdk.errors.APIError: Invalid API key
```

**解决方法**:
- 验证API Key是否正确
- 检查API Key是否已激活
- 确认账户余额充足

#### 问题3: 工具调用超时

**错误信息**:
```
E           AssertionError: 工具执行时间过长: 6.2s >= 5s
```

**解决方法**:
- 检查网络连接
- 查看Agent日志，确认工具是否真的执行缓慢
- 考虑调整tool_timeout配置

#### 问题4: 测试数据未清理

**错误信息**:
```
E           AssertionError: 对话历史未正确隔离
```

**解决方法**:
```bash
# 清理测试数据
rm -rf storage/test-*
rm -rf logs/test_validation.log

# 重新运行测试
python -m pytest tests/validation/test_agent_validation.py -v
```

---

## 测试覆盖率

### 测试用例清单

| 编号 | 名称 | 优先级 | 测试内容 |
|------|------|--------|----------|
| T001 | 基础对话功能验证 | P1 | 验证Agent能够进行基础对话，无需工具 |
| T002 | 系统监控工具验证 | P1 | 验证Agent能够调用sys_monitor工具 |
| T003 | 命令执行工具验证 | P1 | 验证Agent能够调用command_executor工具 |
| T004 | 测试报告生成验证 | P1 | 验证测试报告的完整性和格式 |
| T005 | 多轮工具调用验证 | P2 | 验证Agent的ReAct循环能力 |
| T006 | RAG检索工具验证 | P2 | 验证Agent能够调用rag_search工具 |
| T007 | 对话上下文验证 | P2 | 验证Agent能够维护对话历史 |
| T008 | 工具超时和错误处理验证 | P2 | 验证Agent的错误处理能力 |
| T009 | 模型切换功能验证 | P2 | 验证Agent的模型切换功能 |
| T010 | API失败降级验证 | P3 | 验证Agent的降级机制 |

### 成功标准

测试需要满足以下成功标准（来自spec.md）：

- **SC-001**: 所有P1测试100%通过
- **SC-002**: 工具调用响应时间 < 2秒（90%的情况下）
- **SC-003**: 工具执行时间 < 5秒（100%）
- **SC-004**: 工具调用准确率 ≥ 90%
- **SC-005**: 测试报告完整信息覆盖率100%
- **SC-006**: API失败降级成功率 ≥ 95%
- **SC-007**: 模型切换成功率100%
- **SC-008**: 对话上下文准确率 ≥ 85%
- **SC-009**: 错误处理优雅处理率100%
- **SC-010**: 用户满意度 ≥ 90%

---

## 集成到CI/CD

### GitHub Actions示例

```yaml
name: Agent验证测试

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: 设置Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: 安装uv
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        echo "$HOME/.cargo/bin" >> $GITHUB_PATH

    - name: 安装依赖
      run: |
        uv venv
        source .venv/bin/activate
        uv sync

    - name: 运行验证测试
      env:
        ZHIPU_API_KEY: ${{ secrets.ZHIPU_API_KEY }}
      run: |
        source .venv/bin/activate
        pytest tests/validation/test_agent_validation.py --auto-confirm -v

    - name: 上传测试报告
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-reports
        path: specs/002-agent-validation-test/reports/*.md
```

---

## 最佳实践

### 1. 测试顺序

建议按照优先级顺序运行测试：P1 → P2 → P3

```bash
# 先运行P1测试，确保核心功能正常
python -m pytest tests/validation/test_agent_validation.py::test_p1_tests -v

# P1测试通过后，运行P2测试
python -m pytest tests/validation/test_agent_validation.py::test_p2_tests -v

# 最后运行P3测试
python -m pytest tests/validation/test_agent_validation.py::test_p3_tests -v
```

### 2. 测试隔离

每个测试使用独立的对话历史和会话ID，确保测试之间不会相互影响：

```python
@pytest.fixture
async def fresh_history():
    """为每个测试创建新的对话历史"""
    return ConversationHistory.create_new(f"test-{uuid4()}")
```

### 3. 性能监控

关注测试的性能指标，如果发现性能下降，及时调查：

```bash
# 运行测试并记录性能数据
python -m pytest tests/validation/test_agent_validation.py -v --durations=10
```

### 4. 定期验证

建议每次代码变更后运行验证测试，确保Agent功能未受影响：

```bash
# 提交代码前运行测试
git pre-commit-hook: pytest tests/validation/test_agent_validation.py --auto-confirm
```

---

## 下一步

1. **运行第一个测试**: 从T001开始，验证环境配置正确
2. **查看报告**: 了解测试报告的格式和内容
3. **调试问题**: 如果有测试失败，参考调试章节排查问题
4. **集成到开发流程**: 将测试集成到pre-commit或CI/CD

---

## 需要帮助？

- **查看规范**: [spec.md](spec.md) - 完整的功能需求
- **查看数据模型**: [data-model.md](data-model.md) - 测试框架的数据结构
- **查看报告契约**: [contracts/test-report-schema.md](contracts/test-report-schema.md) - 测试报告格式规范
- **查看实施计划**: [plan.md](plan.md) - 技术决策和设计

---

**最后更新**: 2025-12-29
