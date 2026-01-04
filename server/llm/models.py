"""
模型配置常量

定义可用的 LLM 模型和默认配置。
"""

# 默认聊天模型
DEFAULT_CHAT_MODEL = "glm-4-flash"

# 可用的聊天模型列表
AVAILABLE_MODELS = [
    "glm-4-flash",      # 快速、低成本
    "glm-4.5-flash",    # 更高性能
]

# 嵌入模型
EMBED_MODEL = "embedding-3-pro"

# 模型配置
MODEL_CONFIGS = {
    "glm-4-flash": {
        "temperature": 0.7,
        "max_tokens": 128000,  # 支持长上下文（128K tokens）
        "timeout": 300,  # 增加超时时间以支持长文本生成
    },
    "glm-4.5-flash": {
        "temperature": 0.7,
        "max_tokens": 128000,  # 支持长上下文（128K tokens）
        "timeout": 300,  # 增加超时时间以支持长文本生成
    },
}

# Embedding 模型配置
EMBED_CONFIG = {
    "embedding-3-pro": {
        "dimension": 3072,  # 向量维度
        "timeout": 30,
    }
}
