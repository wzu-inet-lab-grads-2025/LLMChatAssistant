"""
测试配置和共享fixtures

提供pytest配置、测试环境、测试数据准备等功能。
"""

import os
import sys
import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def project_root_path():
    """项目根目录"""
    return project_root


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return project_root / "tests" / "fixtures" / "data"


@pytest.fixture(scope="session")
def test_config(test_data_dir):
    """加载测试配置"""
    from shared.utils.config import AppConfig
    config_path = project_root / "config.yaml"
    return AppConfig.load(config_path)


@pytest.fixture(scope="function")
def temp_storage_dir(tmp_path):
    """临时存储目录"""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    # 创建子目录
    (storage_dir / "vectors").mkdir(exist_ok=True)
    (storage_dir / "uploads").mkdir(exist_ok=True)
    (storage_dir / "history").mkdir(exist_ok=True)

    return storage_dir


@pytest.fixture(scope="function")
def test_logger(tmp_path):
    """测试日志记录器"""
    import logging
    log_file = tmp_path / "test.log"

    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    yield logger

    logger.removeHandler(handler)


@pytest.fixture(scope="session")
def zhipu_api_key():
    """智谱API Key"""
    # 从环境变量或.env文件加载
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        pytest.skip("ZHIPU_API_KEY环境变量未设置")

    return api_key


# 测试数据准备fixtures
@pytest.fixture(scope="session")
def sample_config_files(test_data_dir):
    """准备示例配置文件"""
    config_dir = test_data_dir / "config_files"
    config_dir.mkdir(parents=True, exist_ok=True)

    # 创建示例配置文件
    configs = {
        "app.yaml": """
# 应用配置
app:
  name: "测试应用"
  version: "1.0.0"
  debug: true

server:
  host: "0.0.0.0"
  port: 9999
""",
        "database.yaml": """
# 数据库配置
database:
  host: "localhost"
  port: 5432
  name: "testdb"
  user: "testuser"
  password: "testpass"
""",
        "server.conf": """
# 服务器配置
server {
    listen 9999;
    server_name localhost;
}
"""
    }

    for filename, content in configs.items():
        (config_dir / filename).write_text(content.strip(), encoding='utf-8')

    return list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.conf"))


@pytest.fixture(scope="session")
def sample_log_files(test_data_dir):
    """准备示例日志文件"""
    log_dir = test_data_dir / "log_files"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 创建示例日志文件
    logs = {
        "application.log": """
2025-01-02 10:00:00 INFO  [main] Application starting
2025-01-02 10:00:01 INFO  [main] Database connected
2025-01-02 10:00:02 DEBUG [main] Loading configuration
2025-01-02 10:00:03 INFO  [main] Server started on port 9999
2025-01-02 10:05:00 INFO  [http-1] Request received: GET /api/status
2025-01-02 10:05:01 INFO  [http-1] Response sent: 200 OK
""",
        "error.log": """
2025-01-02 10:10:00 ERROR [main] Failed to connect to database: Connection refused
2025-01-02 10:10:01 ERROR [main] Retrying in 5 seconds...
2025-01-02 10:10:06 ERROR [main] Still unable to connect, giving up
2025-01-02 10:15:00 WARN  [main] Memory usage high: 85%
2025-01-02 10:20:00 ERROR [http-2] Internal server error: ValueError
""",
        "access.log": """
127.0.0.1 - - [02/Jan/2025:10:00:00 +0000] "GET /api/status HTTP/1.1" 200 123
127.0.0.1 - - [02/Jan/2025:10:00:01 +0000] "POST /api/login HTTP/1.1" 201 456
127.0.0.1 - - [02/Jan/2025:10:00:02 +0000] "GET /api/users HTTP/1.1" 200 789
10.0.0.1 - - [02/Jan/2025:10:00:03 +0000] "GET /api/config HTTP/1.1" 200 234
"""
    }

    for filename, content in logs.items():
        (log_dir / filename).write_text(content.strip(), encoding='utf-8')

    return list(log_dir.glob("*.log"))


@pytest.fixture(scope="session")
def sample_documents(test_data_dir):
    """准备示例文档"""
    doc_dir = test_data_dir / "documents"
    doc_dir.mkdir(parents=True, exist_ok=True)

    # 创建示例文档
    docs = {
        "README.md": """
# 项目名称

这是一个智能网络运维助手项目。

## 功能特性

- 实时AI对话
- 文件传输
- 系统监控

## 安装

```bash
pip install -r requirements.txt
python server/main.py
```

## 使用

启动服务器后,使用客户端连接即可。
""",
        "API.md": """
# API 文档

## 聊天接口

### POST /api/chat

发送消息给AI助手。

**请求:**
```json
{
  "message": "你好"
}
```

**响应:**
```json
{
  "reply": "你好!有什么可以帮助你的吗?"
}
```
""",
        "DESIGN.md": """
# 系统设计

## 架构

系统采用客户端-服务器架构:

- **服务器**: 提供AI对话和文件管理服务
- **客户端**: CLI工具,用于与服务器交互

## 协议

使用NPLT协议进行通信:
- Type(1B) + Seq(2B) + Len(2B) + Data(≤64KB)
"""
    }

    for filename, content in docs.items():
        (doc_dir / filename).write_text(content.strip(), encoding='utf-8')

    return list(doc_dir.glob("*.md"))


# pytest配置
def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
