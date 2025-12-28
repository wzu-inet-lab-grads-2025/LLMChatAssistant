"""
配置管理模块

提供系统配置管理和环境变量验证功能。
遵循章程：测试真实性（启动前验证 API key）
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str
    chat_model: str = "glm-4-flash"
    available_models: list = None
    embed_model: str = "embedding-3-pro"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30

    def __post_init__(self):
        if self.available_models is None:
            self.available_models = ["glm-4-flash", "glm-4.5-flash"]

    def validate(self) -> bool:
        """验证配置有效性"""
        return (
            bool(self.api_key) and
            0 <= self.temperature <= 1 and
            self.chat_model in self.available_models
        )


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 9999
    max_clients: int = 10
    heartbeat_interval: int = 90  # 心跳间隔（秒）
    storage_dir: str = "storage"
    logs_dir: str = "logs"
    log_level: str = "INFO"


@dataclass
class Config:
    """全局配置"""
    llm: LLMConfig
    server: ServerConfig

    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置"""
        api_key = os.getenv('ZHIPU_API_KEY', '')

        if not api_key:
            raise ValueError(
                "ZHIPU_API_KEY 未配置。请设置环境变量：\n"
                "  export ZHIPU_API_KEY='your-api-key'\n"
                "或在 .env 文件中配置。"
            )

        llm_config = LLMConfig(api_key=api_key)

        if not llm_config.validate():
            raise ValueError(f"LLM 配置无效：{llm_config}")

        server_config = ServerConfig()

        return cls(
            llm=llm_config,
            server=server_config
        )


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def validate_api_key() -> bool:
    """验证智谱 API key 是否已配置（遵循章程：测试真实性）"""
    api_key = os.getenv('ZHIPU_API_KEY', '')
    return bool(api_key)
