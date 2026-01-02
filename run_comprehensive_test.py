#!/usr/bin/env python3
"""
综合测试运行脚本 - Constitution v1.5.1 合规性验证

运行方法：
    python run_comprehensive_test.py
"""

import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# 设置环境变量
import os
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

if not os.getenv("ZHIPU_API_KEY"):
    print("❌ ZHIPU_API_KEY未配置！")
    print("请在.env文件中设置: ZHIPU_API_KEY=your_api_key")
    sys.exit(1)

print(f"✓ API Key已配置: {os.getenv('ZHIPU_API_KEY')[:8]}...{os.getenv('ZHIPU_API_KEY')[-4:]}")

# 导入并运行测试
from tests.validation.comprehensive_test.test_comprehensive_tools import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
