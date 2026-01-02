#!/usr/bin/env python3
"""快速测试脚本 - 验证中文输入和聊天功能"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients.cli import create_client

async def test_basic_chat():
    """测试基本聊天功能"""
    print("=" * 60)
    print("快速测试：中文输入和聊天功能")
    print("=" * 60)

    # 1. 测试prompt_toolkit是否可用
    print("\n[1/3] 检查 prompt_toolkit...")
    try:
        from prompt_toolkit import PromptSession
        print("✅ prompt_toolkit 已安装")
    except ImportError:
        print("❌ prompt_toolkit 未安装")
        return False

    # 2. 连接服务器
    print("\n[2/3] 连接服务器...")
    try:
        client = await create_client(host="127.0.0.1", port=9999, auto_connect=True)
        if not client.is_connected:
            print("❌ 连接服务器失败")
            return False
        print(f"✅ 已连接，Session ID: {client.session_id}")
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False

    # 3. 发送测试消息
    print("\n[3/3] 发送测试消息...")
    test_message = "你好"
    print(f"发送: {test_message}")

    try:
        response = await client.send_message(test_message)
        print(f"收到响应: {response[:100]}...")

        if response and len(response) > 0:
            print("\n✅ 聊天功能正常")
            return True
        else:
            print("\n❌ 收到空响应")
            return False
    except Exception as e:
        print(f"\n❌ 发送消息错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()

async def test_chinese_deletion():
    """测试中文输入删除（需要手动验证）"""
    print("\n" + "=" * 60)
    print("手动测试：中文输入删除")
    print("=" * 60)
    print("\n请手动测试以下步骤：")
    print("1. 输入: 你好abc")
    print("2. 按3次退格删除 'abc'")
    print("3. 检查是否有残留")
    print("\n启动客户端进行测试...")

    from clients.cli.ui import get_ui
    ui = get_ui()

    try:
        while True:
            user_input = ui.input("\nUser> ")
            if user_input in ['/exit', '/quit']:
                break
            print(f"你输入了: {user_input}")
    except KeyboardInterrupt:
        print("\n测试结束")

async def main():
    """主函数"""
    # 测试1: 基本聊天功能
    chat_ok = await test_basic_chat()

    if not chat_ok:
        print("\n❌ 基本聊天功能测试失败，请检查：")
        print("1. 服务器是否运行（python3 -m server.main）")
        print("2. API Key是否配置正确")
        print("3. 网络连接是否正常")
        return

    # 测试2: 中文输入删除（手动）
    print("\n" + "=" * 60)
    choice = input("\n是否测试中文输入删除？(y/n): ").lower()
    if choice == 'y':
        await test_chinese_deletion()

if __name__ == "__main__":
    asyncio.run(main())
