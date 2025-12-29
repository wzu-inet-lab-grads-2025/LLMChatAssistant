# 研究文档: Agent功能验证测试

**功能**: Agent功能全面验证测试
**日期**: 2025-12-29
**目的**: 解决测试框架设计中的技术问题和最佳实践

## 研究领域 1: pytest异步测试最佳实践

### 决策

使用pytest-asyncio插件，通过@pytest.mark.asyncio装饰器标记异步测试，使用async def定义测试函数。

### 理由

1. **现有代码使用pytest-asyncio** - 查看tests/integration/test_agent.py，现有测试已经使用@pytest.mark.asyncio
2. **标准化做法** - pytest-asyncio是Python异步测试的标准插件
3. **简单集成** - 项目已有pytest配置，无需额外配置

### 实现方案

```python
import pytest

@pytest.mark.asyncio
async def test_agent_basic_conversation():
    """测试Agent基础对话"""
    agent = ReActAgent(llm_provider=llm_provider)
    response, tool_calls = await agent.react_loop(
        user_message="你好",
        conversation_history=history
    )
    assert response is not None
```

### 替代方案

- **使用pytest-trio** - 不适用，项目使用asyncio而非trio
- **手动管理事件循环** - 过于复杂，pytest-asyncio已处理

---

## 研究领域 2: 测试报告格式

### 决策

使用Markdown格式，包含以下章节：测试信息、测试输入、工具链调用详情、最终结果、性能指标、验收结果、测试结论。

### 理由

1. **人类可读** - Markdown易于阅读和渲染
2. **版本控制友好** - 纯文本格式，便于git管理
3. **规范已定义** - 功能规范的"测试报告格式"章节已定义模板
4. **工具支持** - GitHub、VSCode等工具原生支持Markdown

### 实现方案

创建TestReporter类，使用Python的f-string或jinja2模板生成Markdown：

```python
class TestReporter:
    def generate_report(self, test_case: TestCase, result: TestResult) -> str:
        return f"""# 测试报告 {test_case.id}: {test_case.name}

## 测试信息
- 测试编号: {test_case.id}
- 测试名称: {test_case.name}
- 优先级: {test_case.priority}
- 执行时间: {result.timestamp}
- 状态: {self._format_status(result.status)}

## 工具链调用详情
{self._format_tool_calls(result.tool_calls)}

...
"""
```

### 替代方案

- **HTML格式** - 需要额外的模板引擎，对git不够友好
- **JSON格式** - 机器可读但人类不够友好
- **纯文本** - 缺乏结构和格式

---

## 研究领域 3: 用户确认流程

### 决策

使用pytest的命令行参数和交互式输入，在测试类中实现confirm_after_test装饰器或方法。

### 理由

1. **灵活性** - pytest支持命令行参数（--confirm或--auto-confirm）
2. **用户控制** - 用户可以选择自动模式（用于CI/CD）或交互模式（用于本地验证）
3. **简单实现** - 使用Python内置的input()函数

### 实现方案

```python
# conftest.py
def pytest_addoption(parser):
    parser.addoption(
        "--auto-confirm",
        action="store_true",
        default=False,
        help="自动确认测试通过，不等待用户输入"
    )

@pytest.fixture
def auto_confirm(request):
    return request.config.getoption("--auto-confirm")

# test_agent_validation.py
@pytest.mark.asyncio
async def test_t001_basic_conversation(auto_confirm):
    """T001: 基础对话功能验证"""
    # ... 执行测试 ...

    # 生成报告
    report = reporter.generate_report(test_case, result)
    print(report)

    # 等待用户确认（除非auto-confirm=True）
    if not auto_confirm:
        user_input = input("\n测试完成。请确认是否通过？[Y/n] ")
        if user_input.lower() == 'n':
            pytest.fail("用户确认测试未通过")
```

### 替代方案

- **使用pytest-hooks** - 过于复杂，简单场景下不够灵活
- **使用外部测试运行器** - 增加依赖，不符合"复用现有pytest"的原则

---

## 研究领域 4: 性能指标收集

### 决策

使用Python的time.perf_counter()和time.time()函数，在测试代码中手动记录关键时间点。

### 理由

1. **精确度高** - perf_counter()提供高精度时间测量
2. **简单可靠** - 无需额外依赖
3. **现有实现参考** - 查看tests/integration/test_agent.py的第319-373行，已有性能测试实现

### 实现方案

```python
import time

async def run_test_with_metrics(test_case):
    metrics = PerformanceMetrics()

    # 记录开始时间（总响应时间）
    start_time = time.time()

    # 执行Agent react_loop
    response, tool_calls = await agent.react_loop(...)

    # 记录结束时间
    end_time = time.time()
    metrics.total_response_time = end_time - start_time

    # 从tool_calls中提取工具执行时间（Agent已记录）
    metrics.tool_execution_times = [call.duration for call in tool_calls]

    return metrics
```

### 数据结构

```python
@dataclass
class PerformanceMetrics:
    total_response_time: float  # 总响应时间
    tool_call_count: int         # 工具调用次数
    tool_execution_times: List[float]  # 每个工具的执行时间
    tool_execution_total: float  # 工具执行总时间
    average_tool_execution: float  # 平均工具执行时间
```

### 替代方案

- **使用pytest-benchmark** - 需要额外依赖，对于简单的性能指标收集过于重量级
- **使用cProfile** - 主要用于性能分析而非指标收集，过于复杂

---

## 研究领域 5: 测试数据隔离

### 决策

使用pytest的autouse fixtures在每个测试前后创建和清理数据，使用ConversationHistory.create_new()为每个测试创建独立的会话。

### 理由

1. **pytest原生支持** - fixtures是pytest的标准机制
2. **自动清理** - autouse fixtures确保每个测试都运行在干净环境中
3. **会话隔离** - 每个测试使用不同的session_id，避免对话历史污染

### 实现方案

```python
# conftest.py
@pytest.fixture(autouse=True)
async def clean_test_environment():
    """每个测试前后的环境清理"""
    # 测试前：清理临时文件、索引等
    yield
    # 测试后：清理临时数据

@pytest.fixture
async def fresh_agent(llm_provider):
    """为每个测试创建新的Agent实例"""
    agent = ReActAgent(llm_provider=llm_provider)
    return agent

@pytest.fixture
async def fresh_history():
    """为每个测试创建新的对话历史"""
    return ConversationHistory.create_new(f"test-{uuid4()}")
```

### 替代方案

- **使用pytest-xdist并行测试** - 需要额外配置，且API调用可能产生并发问题
- **手动清理** - 容易遗漏，不够可靠

---

## 研究领域 6: ToolCall数据结构分析

### 决策

复用src/storage/history.py中已定义的ToolCall数据类，无需重新定义。

### 理由

1. **已有实现** - ToolCall已在history.py中定义，包含所有必需字段
2. **类型安全** - 使用dataclass提供类型提示和验证
3. **与Agent一致** - Agent返回的tool_calls已经是ToolCall对象

### ToolCall结构（现有）

```python
@dataclass
class ToolCall:
    tool_name: str
    arguments: dict
    result: str
    status: str  # "success", "failed", "timeout"
    duration: float
    timestamp: str
```

### 测试报告中的使用

```python
def _format_tool_call(self, call: ToolCall) -> str:
    return f"""### 工具调用 {index}
- 工具名称: {call.tool_name}
- 调用时间: {call.timestamp}
- 参数: {json.dumps(call.arguments, ensure_ascii=False)}
- 执行时间: {call.duration:.2f}s
- 状态: {call.status}
- 结果: {call.result[:200]}..."""  # 截断长结果
```

---

## 技术栈总结

| 组件 | 选择 | 理由 |
|------|------|------|
| 异步测试 | pytest-asyncio | 现有项目使用，标准化做法 |
| 报告格式 | Markdown | 人类可读、git友好、工具支持 |
| 用户确认 | pytest命令行参数 + input() | 灵活、简单、无额外依赖 |
| 性能测量 | time.perf_counter() | 高精度、无需依赖 |
| 数据隔离 | pytest fixtures | 原生支持、自动清理 |
| 数据结构 | 复用ToolCall dataclass | 与Agent一致、类型安全 |

## 下一步

基于研究结果，接下来将在阶段1生成：
1. data-model.md - 定义TestCase、TestReport、PerformanceMetrics等数据模型
2. contracts/test-report-schema.md - 测试报告的Markdown格式规范
3. quickstart.md - 快速开始指南

所有研究问题已解决，无NEEDS CLARIFICATION标记。
