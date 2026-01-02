# 快速入门指南: 重构后系统验证

**功能**: 重构后系统验证
**最后更新**: 2026-01-02

## 概述

本指南提供重构后系统验证功能的快速入门，帮助您快速设置环境、运行测试并查看结果。

## 前置条件

### 必需条件

1. **Python 3.11**
   ```bash
   python --version  # 应显示 Python 3.11.x
   ```

2. **uv（虚拟环境管理器）**
   ```bash
   uv --version
   ```

3. **智谱AI API Key**
   - 访问 [智谱AI开放平台](https://open.bigmodel.cn/) 注册
   - 获取API Key
   - 设置环境变量：
     ```bash
     export ZHIPU_API_KEY='your-api-key-here'
     # 或创建 .env 文件
     echo "ZHIPU_API_KEY=your-api-key-here" > .env
     ```

### 可选条件

- **pytest相关插件**（自动安装）：
  - pytest-asyncio（异步测试支持）
  - pytest-html（HTML报告）
  - pytest-cov（代码覆盖率）

## 快速开始

### 1. 设置环境

```bash
# 1. 确保在项目根目录
cd /home/zhoutianyu/tmp/LLMChatAssistant

# 2. 使用uv创建虚拟环境并安装依赖
uv sync

# 3. 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 4. 验证API Key配置
echo $ZHIPU_API_KEY  # 应显示你的API Key
```

### 2. 运行所有测试

```bash
# 运行所有验证测试
pytest tests/validation/ -v

# 预期输出：
# tests/validation/test_agent.py::test_agent_simple_chat PASSED
# tests/validation/test_agent.py::test_agent_tool_call PASSED
# ...
# ==================== 28 passed in 95.23s ====================
```

### 3. 查看测试报告

测试完成后，报告将生成在以下位置：

- **HTML报告**: `reports/test_report.html`
- **JSON报告**: `reports/test_report_YYYYMMDD_HHMMSS.json`
- **日志文件**: `logs/test_validation.log`

```bash
# 在浏览器中打开HTML报告
# Linux
xdg-open reports/test_report.html

# macOS
open reports/test_report.html

# Windows
start reports/test_report.html
```

## 常用命令

### 按优先级运行测试

```bash
# 只运行P1测试（Agent、数据传输）
pytest tests/validation/ -m P1 -v

# 只运行P2测试（文件操作、检索）
pytest tests/validation/ -m P2 -v

# 只运行P3测试（历史记录）
pytest tests/validation/ -m P3 -v

# 组合运行P1和P2
pytest tests/validation/ -m "P1 or P2" -v
```

### 运行特定测试文件

```bash
# Agent功能测试
pytest tests/validation/test_agent.py -v

# 数据传输测试
pytest tests/validation/test_data_transmission.py -v

# 文件操作测试
pytest tests/validation/test_file_operations.py -v
```

### 运行特定测试用例

```bash
# 运行单个测试
pytest tests/validation/test_agent.py::test_agent_simple_chat -v

# 运行多个测试（使用-k关键字）
pytest tests/validation/ -k "simple_chat" -v

# 运行包含"chat"的所有测试
pytest tests/validation/ -k "chat" -v
```

### 生成测试报告

```bash
# 只生成JSON报告
pytest tests/validation/ --report-format json

# 只生成HTML报告
pytest tests/validation/ --report-format html

# 生成两种报告（默认）
pytest tests/validation/ --report-format both

# 自定义报告输出路径
pytest tests/validation/ --html=reports/my_report.html --self-contained-html
```

### 调试测试

```bash
# 显示详细输出（-vv显示更详细）
pytest tests/validation/test_agent.py -vv

# 停在第一个失败
pytest tests/validation/ -x

# 进入pdb调试器（失败时）
pytest tests/validation/ --pdb

# 显示print输出（默认捕获）
pytest tests/validation/ -s
```

### CI/CD模式

```bash
# 自动确认模式（不等待用户输入）
pytest tests/validation/ --auto-confirm

# 安静模式（减少输出）
pytest tests/validation/ -q

# 最严格模式（任何警告都视为失败）
pytest tests/validation/ -W error
```

## 测试结果解读

### 通过率标准

根据功能规范，测试通过率要求如下：

| 优先级 | 要求 | 说明 |
|--------|------|------|
| P1 | 100% | Agent功能、数据传输必须完全通过 |
| P2 | ≥95% | 文件操作、检索功能允许少量失败 |
| P3 | ≥90% | 历史记录功能允许更多失败 |

### 测试报告示例

```
========================== test session starts ==========================
platform linux -- Python 3.11.0
collected 28 items

test_agent.py::test_agent_simple_chat PASSED [  3%]
test_agent.py::test_agent_tool_call PASSED [  7%]
test_data_transmission.py::test_text_response PASSED [ 10%]
...
test_history.py::test_history_persistence PASSED [100%]

=================== 27 passed, 1 failed in 95.23s ====================

Summary:
- P1: 10/10 passed (100.0%) ✓
- P2: 14/15 passed (93.3%) ✗ (要求: ≥95%)
- P3: 3/3 passed (100.0%) ✓
- Overall: 27/28 passed (96.4%)
```

### 常见失败原因

1. **API调用失败**
   - 症状：`APICallError: API调用失败`
   - 原因：API Key无效或网络问题
   - 解决：检查`ZHIPU_API_KEY`环境变量

2. **超时**
   - 症状：`AssertionError: 耗时X秒，超过最大限制Y秒`
   - 原因：网络延迟或API响应慢
   - 解决：重试或增加超时时间

3. **文件不存在**
   - 症状：`FileTransferError: 文件不存在: xxx`
   - 原因：测试文件未创建或路径错误
   - 解决：检查test_files_upload/目录

4. **断言失败**
   - 症状：`AssertionError: 响应内容不相关`
   - 原因：实际输出与预期不符
   - 解决：检查测试代码或被测功能

## 故障排除

### 问题1: pytest命令找不到

```bash
# 症状: pytest: command not found
# 解决: 确保虚拟环境已激活
source .venv/bin/activate
pytest --version  # 验证安装
```

### 问题2: API Key未设置

```bash
# 症状: ZHIPU_API_KEY 环境变量未设置
# 解决: 设置环境变量
export ZHIPU_API_KEY='your-api-key-here'

# 或创建 .env 文件
echo "ZHIPU_API_KEY=your-api-key-here" > .env
```

### 问题3: 导入错误

```bash
# 症状: ModuleNotFoundError: No module named 'server'
# 解决: 确保在项目根目录且PYTHONPATH正确
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/validation/
```

### 问题4: 异步测试失败

```bash
# 症状: pytest-asyncio插件未安装或配置错误
# 解决: 安装pytest-asyncio
uv pip install pytest-asyncio
```

## 下一步

### 查看详细文档

- **功能规范**: [spec.md](spec.md)
- **研究文档**: [research.md](research.md)
- **数据模型**: [data-model.md](data-model.md)
- **测试API**: [contracts/test-api.yaml](contracts/test-api.yaml)

### 添加新的测试用例

1. 在对应的测试文件中添加新函数
2. 使用@pytest.mark.asyncio装饰异步测试
3. 使用@pytest.mark.P1/P2/P3标记优先级
4. 遵循Given-When-Then格式

示例：

```python
@pytest.mark.asyncio
@pytest.mark.P1
@pytest.mark.functional
async def test_my_new_test(fresh_agent):
    """
    测试描述

    Given: 前置条件
    When: 执行动作
    Then: 预期结果
    """
    # Given
    test_input = "..."

    # When
    result = await fresh_agent.chat(test_input)

    # Then
    assert result is not None
    assert "expected" in result
```

### 运行特定阶段的测试

```bash
# 只运行Agent功能测试（P1）
pytest tests/validation/test_agent.py -v

# 只运行文件操作测试（P2）
pytest tests/validation/test_file_operations.py -v

# 只运行边界测试
pytest tests/validation/ -m boundary -v
```

## 最佳实践

1. **运行测试前先验证环境**
   ```bash
   # 检查Python版本
   python --version

   # 检查API Key
   echo $ZHIPU_API_KEY

   # 检查虚拟环境
   which python
   ```

2. **按优先级逐步测试**
   ```bash
   # 先运行P1（最快）
   pytest tests/validation/ -m P1 -v

   # P1通过后运行P2
   pytest tests/validation/ -m P2 -v

   # 最后运行P3
   pytest tests/validation/ -m P3 -v
   ```

3. **使用标记灵活选择测试**
   ```bash
   # 只运行功能测试
   pytest tests/validation/ -m functional -v

   # 只运行边界测试
   pytest tests/validation/ -m boundary -v

   # 排除慢速测试
   pytest tests/validation/ -m "not slow" -v
   ```

4. **保存测试报告**
   ```bash
   # 生成带时间戳的报告
   pytest tests/validation/ \
     --html=reports/report_$(date +%Y%m%d_%H%M%S).html \
     --self-contained-html \
     -v
   ```

## 获取帮助

如果遇到问题：

1. 查看日志文件：`logs/test_validation.log`
2. 查看详细错误：`pytest tests/validation/ -vv`
3. 查看项目文档：`docs/`目录
4. 查看项目章程：`.specify/memory/constitution.md`

## 附录: 测试命令速查表

| 命令 | 说明 |
|------|------|
| `pytest tests/validation/` | 运行所有测试 |
| `pytest tests/validation/ -v` | 详细输出 |
| `pytest tests/validation/ -m P1` | 只运行P1测试 |
| `pytest tests/validation/ -k "chat"` | 运行包含"chat"的测试 |
| `pytest tests/validation/ -x` | 停在第一个失败 |
| `pytest tests/validation/ --pdb` | 失败时进入调试器 |
| `pytest tests/validation/ --html=report.html` | 生成HTML报告 |
| `pytest tests/validation/ --auto-confirm` | 自动确认模式 |
