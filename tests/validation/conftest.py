"""
Pytest配置和Fixtures

配置验证测试所需的pytest fixtures和命令行参数。
"""

import pytest
import os
import logging
from pathlib import Path

def pytest_addoption(parser):
    """添加pytest命令行选项"""
    parser.addoption(
        "--auto-confirm",
        action="store_true",
        default=False,
        help="自动确认测试通过，不等待用户输入（适用于CI/CD）"
    )

# 配置测试日志
def pytest_configure(config):
    """Pytest配置钩子"""
    # 验证环境变量
    if not os.getenv("ZHIPU_API_KEY"):
        raise pytest.UsageError(
            "ZHIPU_API_KEY 环境变量未设置。\n"
            "请设置有效的智谱API Key：\n"
            "  export ZHIPU_API_KEY='your-api-key-here'\n"
            "或在.env文件中配置"
        )

    # 配置日志
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "test_validation.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

@pytest.fixture
def auto_confirm(request):
    """返回auto-confirm命令行参数值"""
    return request.config.getoption("--auto_confirm")

@pytest.fixture
async def fresh_agent():
    """为每个测试创建新的Agent实例"""
    from src.server.agent import ReActAgent
    from src.llm.zhipu import ZhipuProvider

    # 创建LLM Provider
    llm_provider = ZhipuProvider()

    # 创建Agent实例
    agent = ReActAgent(llm_provider=llm_provider)

    yield agent

    # 清理：Agent没有需要显式清理的资源

@pytest.fixture
def fresh_history():
    """为每个测试创建新的对话历史"""
    from src.storage.history import ConversationHistory
    from uuid import uuid4

    # 创建新的对话历史，使用唯一的session_id
    session_id = f"test-{uuid4()}"
    history = ConversationHistory.create_new(session_id)

    yield history

    # 清理：对话历史会持久化到storage/history/目录
    # 在测试后清理该session的文件
    history_file = Path(f"storage/history/{session_id}.json")
    if history_file.exists():
        history_file.unlink()

@pytest.fixture(autouse=True)
async def clean_test_environment():
    """每个测试前后的环境清理（自动使用）"""
    # 测试前：清理临时文件
    test_storage = Path("storage/test-*")
    for test_file in Path("storage").glob("test-*"):
        if test_file.is_file():
            test_file.unlink()

    yield

    # 测试后：清理测试数据
    # 清理测试可能创建的向量索引
    test_vectors = Path("storage/vectors/test-*")
    for vector_file in Path("storage/vectors").glob("test-*"):
        if vector_file.is_file():
            vector_file.unlink()
