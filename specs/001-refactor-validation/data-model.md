# 数据模型: 重构后系统验证

**功能**: 重构后系统验证
**日期**: 2026-01-02
**阶段**: 1 - 设计

## 概述

本文档定义了系统验证功能中使用的数据模型，包括测试用例结构、验证报告格式和相关实体。

## 核心实体

### 1. TestCase（测试用例）

表示一个独立的验证场景，包含测试输入、预期结果和实际结果的比较。

**属性**:

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| test_id | str | 是 | 测试用例唯一标识符（如 "T001"） |
| name | str | 是 | 测试用例名称 |
| description | str | 是 | 测试用例描述 |
| priority | str | 是 | 优先级（P1/P2/P3） |
| user_story | str | 是 | 关联的用户故事（如 "US1"） |
| test_type | str | 是 | 测试类型（functional/boundary/error/performance） |
| preconditions | List[str] | 是 | 前置条件列表（Given从句） |
| actions | List[str] | 是 | 测试动作列表（When从句） |
| expected_results | List[str] | 是 | 预期结果列表（Then从句） |
| test_data | Dict | 否 | 测试数据（输入参数、文件路径等） |
| status | str | 是 | 执行状态（pending/passed/failed/skipped） |
| duration | float | 否 | 执行时间（秒） |
| error_message | str | 否 | 错误消息（如失败） |
| stack_trace | str | 否 | 错误堆栈（如失败） |

**示例**:

```python
{
    "test_id": "T001",
    "name": "简单对话请求",
    "description": "验证Agent能够正确响应简单的对话请求",
    "priority": "P1",
    "user_story": "US1",
    "test_type": "functional",
    "preconditions": ["后端服务已启动"],
    "actions": ["发送简单对话请求: '你好'"],
    "expected_results": [
        "系统返回正确格式的响应",
        "响应内容符合预期（包含问候）"
    ],
    "test_data": {
        "message": "你好",
        "model": "glm-4-flash"
    },
    "status": "passed",
    "duration": 2.3,
    "error_message": None,
    "stack_trace": None
}
```

### 2. ValidationResult（验证结果）

表示单个测试的执行结果，包含详细的执行信息。

**属性**:

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| test_id | str | 是 | 关联的测试用例ID |
| passed | bool | 是 | 是否通过 |
| duration | float | 是 | 执行时间（秒） |
| timestamp | str | 是 | 执行时间戳（ISO 8601） |
| actual_output | Any | 否 | 实际输出 |
| expected_output | Any | 否 | 预期输出 |
| error_type | str | 否 | 错误类型（如失败） |
| error_message | str | 否 | 错误消息 |
| stack_trace | str | 否 | 错误堆栈 |
| retry_count | int | 是 | 重试次数 |
| screenshots | List[str] | 否 | 截图路径列表（如适用） |

### 3. TestSuite（测试套件）

表示一组相关的测试用例，通常对应一个功能模块或用户故事。

**属性**:

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| suite_id | str | 是 | 测试套件唯一标识符（如 "agent_suite"） |
| name | str | 是 | 测试套件名称 |
| description | str | 是 | 测试套件描述 |
| priority | str | 是 | 优先级（P1/P2/P3） |
| test_cases | List[TestCase] | 是 | 包含的测试用例列表 |
| total_tests | int | 是 | 总测试数 |
| passed_tests | int | 是 | 通过测试数 |
| failed_tests | int | 是 | 失败测试数 |
| skipped_tests | int | 是 | 跳过测试数 |
| pass_rate | float | 是 | 通过率（0-100） |
| total_duration | float | 是 | 总执行时间（秒） |

**计算规则**:
- total_tests = len(test_cases)
- passed_tests = count(tc.status == "passed" for tc in test_cases)
- failed_tests = count(tc.status == "failed" for tc in test_cases)
- skipped_tests = count(tc.status == "skipped" for tc in test_cases)
- pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
- total_duration = sum(tc.duration for tc in test_cases if tc.duration)

### 4. ValidationReport（验证报告）

表示完整的验证测试执行报告，汇总所有测试结果。

**属性**:

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| report_id | str | 是 | 报告唯一标识符（UUID） |
| report_type | str | 是 | 报告类型（comprehensive/quick/regression） |
| start_time | str | 是 | 开始时间（ISO 8601） |
| end_time | str | 是 | 结束时间（ISO 8601） |
| duration | float | 是 | 总执行时间（秒） |
| environment | Dict | 是 | 测试环境信息 |
| test_suites | List[TestSuite] | 是 | 测试套件列表 |
| summary | Summary | 是 | 测试摘要 |
| errors | List[ErrorInfo] | 是 | 错误列表 |
| artifacts | List[str] | 否 | 产物列表（日志、截图等） |

**Summary（摘要）**:

| 字段名 | 类型 | 描述 |
|--------|------|------|
| total_tests | int | 总测试数 |
| passed_tests | int | 通过测试数 |
| failed_tests | int | 失败测试数 |
| skipped_tests | int | 跳过测试数 |
| overall_pass_rate | float | 总体通过率 |
| p1_pass_rate | float | P1测试通过率 |
| p2_pass_rate | float | P2测试通过率 |
| p3_pass_rate | float | P3测试通过率 |

**ErrorInfo（错误信息）**:

| 字段名 | 类型 | 描述 |
|--------|------|------|
| test_id | str | 测试用例ID |
| error_type | str | 错误类型 |
| error_message | str | 错误消息 |
| stack_trace | str | 错误堆栈 |
| severity | str | 严重程度（critical/major/minor） |

**Environment（环境信息）**:

| 字段名 | 类型 | 描述 |
|--------|------|------|
| python_version | str | Python版本 |
| os | str | 操作系统 |
| test_date | str | 测试日期 |
| branch | str | Git分支 |
| commit_hash | str | Git提交哈希 |
| api_model | str | 使用的LLM模型 |
| test_runner | str | 测试运行器 |

**示例报告**:

```json
{
    "report_id": "vr-20260102-001",
    "report_type": "comprehensive",
    "start_time": "2026-01-02T10:00:00Z",
    "end_time": "2026-01-02T10:15:30Z",
    "duration": 930.0,
    "environment": {
        "python_version": "3.11.0",
        "os": "Linux 5.15.0",
        "test_date": "2026-01-02",
        "branch": "001-refactor-validation",
        "commit_hash": "abc123",
        "api_model": "glm-4-flash",
        "test_runner": "pytest 8.0.0"
    },
    "test_suites": [...],
    "summary": {
        "total_tests": 28,
        "passed_tests": 27,
        "failed_tests": 1,
        "skipped_tests": 0,
        "overall_pass_rate": 96.4,
        "p1_pass_rate": 100.0,
        "p2_pass_rate": 95.0,
        "p3_pass_rate": 90.0
    },
    "errors": [
        {
            "test_id": "T012",
            "error_type": "AssertionError",
            "error_message": "文件内容不匹配",
            "stack_trace": "...",
            "severity": "major"
        }
    ],
    "artifacts": [
        "logs/test_validation.log",
        "reports/test_report.html",
        "reports/test_report.json"
    ]
}
```

### 5. TestData（测试数据）

表示测试过程中使用的样本数据。

**类型**:

| 数据类型 | 描述 | 存储位置 |
|---------|------|----------|
| 文本文件 | 用于测试文件上传下载的样本文本文件 | test_files_upload/ |
| 二进制文件 | 用于测试二进制传输的样本文件 | test_files_upload/ |
| 对话记录 | 用于测试历史记录的样本对话 | 在测试中动态生成 |
| 查询请求 | 用于测试检索的样本查询 | 在测试代码中定义 |

**示例**:

```python
# test_files_upload/readme.txt
"这是一个测试文件用于验证文件上传下载功能。"

# test_files_upload/data.json
{"name": "测试", "value": 123}
```

## 数据流

### 测试执行流程

```
1. 读取测试配置 → 2. 创建测试用例 → 3. 执行测试
                                    ↓
6. 生成报告 ← 5. 汇总结果 ← 4. 记录结果
```

### 实体关系

```
ValidationReport (1)
    ├── TestSuite (N)
    │   └── TestCase (N)
    │       └── ValidationResult (1)
    └── Summary (1)
    └── ErrorInfo (N)
```

## 验证规则

### 测试用例验证规则

1. **唯一性**: test_id必须在所有测试用例中唯一
2. **完整性**: 必填字段不能为空
3. **格式**: timestamp必须符合ISO 8601格式
4. **范围**: priority必须是P1、P2或P3之一
5. **状态**: status必须是pending、passed、failed或skipped之一

### 验证报告验证规则

1. **一致性**: passed_tests + failed_tests + skipped_tests = total_tests
2. **范围**: pass_rate必须在0-100之间
3. **时序**: end_time必须晚于或等于start_time
4. **完整性**: 至少包含一个测试套件

## 状态转换

### TestCase状态转换

```
pending → passed (测试通过)
    ↓
  failed (测试失败)
    ↓
passed (重试后通过)
    ↓
  skipped (跳过测试)
```

### 优先级处理规则

1. **P1测试失败**: 阻止提交，必须立即修复
2. **P2测试失败**: 记录并确定修复优先级，95%通过率要求
3. **P3测试失败**: 记录但不阻止合并，90%通过率要求

## 持久化

### 存储位置

| 数据类型 | 存储位置 | 格式 |
|---------|----------|------|
| 测试日志 | logs/test_validation.log | 纯文本 |
| HTML报告 | reports/test_report.html | HTML |
| JSON报告 | reports/test_report_YYYYMMDD_HHMMSS.json | JSON |
| 测试历史 | storage/test_results/ | JSON |

### 命名规范

- **测试文件**: test_<module>.py（如 test_agent.py）
- **报告文件**: test_report_YYYYMMDD_HHMMSS.json
- **日志文件**: test_validation.log（追加写入）

## 附录: 数据模型实现

### Python类型定义

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class TestStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TestType(str, Enum):
    FUNCTIONAL = "functional"
    BOUNDARY = "boundary"
    ERROR = "error"
    PERFORMANCE = "performance"

@dataclass
class TestCase:
    test_id: str
    name: str
    description: str
    priority: Priority
    user_story: str
    test_type: TestType
    preconditions: List[str]
    actions: List[str]
    expected_results: List[str]
    test_data: Dict[str, Any]
    status: TestStatus = TestStatus.PENDING
    duration: Optional[float] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
```
