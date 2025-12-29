# 数据模型: 测试全面重构与实现验证

**功能分支**: `001-test-overhaul-validation`
**生成日期**: 2025-12-29
**状态**: 阶段 1 输出

## 概述

本文档定义了测试重构和实现验证项目中的核心数据模型，包括测试配置、测试结果、配置验证规则和错误状态模型。

## 核心实体

### 1. 测试配置模型

```python
from typing import Optional, List
from pydantic import BaseModel, Field


class TestConfig(BaseModel):
    """测试配置模型"""

    # API 配置
    api_key: str = Field(..., description="智谱 API key")
    api_key_valid: bool = Field(default=False, description="API key 是否有效")
    api_key_last_validated: Optional[str] = Field(
        default=None, description="API key 最后验证时间（ISO 8601）"
    )

    # 模型配置
    chat_model: str = Field(default="glm-4-flash", description="聊天模型")
    embed_model: str = Field(default="embedding-3-pro", description="嵌入模型")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="温度参数")
    max_tokens: int = Field(default=128000, ge=1, le=128000, description="最大 token 数")

    # 测试配置
    timeout: float = Field(default=30.0, ge=1.0, description="API 调用超时时间（秒）")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="重试次数")
    parallel_tests: int = Field(default=1, ge=1, le=10, description="并行测试数量")

    # 覆盖率配置
    coverage_threshold: float = Field(
        default=90.0, ge=0.0, le=100.0, description="覆盖率目标（百分比）"
    )
    coverage_report_formats: List[str] = Field(
        default=["term", "html", "xml"], description="覆盖率报告格式"
    )

    # 性能阈值
    response_time_threshold: float = Field(
        default=2.0, ge=0.1, description="响应时间阈值（秒）"
    )
    server_startup_time_threshold: float = Field(
        default=10.0, ge=1.0, description="服务器启动时间阈值（秒）"
    )


class ValidationRule(BaseModel):
    """配置验证规则"""

    field_name: str = Field(..., description="字段名称")
    field_type: str = Field(..., description="字段类型")
    required: bool = Field(default=True, description="是否必需")
    validator: Optional[str] = Field(default=None, description="验证器函数名")
    error_message: str = Field(..., description="验证失败时的错误消息")


class ConfigValidationResult(BaseModel):
    """配置验证结果"""

    is_valid: bool = Field(..., description="配置是否有效")
    errors: List[str] = Field(default_factory=list, description="错误消息列表")
    warnings: List[str] = Field(default_factory=list, description="警告消息列表")
    validated_fields: List[str] = Field(default_factory=list, description="已验证的字段")
    missing_fields: List[str] = Field(default_factory=list, description="缺失的字段")
```

### 2. 测试结果模型

```python
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any


class TestStatus(str, Enum):
    """测试状态枚举"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class TestResult(BaseModel):
    """单个测试结果"""

    test_name: str = Field(..., description="测试名称")
    test_file: str = Field(..., description="测试文件路径")
    status: TestStatus = Field(..., description="测试状态")
    duration: float = Field(..., ge=0.0, description="测试执行时间（秒）")
    error_message: Optional[str] = Field(default=None, description="错误消息")
    error_type: Optional[str] = Field(default=None, description="错误类型")
    traceback: Optional[str] = Field(default=None, description="堆栈跟踪")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="测试元数据")


class TestSuiteResult(BaseModel):
    """测试套件结果"""

    suite_name: str = Field(..., description="测试套件名称")
    total_tests: int = Field(..., ge=0, description="总测试数")
    passed: int = Field(..., ge=0, description="通过测试数")
    failed: int = Field(..., ge=0, description="失败测试数")
    skipped: int = Field(..., ge=0, description="跳过测试数")
    errors: int = Field(..., ge=0, description="错误测试数")
    total_duration: float = Field(..., ge=0.0, description="总执行时间（秒）")
    success_rate: float = Field(..., ge=0.0, le=100.0, description="成功率（百分比）")
    results: List[TestResult] = Field(default_factory=list, description="详细测试结果")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
```

### 3. 性能指标模型

```python
class PerformanceMetric(BaseModel):
    """性能指标"""

    metric_name: str = Field(..., description="指标名称")
    actual_value: float = Field(..., description="实际值")
    threshold: float = Field(..., description="阈值")
    unit: str = Field(default="s", description="单位")
    passed: bool = Field(..., description="是否通过")
    exceeded_by: Optional[float] = Field(default=None, description="超出量")


class PerformanceReport(BaseModel):
    """性能报告"""

    test_name: str = Field(..., description="测试名称")
    metrics: List[PerformanceMetric] = Field(default_factory=list, description="性能指标列表")
    overall_passed: bool = Field(..., description="整体是否通过")
    timestamp: datetime = Field(default_factory=datetime.now, description="测试时间")
```

### 4. API 调用模型

```python
class APICallRecord(BaseModel):
    """API 调用记录"""

    operation: str = Field(..., description="操作名称")
    endpoint: str = Field(..., description="API 端点")
    method: str = Field(default="POST", description="HTTP 方法")
    request_time: datetime = Field(..., description="请求时间")
    response_time: Optional[float] = Field(default=None, description="响应时间（秒）")
    status_code: Optional[int] = Field(default=None, description="HTTP 状态码")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(default=None, description="错误消息")

    # 请求信息（脱敏）
    request_headers: Dict[str, str] = Field(
        default_factory=dict, description="请求头（API key 已脱敏）"
    )
    request_body_summary: Optional[str] = Field(default=None, description="请求体摘要")

    # 响应信息
    response_body_summary: Optional[str] = Field(default=None, description="响应体摘要")


class APIValidationError(BaseModel):
    """API 验证错误"""

    field_name: str = Field(..., description="错误字段")
    error_code: Optional[str] = Field(default=None, description="错误码")
    error_message: str = Field(..., description="错误消息")
    suggested_fix: str = Field(..., description="修复建议")
    severity: str = Field(default="error", description="严重程度（error/warning/info）")
```

### 5. 上下文压缩模型

```python
class MessageScore(BaseModel):
    """消息评分"""

    message_id: str = Field(..., description="消息 ID")
    role: str = Field(..., description="消息角色（system/user/assistant）")
    content_length: int = Field(..., ge=0, description="内容长度（字符）")
    token_count: int = Field(..., ge=0, description="Token 数量")

    # 评分组件
    time_decay_score: float = Field(..., ge=0.0, le=1.0, description="时间衰减评分")
    type_score: float = Field(..., ge=0.0, le=1.0, description="消息类型评分")
    keyword_score: float = Field(..., ge=0.0, le=1.0, description="关键词评分")
    length_score: float = Field(..., ge=0.0, le=1.0, description="长度评分")
    user_flag_score: float = Field(..., ge=0.0, le=1.0, description="用户标记评分")

    # 综合评分
    overall_score: float = Field(..., ge=0.0, le=1.0, description="综合评分")


class CompressionResult(BaseModel):
    """压缩结果"""

    original_message_count: int = Field(..., ge=0, description="原始消息数")
    compressed_message_count: int = Field(..., ge=0, description="压缩后消息数")
    original_token_count: int = Field(..., ge=0, description="原始 token 数")
    compressed_token_count: int = Field(..., ge=0, description="压缩后 token 数")
    compression_ratio: float = Field(..., ge=0.0, le=1.0, description="压缩率（0-1）")
    compression_duration_ms: float = Field(..., ge=0.0, description="压缩耗时（毫秒）")

    # 保留的消息
    kept_messages: List[str] = Field(default_factory=list, description="保留的消息 ID")
    removed_messages: List[str] = Field(default_factory=list, description="移除的消息 ID")

    # 评分统计
    average_score: float = Field(..., ge=0.0, le=1.0, description="保留消息的平均评分")
    min_score: float = Field(..., ge=0.0, le=1.0, description="保留消息的最低评分")
```

## 配置验证规则

### 服务器配置验证

| 字段 | 类型 | 必需 | 验证规则 | 错误消息 |
|------|------|------|----------|----------|
| `server.host` | string | 是 | 有效 IP 地址或"0.0.0.0" | "服务器主机地址无效" |
| `server.port` | integer | 是 | 1024-65535 | "端口号必须在 1024-65535 之间" |
| `server.max_clients` | integer | 是 | 1-100 | "最大客户端数必须在 1-100 之间" |
| `server.heartbeat_interval` | integer | 是 | 30-300 | "心跳间隔必须在 30-300 秒之间" |

### LLM 配置验证

| 字段 | 类型 | 必需 | 验证规则 | 错误消息 |
|------|------|------|----------|----------|
| `llm.chat_model` | string | 是 | glm-4-flash 或 glm-4.5-flash | "聊天模型必须是 glm-4-flash 或 glm-4.5-flash" |
| `llm.embed_model` | string | 是 | embedding-3-pro | "嵌入模型必须是 embedding-3-pro" |
| `llm.temperature` | float | 是 | 0.0-1.0 | "温度参数必须在 0.0-1.0 之间" |
| `llm.max_tokens` | integer | 是 | 1-128000 | "最大 token 数必须在 1-128000 之间" |
| `llm.api_key` | string | 是 | 格式为 id.secret | "API key 格式无效（应为 id.secret）" |

### 环境变量验证

| 变量名 | 类型 | 必需 | 验证规则 | 错误消息 |
|--------|------|------|----------|----------|
| `ZHIPU_API_KEY` | string | 是 | 非空且包含"." | "ZHIPU_API_KEY 未设置或格式无效" |

## 错误状态模型

### 服务器启动错误

```python
class ServerStartupError(BaseModel):
    """服务器启动错误"""

    error_type: str = Field(..., description="错误类型")
    component: str = Field(..., description="组件名称")
    error_message: str = Field(..., description="错误消息")
    stack_trace: Optional[str] = Field(default=None, description="堆栈跟踪")
    fix_suggestions: List[str] = Field(default_factory=list, description="修复建议")


# 常见错误类型
SERVER_STARTUP_ERROR_TYPES = {
    "config_file_missing": "配置文件缺失",
    "config_yaml_invalid": "YAML 格式无效",
    "api_key_missing": "API key 未配置",
    "api_key_invalid": "API key 无效",
    "port_in_use": "端口已被占用",
    "llm_init_failed": "LLM Provider 初始化失败",
    "storage_init_failed": "存储层初始化失败",
}
```

### 测试错误

```python
class TestError(BaseModel):
    """测试错误"""

    test_name: str = Field(..., description="测试名称")
    error_type: str = Field(..., description="错误类型")
    error_message: str = Field(..., description="错误消息")
    file_path: str = Field(..., description="文件路径")
    line_number: int = Field(..., ge=1, description="行号")
    function_name: str = Field(..., description="函数名称")
    stack_trace: str = Field(..., description="堆栈跟踪")
    context: Dict[str, Any] = Field(default_factory=dict, description="错误上下文")
    fix_suggestion: str = Field(..., description="修复建议")


# 常见错误类型
TEST_ERROR_TYPES = {
    "assertion_failed": "断言失败",
    "api_call_failed": "API 调用失败",
    "timeout": "测试超时",
    "setup_failed": "测试设置失败",
    "teardown_failed": "测试清理失败",
    "import_error": "导入错误",
    "dependency_missing": "依赖缺失",
}
```

## 关系图

```
TestConfig (测试配置)
    ├── ValidationRule[] (验证规则)
    └── ConfigValidationResult (验证结果)

TestSuiteResult (测试套件结果)
    └── TestResult[] (测试结果)
        ├── TestStatus (状态)
        └── TestError (错误)

APICallRecord (API 调用记录)
    └── APIValidationError (验证错误)

PerformanceReport (性能报告)
    └── PerformanceMetric[] (性能指标)

CompressionResult (压缩结果)
    ├── MessageScore[] (消息评分)
    └── 保留/移除消息 ID 列表
```

## 数据持久化

### 测试结果存储

测试结果将持久化到以下位置：

- **日志文件**: `logs/pytest.log` - pytest 运行日志
- **覆盖率报告**: `htmlcov/index.html` - HTML 覆盖率报告
- **覆盖率数据**: `.coverage` - 覆盖率原始数据
- **XML 报告**: `coverage.xml` - CI/CD 集成报告

### 压缩数据存储

压缩相关数据存储在：

- **压缩历史**: `storage/history/compression_history.json` - 压缩操作记录
- **评分缓存**: `storage/history/score_cache.json` - 消息评分缓存（加速后续压缩）

## 验证规则示例

### 示例 1: 配置验证

```python
from typing import List, Tuple
import yaml


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate_server_config(config_path: str) -> Tuple[bool, List[str]]:
        """
        验证服务器配置

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误消息列表)
        """
        errors = []

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            errors.append("配置文件不存在")
            return False, errors
        except yaml.YAMLError as e:
            errors.append(f"YAML 格式无效: {e}")
            return False, errors

        # 验证服务器配置
        server = config.get('server', {})
        if 'host' not in server:
            errors.append("server.host 字段缺失")
        if 'port' not in server:
            errors.append("server.port 字段缺失")
        elif not (1024 <= server['port'] <= 65535):
            errors.append("server.port 必须在 1024-65535 之间")

        # 验证 LLM 配置
        llm = config.get('llm', {})
        if 'chat_model' not in llm:
            errors.append("llm.chat_model 字段缺失")
        if 'api_key' not in llm:
            errors.append("llm.api_key 字段缺失")
        elif '.' not in llm['api_key']:
            errors.append("llm.api_key 格式无效（应为 id.secret）")

        return len(errors) == 0, errors
```

### 示例 2: API Key 验证

```python
class APIKeyValidator:
    """API Key 验证器"""

    @staticmethod
    def validate_format(api_key: str) -> Tuple[bool, str]:
        """
        验证 API key 格式

        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        if not api_key:
            return False, "API key 为空"

        if not isinstance(api_key, str):
            return False, f"API key 类型错误：{type(api_key)}"

        if '.' not in api_key:
            return False, "API key 格式无效（缺少 '.' 分隔符）"

        parts = api_key.split('.')
        if len(parts) != 2:
            return False, "API key 格式无效（分隔符数量错误）"

        id_part, secret_part = parts
        if not id_part or not secret_part:
            return False, "API key 格式无效（id 或 secret 部分为空）"

        return True, ""
```

## 总结

本文档定义了测试重构项目中的所有核心数据模型，包括：

1. **测试配置模型**: 测试配置、验证规则、验证结果
2. **测试结果模型**: 测试结果、测试套件结果
3. **性能指标模型**: 性能指标、性能报告
4. **API 调用模型**: API 调用记录、验证错误
5. **上下文压缩模型**: 消息评分、压缩结果
6. **错误状态模型**: 服务器启动错误、测试错误

所有模型都使用 Pydantic 进行验证，确保数据一致性和类型安全。
