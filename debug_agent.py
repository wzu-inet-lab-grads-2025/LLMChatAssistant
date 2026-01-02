#!/usr/bin/env python3
"""调试Agent - 查看LLM返回的原始结果"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from llm.zhipu import ZhipuProvider
from storage.history import ConversationHistory
from server.agent import ReActAgent
from tools.command import CommandTool
from tools.monitor import MonitorTool
from tools.semantic_search import SemanticSearchTool
from storage.vector_store import VectorStore

async def debug_agent():
    """调试Agent的决策过程"""
    print("=" * 60)
    print("调试：Agent工具调用决策")
    print("=" * 60)

    # 初始化LLM
    print("\n[1/4] 初始化LLM Provider...")
    api_key = os.environ.get('ZHIPU_API_KEY')
    if not api_key:
        # 尝试从.env文件读取
        try:
            with open('.env') as f:
                for line in f:
                    if line.startswith('ZHIPU_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        break
        except:
            pass

    if not api_key:
        print("❌ 找不到ZHIPU_API_KEY")
        return False

    llm_provider = ZhipuProvider(api_key=api_key, model="glm-4-flash")
    print(f"✅ LLM Provider初始化成功")

    # 初始化向量存储
    print("\n[2/4] 初始化向量存储...")
    vector_store = VectorStore(storage_dir="./data/vectors")
    print("✅ 向量存储初始化成功")

    # 初始化Agent
    print("\n[3/4] 初始化Agent...")
    agent = ReActAgent(
        llm_provider=llm_provider,
        tools={
            "command_executor": CommandTool(),
            "sys_monitor": MonitorTool(),
            "semantic_search": SemanticSearchTool(llm_provider, vector_store)
        },
        max_tool_rounds=5,
        tool_timeout=5
    )
    print("✅ Agent初始化成功")

    # 测试决策
    print("\n[4/4] 测试决策过程...")
    test_message = "查看系统状态"
    print(f"用户消息: {test_message}")

    # 创建一个会话ID
    import time
    import uuid
    session_id = str(uuid.uuid4())
    conversation_history = ConversationHistory(
        session_id=session_id,
        messages=[],
        created_at=time.time(),
        updated_at=time.time()
    )

    # 调用_think_and_decide
    print("\n调用 _think_and_decide...")
    thought = await agent._think_and_decide(test_message, conversation_history)

    print(f"\nLLM返回结果:")
    print("-" * 60)
    print(thought)
    print("-" * 60)

    # 解析工具调用
    print("\n解析工具调用...")
    tool_use = agent._parse_tool_use(thought)

    if tool_use:
        print(f"✅ 检测到工具调用:")
        print(f"  工具名: {tool_use['name']}")
        print(f"  参数: {tool_use['args']}")
    else:
        print("❌ 未检测到工具调用")
        print("\n可能的原因:")
        print("1. LLM返回格式不符合预期")
        print("2. LLM没有理解需要使用工具")
        print("3. 系统提示词不够明确")

    return True

if __name__ == "__main__":
    asyncio.run(debug_agent())
