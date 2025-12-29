# 数据模型: Agent功能验证测试

**功能**: Agent功能全面验证测试
**日期**: 2025-12-29
**目的**: 定义测试框架中使用的所有数据实体

## 实体关系图

```
TestSuite
  ├── TestCase (10个: T001-T010)
  │     ├── Input: user_message, conversation_history
  │     ├── Output: response, tool_calls
  │     ├── PerformanceMetrics
  │     └── ValidationResult (验收场景)
  └── TestReport
        ├── test_case: TestCase
        ├── result: TestResult
        └── markdown_report: str
```

---

## 实体 1: TestCase（测试用例）

### 描述

代表一个独立的测试场景，对应功能规范中的一个用户故事。

### 字段

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | str | 是 | 测试编号（如"T001"）|
| name | str | 是 | 测试名称（如"基础对话功能验证"）|
| priority | str | 是 | 优先级（"P1", "P2", "P3"）|
| description | str | 是 | 测试描述 |
| user_story | str | 是 | 对应的用户故事描述 |
| acceptance_scenarios | List[AcceptanceScenario] | 是 | 验收场景列表 |
| test_type | str | 是 | 测试类型（"unit", "integration", "system"）|

### 验证规则

- id 必须匹配模式 `T\d{3}`（3位数字）
- priority 必须是 "P1", "P2", 或 "P3"
- acceptance_scenarios 不能为空

### 状态转换

N/A（测试用例是静态定义）

### Python实现

```python
from dataclasses import dataclass
from typing import List

@dataclass
class AcceptanceScenario:
    """验收场景"""
    given: str  # 初始状态
    when: str   # 操作
    then: str   # 预期结果
    passed: bool = False  # 是否通过

@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    priority: str
    description: str
    user_story: str
    acceptance_scenarios: List[AcceptanceScenario]
    test_type: str = "integration"
```

---

## 实体 2: TestResult（测试结果）

### 描述

记录测试执行的实际结果，包括响应、工具调用、性能指标等。

### 字段

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| test_case_id | str | 是 | 关联的测试用例ID |
| status | str | 是 | 测试状态（"passed", "failed", "skipped"）|
| timestamp | str | 是 | 执行时间（ISO 8601格式）|
| user_input | str | 是 | 用户输入消息 |
| agent_response | str | 是 | Agent的回复 |
| tool_calls | List[ToolCall] | 是 | 工具调用列表（复用现有ToolCall）|
| performance_metrics | PerformanceMetrics | 是 | 性能指标 |
| validation_results | List[ValidationResult] | 是 | 验收结果 |
| error_message | str | 否 | 失败时的错误信息 |

### 验证规则

- status 必须是 "passed", "failed", 或 "skipped"
- tool_calls 不能为 None（可以为空列表）
- 如果 status == "failed"，error_message 必须非空

### Python实现

```python
from src.storage.history import ToolCall  # 复用现有ToolCall

@dataclass
class TestResult:
    """测试结果"""
    test_case_id: str
    status: str
    timestamp: str
    user_input: str
    agent_response: str
    tool_calls: List[ToolCall]
    performance_metrics: 'PerformanceMetrics'
    validation_results: List['ValidationResult']
    error_message: str = ""
```

---

## 实体 3: PerformanceMetrics（性能指标）

### 描述

记录测试执行过程中的性能数据，用于验证性能相关的成功标准。

### 字段

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| total_response_time | float | 是 | 总响应时间（秒），从用户输入到Agent回复 |
| tool_call_count | int | 是 | 工具调用次数 |
| tool_execution_times | List[float] | 是 | 每个工具的执行时间（秒）|
| tool_execution_total | float | 是 | 工具执行总时间（秒）|
| average_tool_execution | float | 是 | 平均工具执行时间（秒）|
| llm_call_count | int | 是 | LLM调用次数 |
| llm_total_time | float | 是 | LLM调用总时间（秒）|

### 验证规则

- 所有时间字段必须 ≥ 0
- tool_call_count 必须 == len(tool_execution_times)
- average_tool_execution = tool_execution_total / tool_call_count（如果 tool_call_count > 0）

### 成功标准映射

- SC-002: total_response_time < 2.0（90%的情况下）
- SC-003: 所有 tool_execution_times < 5.0（100%）

### Python实现

```python
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_response_time: float
    tool_call_count: int
    tool_execution_times: List[float]
    tool_execution_total: float
    average_tool_execution: float
    llm_call_count: int
    llm_total_time: float

    def calculate_average(self):
        """计算平均工具执行时间"""
        if self.tool_call_count > 0:
            self.average_tool_execution = self.tool_execution_total / self.tool_call_count
        else:
            self.average_tool_execution = 0.0
```

---

## 实体 4: ValidationResult（验证结果）

### 描述

记录单个验收场景的验证结果。

### 字段

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| scenario_id | int | 是 | 场景编号（1-based）|
| scenario_description | str | 是 | 场景描述 |
| expected | str | 是 | 预期结果 |
| actual | str | 是 | 实际结果 |
| passed | bool | 是 | 是否通过 |
| notes | str | 否 | 备注信息 |

### 验证规则

- scenario_id 必须 ≥ 1
- expected 和 actual 不能为空

### Python实现

```python
@dataclass
class ValidationResult:
    """验证结果"""
    scenario_id: int
    scenario_description: str
    expected: str
    actual: str
    passed: bool
    notes: str = ""
```

---

## 实体 5: TestReport（测试报告）

### 描述

汇总测试用例和测试结果，生成人类可读的报告。

### 字段

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| test_case | TestCase | 是 | 测试用例 |
| test_result | TestResult | 是 | 测试结果 |
| report_path | str | 是 | 报告文件路径 |
| generated_at | str | 是 | 生成时间（ISO 8601格式）|

### 方法

- `generate_markdown() -> str` - 生成Markdown格式的报告
- `save() -> None` - 保存报告到文件

### Python实现

```python
from pathlib import Path

class TestReport:
    """测试报告生成器"""

    def __init__(self, test_case: TestCase, test_result: TestResult, report_path: str):
        self.test_case = test_case
        self.test_result = test_result
        self.report_path = report_path
        self.generated_at = datetime.now().isoformat()

    def generate_markdown(self) -> str:
        """生成Markdown格式的报告"""
        # 实现详见 contracts/test-report-schema.md
        pass

    def save(self):
        """保存报告到文件"""
        Path(self.report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.report_path).write_text(self.generate_markdown(), encoding='utf-8')
```

---

## 实体 6: TestSuite（测试套件）

### 描述

管理所有测试用例，支持按优先级分组和执行。

### 字段

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| name | str | 是 | 测试套件名称 |
| test_cases | List[TestCase] | 是 | 所有测试用例 |
| results | List[TestResult] | 是 | 所有测试结果 |

### 方法

- `get_by_priority(priority: str) -> List[TestCase]` - 按优先级获取测试
- `get_by_id(test_id: str) -> TestCase` - 按ID获取测试
- `add_result(result: TestResult) -> None` - 添加测试结果

### Python实现

```python
@dataclass
class TestSuite:
    """测试套件"""
    name: str
    test_cases: List[TestCase]
    results: List[TestResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

    def get_by_priority(self, priority: str) -> List[TestCase]:
        """按优先级获取测试"""
        return [tc for tc in self.test_cases if tc.priority == priority]

    def get_by_id(self, test_id: str) -> TestCase:
        """按ID获取测试"""
        for tc in self.test_cases:
            if tc.id == test_id:
                return tc
        raise ValueError(f"测试用例不存在: {test_id}")

    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)
```

---

## 数据流

```
1. 定义测试用例 (TestCase)
   ↓
2. 执行测试 → 收集数据 → TestResult
   ↓                ↓
   │            PerformanceMetrics
   │            ValidationResult
   ↓
3. 生成报告 (TestReport)
   ↓
4. 保存Markdown文件
```

---

## 测试用例定义（10个）

### P1组（核心功能）

```python
TEST_CASES_P1 = [
    TestCase(
        id="T001",
        name="基础对话功能验证",
        priority="P1",
        description="验证Agent的基础对话能力",
        user_story="用户希望验证Agent的基础对话能力，确保它能够进行正常的问答交流",
        acceptance_scenarios=[
            AcceptanceScenario(
                given="Agent已初始化并连接到智谱API",
                when="用户发送问候消息'你好'",
                then="Agent应该返回友好的问候回复，不调用任何工具"
            ),
            # ... 更多场景
        ]
    ),
    # T002-T004...
]
```

### P2组（进阶功能）

```python
TEST_CASES_P2 = [
    TestCase(id="T005", name="多轮工具调用验证", priority="P2", ...),
    TestCase(id="T006", name="RAG检索工具验证", priority="P2", ...),
    TestCase(id="T007", name="对话上下文验证", priority="P2", ...),
    TestCase(id="T008", name="工具超时和错误处理验证", priority="P2", ...),
    TestCase(id="T009", name="模型切换功能验证", priority="P2", ...),
]
```

### P3组（边缘场景）

```python
TEST_CASES_P3 = [
    TestCase(id="T010", name="API失败降级验证", priority="P3", ...),
]
```

---

## 复用的现有数据结构

### ToolCall（来自 src/storage/history.py）

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

### ConversationHistory（来自 src/storage/history.py）

```python
class ConversationHistory:
    @staticmethod
    def create_new(session_id: str) -> ConversationHistory:
        """创建新的对话历史"""
        ...

    def get_context(self, max_turns: int = 5) -> List[Message]:
        """获取上下文"""
        ...
```

---

## 下一步

数据模型已定义完成。接下来将在 contracts/ 中定义：
1. test-report-schema.md - 测试报告的Markdown格式规范
