# 智能上下文压缩算法设计报告

**功能**: FR-009d 会话切换上下文压缩
**日期**: 2025-12-29
**版本**: 1.0
**状态**: 设计阶段

---

## 1. 背景与目标

### 1.1 当前实现状态

**文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/src/storage/history.py`

当前实现的上下文管理机制：
- `get_context(max_turns=10)`: 简单地返回最近 N 轮对话（固定窗口）
- **问题**: 缺少智能压缩，无法根据 token 阈值动态调整
- **问题**: 无重要性评分机制，可能删除关键信息
- **问题**: 无法处理超长对话历史（超过模型上下文窗口）

### 1.2 设计目标

1. **基于 token 阈值的智能压缩**: 当上下文 token 数超过模型限制时触发压缩
2. **重要性评分机制**: 根据多个维度评分，保留高价值消息
3. **保持对话连贯性**: 压缩后 AI 仍能理解对话上下文
4. **性能优化**: 快速计算，避免增加过多延迟
5. **可配置性**: 支持调整压缩阈值和评分策略

---

## 2. Token 计数方法设计

### 2.1 智谱 GLM Token 特性

根据研究结果：

**模型上下文窗口**:
- **GLM-4 / GLM-4-Flash**: 128K tokens (输入) + 4K tokens (输出)
- **GLM-4.5**: 96K tokens (输出)
- **GLM-4.6V**: 128K tokens (输入)

**中文 Token 估算规则**:
- 1 个中文字符 ≈ 0.7-1 token
- 1 个英文单词 ≈ 0.75 token
- 混合内容根据语言比例动态变化

**参考来源**:
- [智谱AI GLM-4 文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-4)
- [大语言模型千问、gpt、智谱token计算-tiktoken](https://blog.csdn.net/Code_LT/article/details/140721869)
- [AI大模型应用开发实践：使用tiktoken计算token数量](https://blog.csdn.net/wangjiansui/article/details/139142146)

### 2.2 Token 计数方案对比

| 方案 | 准确性 | 性能 | 复杂度 | 推荐度 |
|------|--------|------|--------|--------|
| **方案 1: Tiktoken** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **方案 2: API 估算** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **方案 3: 简化计算** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **方案 4: 字符长度** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ |

**推荐**: **方案 1 (Tiktoken) + 方案 3 (简化计算) 混合**

### 2.3 Tiktoken 集成方案

**依赖添加**:

```toml
# pyproject.toml
dependencies = [
    "tiktoken>=0.5.0",  # 添加 tiktoken 依赖
    # ... 其他依赖
]
```

**实现代码**:

```python
"""
Token 计数工具模块

支持使用 tiktoken 或简化计算估算文本 token 数
"""

import tiktoken
from typing import List, Dict, Optional

class TokenCounter:
    """Token 计数器

    使用 tiktoken 库进行精确 token 计算，或使用简化估算方法
    """

    # 编码器缓存（按模型名称）
    _encoders: Dict[str, tiktoken.Encoding] = {}

    # 中文 token 估算系数（1 中文字符 ≈ 0.85 token）
    CN_CHAR_RATIO = 0.85

    # 英文 token 估算系数（1 英文单词 ≈ 0.75 token）
    EN_WORD_RATIO = 0.75

    @classmethod
    def get_encoder(cls, model: str = "gpt-4") -> tiktoken.Encoding:
        """获取 tiktoken 编码器（带缓存）

        Args:
            model: 模型名称（默认使用 gpt-4 编码器作为通用估算）

        Returns:
            tiktoken.Encoding 实例
        """
        if model not in cls._encoders:
            try:
                # 尝试获取特定模型的编码器
                cls._encoders[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # 如果模型不存在，使用 cl100k_base (GPT-4) 作为通用编码器
                cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
        return cls._encoders[model]

    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-4") -> int:
        """计算文本的 token 数量（精确计算）

        Args:
            text: 待计算文本
            model: 模型名称（用于选择编码器）

        Returns:
            token 数量
        """
        if not text:
            return 0

        encoder = cls.get_encoder(model)
        tokens = encoder.encode(text)
        return len(tokens)

    @classmethod
    def count_tokens_fast(cls, text: str) -> int:
        """快速估算 token 数量（简化计算）

        适用于性能敏感场景，准确度约 85-90%

        Args:
            text: 待计算文本

        Returns:
            估算的 token 数量
        """
        if not text:
            return 0

        # 统计中文字符
        cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

        # 统计英文单词（按空格分词）
        en_words = len(text.split())

        # 估算 token 数
        estimated_tokens = int(cn_chars * cls.CN_CHAR_RATIO + en_words * cls.EN_WORD_RATIO)

        return max(estimated_tokens, 1)  # 至少 1 个 token

    @classmethod
    def count_messages_tokens(
        cls,
        messages: List[Dict],
        model: str = "gpt-4",
        use_fast: bool = False
    ) -> int:
        """计算消息列表的总 token 数

        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "..."}, ...]
            model: 模型名称
            use_fast: 是否使用快速估算（默认 False，使用精确计算）

        Returns:
            总 token 数
        """
        total_tokens = 0

        for msg in messages:
            # 消息内容的 token 数
            content = msg.get("content", "")
            if use_fast:
                total_tokens += cls.count_tokens_fast(content)
            else:
                total_tokens += cls.count_tokens(content, model)

            # 消息格式的额外开销（role、格式字符等）
            # 每条消息约 4 个 token 的格式开销
            total_tokens += 4

        return total_tokens

    @classmethod
    def count_chatmessage_tokens(
        cls,
        chatmessage_list: List["ChatMessage"],
        model: str = "gpt-4",
        use_fast: bool = False
    ) -> int:
        """计算 ChatMessage 对象列表的总 token 数

        Args:
            chatmessage_list: ChatMessage 对象列表
            model: 模型名称
            use_fast: 是否使用快速估算

        Returns:
            总 token 数
        """
        total_tokens = 0

        for msg in chatmessage_list:
            if use_fast:
                total_tokens += cls.count_tokens_fast(msg.content)
            else:
                total_tokens += cls.count_tokens(msg.content, model)

            # 格式开销
            total_tokens += 4

            # 如果包含工具调用，额外计算
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_json = str(tc.to_dict())
                    if use_fast:
                        total_tokens += cls.count_tokens_fast(tool_json)
                    else:
                        total_tokens += cls.count_tokens(tool_json, model)

        return total_tokens


# 单例实例（便于全局使用）
token_counter = TokenCounter()
```

**使用示例**:

```python
# 精确计算（推荐）
token_count = TokenCounter.count_tokens("你好世界，这是一个测试")

# 快速估算（性能敏感场景）
token_count_fast = TokenCounter.count_tokens_fast("你好世界，这是一个测试")

# 计算消息列表
messages = [
    {"role": "user", "content": "帮我检查一下服务器内存"},
    {"role": "assistant", "content": "总内存: 16GB，已使用: 8.5GB (53%)"}
]
total_tokens = TokenCounter.count_messages_tokens(messages)
```

### 2.4 Token 计数性能优化

**优化策略**:
1. **编码器缓存**: 避免重复加载 tiktoken 编码器
2. **批量计算**: 一次性计算多条消息的 token 数
3. **快速模式**: 对于长历史使用简化估算（性能提升 5-10 倍）
4. **延迟计算**: 仅在需要压缩时才计算 token 数

**性能基准**（参考）:
- Tiktoken 精确计算: ~1ms/1000 字符
- 简化估算: ~0.1ms/1000 字符
- 对于 100 轮对话（约 10K 字符），精确计算耗时约 10ms（可接受）

---

## 3. 重要性评分策略设计

### 3.1 评分因素设计

基于研究成果和最佳实践，设计以下评分因素：

| 评分因素 | 权重 | 说明 | 评分函数 |
|----------|------|------|----------|
| **时间衰减** | 0.3 | 最近的对话更重要 | `score_time = 1.0 / (1 + age_hours / 24)` |
| **消息类型** | 0.25 | 系统提示、工具调用结果更重要 | `score_type = {system: 1.0, tool_result: 0.9, user: 0.7, assistant: 0.6}` |
| **关键词匹配** | 0.2 | 包含关键信息的消息保留 | `score_keywords = matched_keywords / total_keywords` |
| **消息长度** | 0.1 | 较长的消息通常包含更多信息 | `score_length = min(len(content) / 500, 1.0)` |
| **用户标记** | 0.15 | 用户显式标记的消息优先保留 | `score_user = 1.0 if marked else 0.0` |

**参考来源**:
- [大模型应用中的对话压缩方法综述](https://zhuanlan.zhihu.com/p/1927119710392124301)
- [从被逆向的Claude Code解析上下文工程](https://www.53ai.com/news/LargeLanguageModel/2025080309284.html)
- [AI Agent 上下文管理：基于搭叩的七大原则与实践](https://www.infoq.cn/article/ufsvugyl6fvvmqx67ycc)

### 3.2 评分算法实现

```python
"""
消息重要性评分模块

根据多个维度评估对话消息的重要性，用于智能上下文压缩
"""

from datetime import datetime, timedelta
from typing import List, Set, Optional
from dataclasses import dataclass

@dataclass
class ImportanceScore:
    """重要性评分结果"""
    total_score: float        # 总分（0-1）
    time_score: float         # 时间衰减分数
    type_score: float         # 类型分数
    keyword_score: float      # 关键词分数
    length_score: float       # 长度分数
    user_score: float         # 用户标记分数


class MessageScorer:
    """消息重要性评分器"""

    # 评分权重配置
    WEIGHT_TIME = 0.3
    WEIGHT_TYPE = 0.25
    WEIGHT_KEYWORD = 0.2
    WEIGHT_LENGTH = 0.1
    WEIGHT_USER = 0.15

    # 消息类型重要性
    TYPE_IMPORTANCE = {
        "system": 1.0,         # 系统提示最重要
        "user": 0.7,           # 用户消息次之
        "assistant": 0.6,      # AI 回复
    }

    # 关键词列表（可配置）
    DEFAULT_KEYWORDS: Set[str] = {
        # 命令类
        "执行", "命令", "运行", "调用", "检查", "查看",

        # 错误类
        "错误", "失败", "异常", "问题", "bug",

        # 重要信息
        "注意", "重要", "必须", "关键", "核心",

        # 技术术语
        "服务器", "内存", "磁盘", "网络", "日志",

        # 结论类
        "结果", "结论", "总结", "完成", "成功",
    }

    def __init__(
        self,
        keywords: Optional[Set[str]] = None,
        reference_time: Optional[datetime] = None
    ):
        """初始化评分器

        Args:
            keywords: 自定义关键词列表（默认使用 DEFAULT_KEYWORDS）
            reference_time: 参考时间（默认使用当前时间）
        """
        self.keywords = keywords or self.DEFAULT_KEYWORDS
        self.reference_time = reference_time or datetime.now()

    def score_message(
        self,
        chatmessage: "ChatMessage",
        user_marked: bool = False
    ) -> ImportanceScore:
        """对单条消息进行重要性评分

        Args:
            chatmessage: ChatMessage 对象
            user_marked: 是否被用户标记为重要

        Returns:
            ImportanceScore 评分结果
        """
        # 1. 时间衰减分数
        time_score = self._score_time_decay(chatmessage.timestamp)

        # 2. 消息类型分数
        type_score = self._score_message_type(chatmessage.role)

        # 3. 关键词匹配分数
        keyword_score = self._score_keywords(chatmessage.content)

        # 4. 消息长度分数
        length_score = self._score_length(chatmessage.content)

        # 5. 用户标记分数
        user_score = 1.0 if user_marked else 0.0

        # 计算加权总分
        total_score = (
            time_score * self.WEIGHT_TIME +
            type_score * self.WEIGHT_TYPE +
            keyword_score * self.WEIGHT_KEYWORD +
            length_score * self.WEIGHT_LENGTH +
            user_score * self.WEIGHT_USER
        )

        return ImportanceScore(
            total_score=total_score,
            time_score=time_score,
            type_score=type_score,
            keyword_score=keyword_score,
            length_score=length_score,
            user_score=user_score
        )

    def _score_time_decay(self, timestamp: datetime) -> float:
        """计算时间衰减分数

        策略:
        - 最近 1 小时: 1.0 分
        - 1-24 小时: 0.8 分
        - 1-7 天: 0.6 分
        - 7-30 天: 0.4 分
        - 30 天以上: 0.2 分

        Args:
            timestamp: 消息时间戳

        Returns:
            时间分数（0-1）
        """
        age = self.reference_time - timestamp
        age_hours = age.total_seconds() / 3600

        if age_hours < 1:
            return 1.0
        elif age_hours < 24:
            return 0.8
        elif age_hours < 168:  # 7 天
            return 0.6
        elif age_hours < 720:  # 30 天
            return 0.4
        else:
            return 0.2

    def _score_message_type(self, role: str) -> float:
        """计算消息类型分数

        Args:
            role: 消息角色（user, assistant, system）

        Returns:
            类型分数（0-1）
        """
        return self.TYPE_IMPORTANCE.get(role, 0.5)

    def _score_keywords(self, content: str) -> float:
        """计算关键词匹配分数

        Args:
            content: 消息内容

        Returns:
            关键词分数（0-1）
        """
        if not content:
            return 0.0

        matched_count = 0
        content_lower = content.lower()

        for keyword in self.keywords:
            if keyword.lower() in content_lower:
                matched_count += 1

        # 避免除以零
        if not self.keywords:
            return 0.0

        # 归一化到 [0, 1]
        return min(matched_count / len(self.keywords), 1.0)

    def _score_length(self, content: str) -> float:
        """计算消息长度分数

        策略:
        - 长度 >= 500 字符: 1.0 分
        - 长度 < 500 字符: 按比例计算

        Args:
            content: 消息内容

        Returns:
            长度分数（0-1）
        """
        if not content:
            return 0.0

        length = len(content)
        return min(length / 500, 1.0)

    def score_messages(
        self,
        messages: List["ChatMessage"],
        user_marked_indices: Optional[Set[int]] = None
    ) -> List[ImportanceScore]:
        """批量评分消息列表

        Args:
            messages: ChatMessage 列表
            user_marked_indices: 用户标记的消息索引集合

        Returns:
            ImportanceScore 列表（与 messages 一一对应）
        """
        user_marked_indices = user_marked_indices or set()

        scores = []
        for idx, msg in enumerate(messages):
            user_marked = idx in user_marked_indices
            score = self.score_message(msg, user_marked)
            scores.append(score)

        return scores
```

### 3.3 评分策略调优

**可配置项**:

1. **权重调整**: 根据实际效果调整各因素权重
2. **关键词定制**: 根据业务场景定制关键词列表
3. **时间衰减曲线**: 可调整为线性或指数衰减
4. **类型重要性**: 根据实际需求调整

**调优建议**:

- **初期**: 使用默认配置，观察压缩效果
- **中期**: 根据用户反馈调整关键词和权重
- **长期**: 使用机器学习方法自动优化评分函数（参考 DSPy 框架）

---

## 4. 智能压缩算法设计

### 4.1 压缩触发条件

**触发条件**（满足任一即触发）:

1. **Token 阈值触发**: 上下文 token 数 > 模型上下文窗口 * 0.7（安全余量）
   - GLM-4: 阈值 = 128K * 0.7 = 89,600 tokens
   - GLM-4.5: 阈值 = 96K * 0.7 = 67,200 tokens

2. **消息数量触发**: 消息数量 > 配置的最大消息数（默认 100 条）

3. **手动触发**: 用户执行 /compress 命令

### 4.2 压缩算法流程

```
┌─────────────────────────────────────────────────────────────┐
│                    智能压缩算法流程                          │
└─────────────────────────────────────────────────────────────┘

输入:
  - messages: 完整对话历史
  - max_tokens: 最大 token 限制
  - scorer: 重要性评分器

步骤 1: 计算 token 数
  ├─ 计算当前上下文总 token 数
  └─ 如果 total_tokens <= max_tokens，不压缩，返回

步骤 2: 重要性评分
  ├─ 对所有消息评分（使用 MessageScorer）
  └─ 生成 (message, score) 列表

步骤 3: 强制保留关键消息
  ├─ 保留系统提示（role == "system"）
  ├─ 保留最近 N 条消息（默认 10 条）
  └─ 保留用户标记的消息

步骤 4: 按重要性排序剩余消息
  ├─ 对剩余消息按 score 降序排序
  └─ 计算保留的 token 预算

步骤 5: 选择消息
  ├─ 从高到低选择消息，直到达到 token 预算
  └─ 确保至少保留 30% 的原始消息

步骤 6: 重新排序
  └─ 按时间顺序重新排序选中的消息

输出:
  - compressed_messages: 压缩后的消息列表
  - compression_ratio: 压缩率
  - metadata: 压缩元数据（保留的消息索引等）
```

### 4.3 压缩算法实现

```python
"""
智能上下文压缩模块

基于 token 阈值和重要性评分的上下文压缩机制
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CompressionResult:
    """压缩结果"""
    compressed_messages: List["ChatMessage"]  # 压缩后的消息列表
    original_count: int                       # 原始消息数量
    compressed_count: int                     # 压缩后消息数量
    original_tokens: int                      # 原始 token 数
    compressed_tokens: int                    # 压缩后 token 数
    compression_ratio: float                  # 压缩率 (compressed / original)
    metadata: dict                            # 压缩元数据


class ContextCompressor:
    """上下文压缩器"""

    # 默认配置
    DEFAULT_MAX_TOKENS = 89600  # GLM-4 的 70%
    DEFAULT_MIN_RECENT = 10      # 至少保留最近 10 条消息
    DEFAULT_MIN_RETENTION = 0.3  # 至少保留 30% 的消息

    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        min_recent: int = DEFAULT_MIN_RECENT,
        min_retention: float = DEFAULT_MIN_RETENTION,
        scorer: Optional[MessageScorer] = None,
        token_counter: Optional[TokenCounter] = None
    ):
        """初始化压缩器

        Args:
            max_tokens: 最大 token 数（触发压缩的阈值）
            min_recent: 至少保留最近 N 条消息
            min_retention: 至少保留的消息比例（0-1）
            scorer: 重要性评分器（默认创建新实例）
            token_counter: Token 计数器（默认使用精确计算）
        """
        self.max_tokens = max_tokens
        self.min_recent = min_recent
        self.min_retention = min_retention
        self.scorer = scorer or MessageScorer()
        self.token_counter = token_counter or TokenCounter()

    def should_compress(
        self,
        messages: List["ChatMessage"],
        use_fast: bool = False
    ) -> bool:
        """判断是否需要压缩

        Args:
            messages: 消息列表
            use_fast: 是否使用快速 token 计算

        Returns:
            是否需要压缩
        """
        if not messages:
            return False

        # 计算 token 数
        total_tokens = self.token_counter.count_chatmessage_tokens(
            messages,
            use_fast=use_fast
        )

        # 判断是否超过阈值
        return total_tokens > self.max_tokens

    def compress(
        self,
        messages: List["ChatMessage"],
        use_fast: bool = False,
        user_marked_indices: Optional[set[int]] = None
    ) -> CompressionResult:
        """执行智能压缩

        Args:
            messages: 原始消息列表
            use_fast: 是否使用快速 token 计算
            user_marked_indices: 用户标记的消息索引

        Returns:
            CompressionResult 压缩结果
        """
        if not messages:
            return CompressionResult(
                compressed_messages=[],
                original_count=0,
                compressed_count=0,
                original_tokens=0,
                compressed_tokens=0,
                compression_ratio=0.0,
                metadata={}
            )

        # 步骤 1: 计算原始 token 数
        original_tokens = self.token_counter.count_chatmessage_tokens(
            messages,
            use_fast=use_fast
        )

        # 如果未超过阈值，不压缩
        if original_tokens <= self.max_tokens:
            logger.debug(f"Token 数 ({original_tokens}) 未超过阈值 ({self.max_tokens})，无需压缩")
            return CompressionResult(
                compressed_messages=messages,
                original_count=len(messages),
                compressed_count=len(messages),
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                metadata={"compressed": False}
            )

        logger.info(f"开始压缩: 原始 {len(messages)} 条消息, {original_tokens} tokens")

        # 步骤 2: 重要性评分
        scores = self.scorer.score_messages(messages, user_marked_indices)

        # 步骤 3: 强制保留关键消息
        reserved_indices = self._get_reserved_indices(messages, scores)

        # 步骤 4: 按重要性排序剩余消息
        remaining_indices = [
            i for i in range(len(messages))
            if i not in reserved_indices
        ]

        # 按 score 降序排序
        remaining_indices.sort(
            key=lambda i: scores[i].total_score,
            reverse=True
        )

        # 步骤 5: 选择消息（贪心算法）
        selected_indices = self._select_messages(
            messages,
            reserved_indices,
            remaining_indices,
            use_fast=use_fast
        )

        # 步骤 6: 按时间顺序重新排序
        selected_indices.sort()

        # 构建压缩后的消息列表
        compressed_messages = [messages[i] for i in selected_indices]

        # 计算压缩后的 token 数
        compressed_tokens = self.token_counter.count_chatmessage_tokens(
            compressed_messages,
            use_fast=use_fast
        )

        # 计算压缩率
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        logger.info(
            f"压缩完成: {len(messages)} -> {len(compressed_messages)} 条消息, "
            f"{original_tokens} -> {compressed_tokens} tokens "
            f"(压缩率: {compression_ratio:.1%})"
        )

        return CompressionResult(
            compressed_messages=compressed_messages,
            original_count=len(messages),
            compressed_count=len(compressed_messages),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            metadata={
                "compressed": True,
                "selected_indices": selected_indices,
                "reserved_indices": reserved_indices,
                "scores": [(i, scores[i].total_score) for i in selected_indices]
            }
        )

    def _get_reserved_indices(
        self,
        messages: List["ChatMessage"],
        scores: List[ImportanceScore]
    ) -> set[int]:
        """获取必须保留的消息索引

        Args:
            messages: 消息列表
            scores: 评分列表

        Returns:
            保留的消息索引集合
        """
        reserved = set()

        for i, (msg, score) in enumerate(zip(messages, scores)):
            # 1. 系统提示
            if msg.role == "system":
                reserved.add(i)

            # 2. 用户标记的消息
            elif score.user_score > 0:
                reserved.add(i)

            # 3. 最近 N 条消息
            elif i >= len(messages) - self.min_recent:
                reserved.add(i)

        return reserved

    def _select_messages(
        self,
        messages: List["ChatMessage"],
        reserved_indices: set[int],
        remaining_indices: List[int],
        use_fast: bool
    ) -> List[int]:
        """从剩余消息中选择高价值消息

        Args:
            messages: 消息列表
            reserved_indices: 已保留的消息索引
            remaining_indices: 剩余消息索引（已按重要性排序）
            use_fast: 是否使用快速 token 计算

        Returns:
            选中的消息索引列表
        """
        selected = list(reserved_indices)

        # 计算当前 token 数
        current_tokens = self.token_counter.count_chatmessage_tokens(
            [messages[i] for i in selected],
            use_fast=use_fast
        )

        # 计算剩余 token 预算
        remaining_budget = self.max_tokens - current_tokens

        # 贪心选择：从高到低添加消息，直到达到预算
        for idx in remaining_indices:
            if remaining_budget <= 0:
                break

            msg_tokens = self.token_counter.count_tokens_fast(messages[idx].content)

            if msg_tokens <= remaining_budget:
                selected.append(idx)
                remaining_budget -= msg_tokens

        # 确保至少保留 min_retention 比例的消息
        min_count = max(
            int(len(messages) * self.min_retention),
            self.min_recent
        )

        if len(selected) < min_count:
            # 补充到最小数量（从剩余消息中按重要性顺序添加）
            for idx in remaining_indices:
                if idx not in selected:
                    selected.append(idx)
                if len(selected) >= min_count:
                    break

        return selected
```

### 4.4 压缩算法特点

**优点**:
1. **智能保留**: 基于多维度评分，保留高价值消息
2. **安全余量**: 强制保留系统提示和最近消息
3. **可配置性**: 支持调整阈值、权重、关键词
4. **性能优化**: 支持快速 token 估算模式
5. **透明性**: 返回压缩元数据，便于调试和分析

**注意事项**:
1. **压缩率**: 目标压缩率 30-50%（保留 50-70% 的信息）
2. **连贯性**: 压缩后按时间排序，保持对话流程
3. **最低保障**: 至少保留 30% 的消息，避免过度压缩
4. **用户感知**: 可在日志中记录压缩决策，便于用户理解

---

## 5. 集成方案设计

### 5.1 在 ConversationHistory 中集成

**修改文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/src/storage/history.py`

**新增方法**:

```python
class ConversationHistory:
    """对话历史（增强版：支持智能压缩）"""

    # ... 现有代码 ...

    def get_context_compressed(
        self,
        max_tokens: int = 89600,
        min_recent: int = 10,
        min_retention: float = 0.3,
        user_marked_indices: Optional[set[int]] = None
    ) -> List[ChatMessage]:
        """获取智能压缩后的上下文

        Args:
            max_tokens: 最大 token 数（默认 GLM-4 的 70%）
            min_recent: 至少保留最近 N 条消息
            min_retention: 至少保留的消息比例（0-1）
            user_marked_indices: 用户标记的消息索引

        Returns:
            压缩后的消息列表
        """
        # 如果消息列表为空，返回空列表
        if not self.messages:
            return []

        # 导入压缩器（延迟导入，避免循环依赖）
        from src.storage.compression import ContextCompressor, TokenCounter

        # 创建压缩器
        compressor = ContextCompressor(
            max_tokens=max_tokens,
            min_recent=min_recent,
            min_retention=min_retention
        )

        # 执行压缩
        result = compressor.compress(
            self.messages,
            use_fast=False,  # 使用精确计算
            user_marked_indices=user_marked_indices
        )

        # 记录压缩日志
        if result.metadata.get("compressed"):
            logger.info(
                f"会话 {self.session_id[:8]} 上下文已压缩: "
                f"{result.original_count} -> {result.compressed_count} 条消息, "
                f"压缩率 {result.compression_ratio:.1%}"
            )

        return result.compressed_messages

    def get_context(
        self,
        max_turns: int = 10,
        enable_compression: bool = False,
        max_tokens: Optional[int] = None
    ) -> List[ChatMessage]:
        """获取对话上下文（增强版：支持智能压缩开关）

        Args:
            max_turns: 最大轮数（如果 enable_compression=False）
            enable_compression: 是否启用智能压缩（默认 False）
            max_tokens: 压缩阈值（如果 enable_compression=True）

        Returns:
            消息列表
        """
        # 如果启用压缩
        if enable_compression:
            return self.get_context_compressed(
                max_tokens=max_tokens or 89600
            )

        # 否则使用原始的固定窗口策略
        return self.messages[-max_turns*2:]

    def estimate_tokens(self, use_fast: bool = True) -> int:
        """估算当前对话历史的 token 数

        Args:
            use_fast: 是否使用快速估算

        Returns:
            估算的 token 数
        """
        from src.storage.compression import TokenCounter

        return TokenCounter.count_chatmessage_tokens(
            self.messages,
            use_fast=use_fast
        )
```

### 5.2 会话切换时的上下文加载

**修改文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/src/storage/history.py`

**在 SessionManager.switch_session 方法中集成**:

```python
class SessionManager:
    """会话管理器（增强版）"""

    # ... 现有代码 ...

    def switch_session(
        self,
        session_id: str,
        enable_compression: bool = True,
        max_tokens: int = 89600
    ) -> tuple[bool, Optional[ConversationHistory]]:
        """切换会话（增强版：支持上下文压缩）

        Args:
            session_id: 目标会话 ID
            enable_compression: 是否启用上下文压缩
            max_tokens: 压缩阈值

        Returns:
            (是否切换成功, 加载的对话历史)
        """
        if session_id not in self.sessions:
            return False, None

        if self.sessions[session_id].archived:
            logger.error(f"无法切换到已归档的会话 {session_id}")
            return False, None

        # 加载会话历史
        history = ConversationHistory.load(session_id, self.storage_dir)

        if history is None:
            logger.warning(f"会话 {session_id} 的历史记录未找到")
            # 创建空历史
            history = ConversationHistory.create_new(session_id)

        # 如果启用压缩，压缩上下文
        if enable_compression and history.messages:
            compressed_messages = history.get_context_compressed(
                max_tokens=max_tokens
            )
            logger.info(
                f"会话切换: {session_id[:8]} 上下文已压缩, "
                f"加载 {len(compressed_messages)} 条消息"
            )
            # 注意：这里不修改原始 history，仅在传递给 LLM 时使用压缩版本
        else:
            logger.info(f"会话切换: {session_id[:8]} 加载完整历史")

        # 更新当前会话
        self.current_session_id = session_id
        self.sessions[session_id].touch()
        self._save_sessions()

        return True, history
```

### 5.3 Agent 中的集成

**修改文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/src/server/agent.py`

**在调用 LLM 前启用压缩**:

```python
class Agent:
    """Agent（增强版：支持智能压缩）"""

    # ... 现有代码 ...

    async def process(
        self,
        user_message: str,
        conversation_history: ConversationHistory,
        enable_compression: bool = True,
        max_tokens: int = 89600
    ) -> str:
        """处理用户消息（增强版：支持智能压缩）

        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            enable_compression: 是否启用上下文压缩
            max_tokens: 压缩阈值

        Returns:
            AI 回复
        """
        # 添加用户消息到历史
        conversation_history.add_message("user", user_message)

        # 获取上下文
        if enable_compression:
            # 使用智能压缩
            context_messages = conversation_history.get_context_compressed(
                max_tokens=max_tokens
            )
        else:
            # 使用固定窗口
            context_messages = conversation_history.get_context(max_turns=5)

        # 构建消息列表
        messages = []
        for msg in context_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # ... 调用 LLM ...

        return response
```

---

## 6. 配置与调优

### 6.1 配置文件设计

**修改文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/config.yaml`

**新增压缩配置**:

```yaml
llm:
  chat_model: "glm-4-flash"
  embed_model: "embedding-3-pro"
  temperature: 0.7
  max_tokens: 128000  # GLM-4 上下文窗口
  timeout: 300

# 新增：上下文压缩配置
compression:
  enabled: true               # 是否启用智能压缩
  max_tokens: 89600           # 压缩阈值（70% 的上下文窗口）
  min_recent: 10              # 至少保留最近 10 条消息
  min_retention: 0.3          # 至少保留 30% 的消息
  use_fast_token_count: false # 是否使用快速 token 计算（性能敏感场景）

  # 评分权重
  scoring:
    weight_time: 0.3          # 时间衰减权重
    weight_type: 0.25         # 消息类型权重
    weight_keyword: 0.2       # 关键词匹配权重
    weight_length: 0.1        # 消息长度权重
    weight_user: 0.15         # 用户标记权重

  # 关键词列表（可自定义）
  keywords:
    - "执行"
    - "命令"
    - "错误"
    - "失败"
    - "重要"
    - "注意"
    - "服务器"
    - "内存"
    - "磁盘"
    - "结果"
```

### 6.2 配置加载代码

```python
# src/utils/config.py

@dataclass
class CompressionConfig:
    """压缩配置"""
    enabled: bool = True
    max_tokens: int = 89600
    min_recent: int = 10
    min_retention: float = 0.3
    use_fast_token_count: bool = False

    # 评分权重
    weight_time: float = 0.3
    weight_type: float = 0.25
    weight_keyword: float = 0.2
    weight_length: float = 0.1
    weight_user: float = 0.15

    # 关键词列表
    keywords: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'CompressionConfig':
        """从字典加载配置"""
        scoring = data.get("scoring", {})
        return cls(
            enabled=data.get("enabled", True),
            max_tokens=data.get("max_tokens", 89600),
            min_recent=data.get("min_recent", 10),
            min_retention=data.get("min_retention", 0.3),
            use_fast_token_count=data.get("use_fast_token_count", False),
            weight_time=scoring.get("weight_time", 0.3),
            weight_type=scoring.get("weight_type", 0.25),
            weight_keyword=scoring.get("weight_keyword", 0.2),
            weight_length=scoring.get("weight_length", 0.1),
            weight_user=scoring.get("weight_user", 0.15),
            keywords=data.get("keywords", [])
        )

@dataclass
class AppConfig:
    """应用配置（增强版）"""
    server: ServerConfig
    llm: LLMConfig
    compression: CompressionConfig  # 新增

    # ... 其他代码 ...
```

### 6.3 调优建议

**初期配置**（保守策略）:
- `max_tokens`: 89600 (70% 的上下文窗口)
- `min_retention`: 0.5 (至少保留 50% 的消息)
- `weight_time`: 0.4 (时间权重更高，保留最近消息)

**中期优化**（平衡策略）:
- `max_tokens`: 100000 (78% 的上下文窗口)
- `min_retention`: 0.3 (至少保留 30% 的消息)
- `weight_keyword`: 0.25 (提高关键词权重)

**后期优化**（激进策略）:
- `max_tokens`: 110000 (86% 的上下文窗口)
- `min_retention`: 0.2 (至少保留 20% 的消息)
- 根据实际数据训练评分函数（使用 DSPy 等框架）

---

## 7. 性能分析与优化

### 7.1 性能开销分析

| 操作 | 时间复杂度 | 实际耗时（估算） | 优化建议 |
|------|------------|------------------|----------|
| Token 计数（精确） | O(n) | 10ms / 100 轮对话 | 使用快速模式 |
| Token 计数（快速） | O(n) | 1ms / 100 轮对话 | 推荐使用 |
| 重要性评分 | O(n * k) | 5ms / 100 轮对话 | k 为关键词数 |
| 排序 | O(n log n) | 1ms / 100 条消息 | 可接受 |
| 选择消息 | O(n) | 2ms / 100 条消息 | 可接受 |
| **总计** | - | **19ms** | 可接受 |

**结论**: 对于 100 轮对话，压缩耗时约 20ms，对用户体验影响很小。

### 7.2 优化策略

**已实现的优化**:
1. **编码器缓存**: Tiktoken 编码器复用
2. **快速估算模式**: 可选的简化 token 计算
3. **延迟计算**: 仅在触发压缩时才计算 token 数

**未来优化方向**:
1. **增量计算**: 缓存消息的 token 数，避免重复计算
2. **并行评分**: 使用多线程/多进程批量评分
3. **预压缩**: 在会话保存时预压缩，切换时直接加载
4. **模型量化**: 使用更小的评分模型（如 TinyML）

---

## 8. 测试策略

### 8.1 单元测试

**测试文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/tests/unit/test_compression.py`

**测试用例**:

```python
import pytest
from src.storage.compression import TokenCounter, MessageScorer, ContextCompressor
from src.storage.history import ChatMessage, ConversationHistory
from datetime import datetime, timedelta

class TestTokenCounter:
    """Token 计数器测试"""

    def test_count_tokens_chinese(self):
        """测试中文 token 计数"""
        text = "你好世界，这是一个测试"
        tokens = TokenCounter.count_tokens(text)
        assert tokens > 0
        # 中文字符约 1 字符 = 0.85 token
        assert 10 <= tokens <= 15

    def test_count_tokens_english(self):
        """测试英文 token 计数"""
        text = "Hello world, this is a test"
        tokens = TokenCounter.count_tokens(text)
        assert tokens > 0
        # 英文约 1 词 = 0.75 token
        assert 5 <= tokens <= 10

    def test_count_tokens_fast(self):
        """测试快速估算"""
        text = "你好世界，这是一个测试"
        tokens_fast = TokenCounter.count_tokens_fast(text)
        tokens_exact = TokenCounter.count_tokens(text)

        # 快速估算与精确计算误差在 20% 以内
        assert abs(tokens_fast - tokens_exact) / tokens_exact < 0.2

    def test_count_messages_tokens(self):
        """测试消息列表 token 计数"""
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"}
        ]
        tokens = TokenCounter.count_messages_tokens(messages)
        assert tokens > 10


class TestMessageScorer:
    """消息评分器测试"""

    def test_score_message_recent(self):
        """测试最近消息评分"""
        scorer = MessageScorer()
        msg = ChatMessage(
            role="user",
            content="帮我检查一下服务器内存",
            timestamp=datetime.now()
        )
        score = scorer.score_message(msg)
        assert score.total_score > 0.5  # 最近消息应该高分
        assert score.time_score == 1.0  # 1 小时内消息时间分为 1.0

    def test_score_message_old(self):
        """测试旧消息评分"""
        scorer = MessageScorer()
        old_time = datetime.now() - timedelta(days=40)
        msg = ChatMessage(
            role="user",
            content="这是一条旧消息",
            timestamp=old_time
        )
        score = scorer.score_message(msg)
        assert score.time_score < 0.5  # 旧消息时间分较低

    def test_score_message_system(self):
        """测试系统提示评分"""
        scorer = MessageScorer()
        msg = ChatMessage(
            role="system",
            content="你是一个智能运维助手",
            timestamp=datetime.now()
        )
        score = scorer.score_message(msg)
        assert score.type_score == 1.0  # 系统提示类型分为 1.0

    def test_score_keywords(self):
        """测试关键词匹配"""
        scorer = MessageScorer()
        msg = ChatMessage(
            role="user",
            content="帮我执行命令检查服务器内存错误",
            timestamp=datetime.now()
        )
        score = scorer.score_message(msg)
        assert score.keyword_score > 0.3  # 匹配到关键词应该加分


class TestContextCompressor:
    """上下文压缩器测试"""

    def test_should_compress_no(self):
        """测试不需要压缩的情况"""
        compressor = ContextCompressor(max_tokens=10000)

        messages = [
            ChatMessage(role="user", content="你好", timestamp=datetime.now()),
            ChatMessage(role="assistant", content="你好！", timestamp=datetime.now())
        ]

        should = compressor.should_compress(messages)
        assert should == False  # 短对话不需要压缩

    def test_should_compress_yes(self):
        """测试需要压缩的情况"""
        compressor = ContextCompressor(max_tokens=100)

        # 创建 100 条长消息
        messages = []
        for i in range(100):
            messages.append(ChatMessage(
                role="user" if i % 2 == 0 else "assistant",
                content="这是一条很长的消息内容" * 100,  # 约 700 字符
                timestamp=datetime.now()
            ))

        should = compressor.should_compress(messages, use_fast=True)
        assert should == True  # 长对话需要压缩

    def test_compress_result(self):
        """测试压缩结果"""
        compressor = ContextCompressor(
            max_tokens=1000,
            min_recent=5
        )

        # 创建 50 条消息
        messages = []
        for i in range(50):
            messages.append(ChatMessage(
                role="user" if i % 2 == 0 else "assistant",
                content=f"消息 {i}",
                timestamp=datetime.now() - timedelta(hours=50-i)
            ))

        result = compressor.compress(messages, use_fast=True)

        # 验证压缩结果
        assert result.compressed_count < result.original_count  # 消息数量减少
        assert result.compressed_tokens < result.original_tokens  # token 数减少
        assert result.compression_ratio < 1.0  # 压缩率 < 100%
        assert result.compressed_count >= 5  # 至少保留最近 5 条消息

    def test_compress_preserve_system(self):
        """测试保留系统提示"""
        compressor = ContextCompressor(max_tokens=100)

        messages = [
            ChatMessage(role="system", content="系统提示", timestamp=datetime.now()),
            ChatMessage(role="user", content="用户消息", timestamp=datetime.now()),
            ChatMessage(role="assistant", content="AI回复", timestamp=datetime.now())
        ]

        result = compressor.compress(messages, use_fast=True)

        # 系统提示必须保留
        roles = [msg.role for msg in result.compressed_messages]
        assert "system" in roles

    def test_compress_preserve_recent(self):
        """测试保留最近消息"""
        compressor = ContextCompressor(max_tokens=100, min_recent=3)

        messages = []
        for i in range(20):
            messages.append(ChatMessage(
                role="user",
                content=f"消息 {i}",
                timestamp=datetime.now() - timedelta(hours=20-i)
            ))

        result = compressor.compress(messages, use_fast=True)

        # 最近 3 条消息必须保留
        assert result.compressed_count >= 3


class TestConversationHistoryCompression:
    """对话历史压缩测试"""

    def test_get_context_compressed(self):
        """测试获取压缩后的上下文"""
        history = ConversationHistory.create_new()

        # 添加 50 条消息
        for i in range(50):
            history.add_message(
                "user" if i % 2 == 0 else "assistant",
                f"消息 {i}"
            )

        # 获取压缩后的上下文
        compressed = history.get_context_compressed(max_tokens=1000)

        # 验证压缩结果
        assert len(compressed) < 50
        assert len(compressed) >= 10  # 至少保留最近 10 条

    def test_estimate_tokens(self):
        """测试 token 估算"""
        history = ConversationHistory.create_new()

        history.add_message("user", "你好世界")
        history.add_message("assistant", "你好！")

        tokens = history.estimate_tokens()
        assert tokens > 0
```

### 8.2 集成测试

**测试文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/tests/integration/test_compression_integration.py`

**测试场景**:

```python
import pytest
from src.storage.history import ConversationHistory, SessionManager
from src.storage.compression import ContextCompressor
from datetime import datetime

class TestCompressionIntegration:
    """压缩功能集成测试"""

    def test_session_switch_with_compression(self):
        """测试会话切换时的上下文压缩"""
        manager = SessionManager()

        # 创建会话 1
        session1 = manager.create_session()
        history1 = ConversationHistory.create_new(session1)

        # 添加 100 条消息
        for i in range(100):
            history1.add_message(
                "user" if i % 2 == 0 else "assistant",
                f"会话1的消息 {i}" * 10
            )
        history1.save()

        # 切换会话（启用压缩）
        success, loaded_history = manager.switch_session(
            session1,
            enable_compression=True,
            max_tokens=5000
        )

        assert success
        assert loaded_history is not None

        # 验证压缩效果
        tokens = loaded_history.estimate_tokens()
        assert tokens < 5000 or len(loaded_history.messages) < 100

    def test_agent_with_compression(self):
        """测试 Agent 使用压缩后的上下文"""
        from src.server.agent import Agent

        history = ConversationHistory.create_new()

        # 添加长对话历史
        for i in range(50):
            history.add_message("user", f"问题 {i}")
            history.add_message("assistant", f"回答 {i}" * 100)

        # 使用压缩模式
        # （这里需要 mock LLM 调用，避免实际 API 请求）
        # ...
```

### 8.3 性能测试

**测试文件**: `/home/zhoutianyu/tmp/LLMChatAssistant/tests/performance/test_compression_performance.py`

**性能基准**:

```python
import pytest
import time
from src.storage.compression import ContextCompressor, TokenCounter
from src.storage.history import ChatMessage
from datetime import datetime, timedelta

class TestCompressionPerformance:
    """压缩性能测试"""

    def test_token_count_performance(self):
        """测试 token 计数性能"""
        # 生成 10,000 字符的文本
        text = "你好世界，这是一个测试" * 500

        # 精确计算
        start = time.time()
        for _ in range(100):
            TokenCounter.count_tokens(text)
        duration_exact = (time.time() - start) * 1000  # ms

        # 快速估算
        start = time.time()
        for _ in range(100):
            TokenCounter.count_tokens_fast(text)
        duration_fast = (time.time() - start) * 1000  # ms

        print(f"精确计算: {duration_exact:.2f}ms / 100次")
        print(f"快速估算: {duration_fast:.2f}ms / 100次")
        print(f"加速比: {duration_exact / duration_fast:.1f}x")

        # 验证快速模式确实更快
        assert duration_fast < duration_exact

    def test_compression_performance(self):
        """测试压缩性能"""
        compressor = ContextCompressor(max_tokens=10000)

        # 生成 200 条消息
        messages = []
        for i in range(200):
            messages.append(ChatMessage(
                role="user" if i % 2 == 0 else "assistant",
                content=f"消息 {i}" * 50,
                timestamp=datetime.now() - timedelta(hours=200-i)
            ))

        # 测试压缩耗时
        start = time.time()
        result = compressor.compress(messages, use_fast=True)
        duration = (time.time() - start) * 1000  # ms

        print(f"压缩耗时: {duration:.2f}ms")
        print(f"消息数量: {result.original_count} -> {result.compressed_count}")
        print(f"压缩率: {result.compression_ratio:.1%}")

        # 性能要求：200 条消息压缩时间 < 100ms
        assert duration < 100
```

---

## 9. 部署与监控

### 9.1 部署检查清单

- [ ] 安装 tiktoken 依赖 (`uv add tiktoken`)
- [ ] 更新 config.yaml 添加 compression 配置
- [ ] 部署新的压缩模块 (`src/storage/compression.py`)
- [ ] 更新 ConversationHistory 类
- [ ] 更新 SessionManager.switch_session 方法
- [ ] 更新 Agent.process 方法
- [ ] 运行单元测试验证功能
- [ ] 运行集成测试验证端到端流程
- [ ] 运行性能测试确保无性能回归

### 9.2 监控指标

**关键指标**:

1. **压缩触发率**: 触发压缩的请求比例（目标: < 20%）
2. **压缩率**: 压缩后的 token 占原始 token 的比例（目标: 30-50%）
3. **压缩耗时**: 平均压缩时间（目标: < 50ms）
4. **信息保留率**: 压缩后保留的关键信息比例（目标: > 90%）
5. **用户满意度**: 压缩后 AI 回复质量（人工评估）

**日志示例**:

```python
logger.info(
    f"上下文压缩: "
    f"会话={session_id[:8]}, "
    f"原始={original_tokens} tokens, "
    f"压缩={compressed_tokens} tokens, "
    f"压缩率={compression_ratio:.1%}, "
    f"耗时={duration_ms:.1f}ms"
)
```

---

## 10. 总结与未来工作

### 10.1 实施路径

**阶段 1: 基础实现**（1-2 天）
- 实现 TokenCounter 类
- 实现 MessageScorer 类
- 实现 ContextCompressor 类
- 编写单元测试

**阶段 2: 集成**（1 天）
- 在 ConversationHistory 中集成
- 在 SessionManager 中集成
- 在 Agent 中集成
- 编写集成测试

**阶段 3: 优化**（1 天）
- 性能优化
- 配置调优
- 压力测试

**阶段 4: 部署**（0.5 天）
- 代码审查
- 部署到生产环境
- 监控指标

**总计**: 约 3.5-4.5 天

### 10.2 未来增强

1. **自适应压缩**: 根据对话主题自动调整评分策略
2. **语义摘要**: 使用 LLM 生成旧对话的摘要，而非简单删除
3. **分层存储**: 热数据（最近消息）+ 温数据（压缩摘要）+ 冷数据（归档）
4. **用户反馈**: 允许用户标记重要消息，影响评分权重
5. **多模态压缩**: 支持图片、文件等多模态内容的压缩

---

## 11. 参考资料

### Token 计数
- [智谱AI GLM-4 文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-4)
- [大语言模型千问、gpt、智谱token计算-tiktoken](https://blog.csdn.net/Code_LT/article/details/140721869)
- [AI大模型应用开发实践：使用tiktoken计算token数量](https://blog.csdn.net/wangjiansui/article/details/139142146)
- [Tiktoken 如何精确计算Token？](https://zhuanlan.zhihu.com/p/1928802390741606421)

### 上下文压缩
- [大模型应用中的对话压缩方法综述](https://zhuanlan.zhihu.com/p/1927119710392124301)
- [从被逆向的Claude Code解析上下文工程](https://www.53ai.com/news/LargeLanguageModel/2025080309284.html)
- [AI Agent 上下文管理：基于搭叩的七大原则与实践](https://www.infoq.cn/article/ufsvugyl6fvvmqx67ycc)
- [大模型Agent的"记忆瘦身术"：上下文压缩工程](https://zhuanlan.zhihu.com/p/1953905256908960619)
- [上下文工程的系统应用方法论（2025实践版）](https://aistudio.baidu.com/blog/detail/739580289552645)

### 智谱 API
- [核心参数 - 智谱AI文档](https://docs.bigmodel.cn/cn/guide/start/concept-param)
- [GLM-4.5 API深度解析](https://www.cursor-ide.com/blog/glm-4-5-api)
- [智谱发布GLM-4全家桶：128K长文本](https://hub.baai.ac.cn/view/34438)

---

**文档版本**: 1.0
**作者**: Claude Code
**最后更新**: 2025-12-29
