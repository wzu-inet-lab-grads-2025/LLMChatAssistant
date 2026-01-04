"""
配置管理模块

提供系统配置管理和环境变量验证功能。
支持 config.yaml + .env 配置策略。
遵循章程：测试真实性（启动前验证 API key）
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "zhipu"
    api_key: str = ""
    chat_model: str = "glm-4-flash"
    embed_model: str = "embedding-3-pro"
    temperature: float = 0.7
    max_tokens: int = 128000
    timeout: int = 30

    def validate(self) -> bool:
        """验证配置有效性"""
        return (
            bool(self.api_key) and
            0 <= self.temperature <= 1 and
            self.chat_model in ["glm-4-flash", "glm-4.5-flash"]
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
class StreamingConfig:
    """流式输出配置"""
    enabled: bool = True  # 是否启用流式输出
    chunk_size: int = 20  # 每次发送的字符数（建议 10-50）
    delay: float = 0.05  # 每次发送的延迟秒数（建议 0.03-0.1）

    def validate(self) -> bool:
        """验证配置有效性"""
        return (
            1 <= self.chunk_size <= 100 and
            0.01 <= self.delay <= 0.5
        )


@dataclass
class FileAccessConfig:
    """文件访问安全配置"""
    # 允许访问的路径白名单
    allowed_paths: list[str] = field(default_factory=lambda: [
        "./workspace",
        "./storage/uploads",
        "/var/log/*.log",
        "/tmp/*.txt",
        "/tmp/pytest-of-*/*"  # pytest临时目录
    ])

    # 禁止访问的路径模式
    forbidden_patterns: list[str] = field(default_factory=lambda: [
        "*/.ssh/*",
        "*/.env",
        "*/.git/config",
        "/etc/passwd",
        "/etc/shadow",
        "/etc/*secret*"
    ])

    # RAG 索引配置
    auto_index: bool = True
    max_file_size: int = 10485760  # 10MB
    chunk_size: int = 500
    chunk_overlap: int = 50

    # 命令执行限制
    max_output_size: int = 102400  # 100KB
    max_files_per_glob: int = 100

    def validate(self) -> bool:
        """验证配置有效性"""
        return (
            self.max_file_size > 0 and
            self.max_output_size > 0 and
            self.chunk_size > 0 and
            0 <= self.chunk_overlap < self.chunk_size
        )


@dataclass
class AppConfig:
    """应用配置（从 config.yaml 和 .env 加载）"""
    server: ServerConfig
    llm: LLMConfig
    streaming: StreamingConfig
    file_access: FileAccessConfig

    # 配置文件路径
    config_file: str = "config.yaml"  # 项目根目录
    env_file: str = ".env"            # 项目根目录

    @classmethod
    def load(cls, config_file: str = "config.yaml", env_file: str = ".env") -> 'AppConfig':
        """从 config.yaml 和 .env 加载配置

        加载优先级：命令行参数 > 环境变量 > config.yaml
        """
        # 1. 加载 .env 文件
        from dotenv import load_dotenv
        if os.path.exists(env_file):
            load_dotenv(env_file)

        # 2. 读取 config.yaml
        import yaml
        if not os.path.exists(config_file):
            raise FileNotFoundError(
                f"配置文件不存在：{config_file}\n"
                f"请在项目根目录创建 {config_file} 文件。"
            )

        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # 3. 解析配置
        server_config = ServerConfig(**config_data.get('server', {}))

        # 4. LLM 配置：API key 从环境变量读取
        llm_config_data = config_data.get('llm', {})
        api_key = os.getenv('ZHIPU_API_KEY')
        if not api_key:
            raise ValueError(
                "ZHIPU_API_KEY 环境变量未配置。\n"
                f"请在 {env_file} 文件中设置：ZHIPU_API_KEY=your-api-key"
            )

        llm_config = LLMConfig(
            provider="zhipu",
            api_key=api_key,
            **llm_config_data
        )

        # 5. 流式输出配置
        streaming_config = StreamingConfig(**config_data.get('streaming', {}))

        # 6. 文件访问安全配置
        file_access_data = config_data.get('file_access', {})
        file_access_config = FileAccessConfig(**file_access_data)

        return cls(
            server=server_config,
            llm=llm_config,
            streaming=streaming_config,
            file_access=file_access_config,
            config_file=config_file,
            env_file=env_file
        )

    def validate(self) -> bool:
        """验证配置有效性"""
        return (
            1024 <= self.server.port <= 65535 and
            self.server.max_clients > 0 and
            self.llm.validate() and
            self.streaming.validate() and
            self.file_access.validate()
        )


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config(config_file: str = "config.yaml", env_file: str = ".env") -> AppConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = AppConfig.load(config_file, env_file)
    return _config


def validate_api_key() -> bool:
    """验证智谱 API key 是否已配置（遵循章程：测试真实性）"""
    api_key = os.getenv('ZHIPU_API_KEY', '')
    return bool(api_key)
