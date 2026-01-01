"""
环境验证测试脚本
验证开发环境是否符合项目章程要求

Constitution 合规检查:
- Python 3.11 (开发环境标准)
- uv 管理 (虚拟环境)
- ZHIPU_API_KEY 配置 (测试真实性)
- logs 文件夹可写入 (文档与可追溯性)
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv


def check_python_version():
    """检查 Python 版本"""
    print("\n" + "="*60)
    print("检查 1: Python 版本")
    print("="*60)

    version = sys.version_info
    print(f"当前版本: Python {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 11:
        print("✅ PASS: Python 3.11+")
        return True
    else:
        print(f"❌ FAIL: 需要 Python 3.11+, 当前为 {version.major}.{version.minor}")
        return False


def check_uv_environment():
    """检查 uv 虚拟环境"""
    print("\n" + "="*60)
    print("检查 2: uv 虚拟环境")
    print("="*60)

    # 检查是否在虚拟环境中
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print(f"虚拟环境路径: {sys.prefix}")
        print("✅ PASS: 虚拟环境已激活")
        return True
    else:
        print("❌ FAIL: 虚拟环境未激活")
        print("提示: 请运行 'source .venv/bin/activate' 激活虚拟环境")
        return False


def check_zhipu_api_key():
    """检查智谱 API Key"""
    print("\n" + "="*60)
    print("检查 3: 智谱 API Key (ZHIPU_API_KEY)")
    print("="*60)

    # 加载 .env
    load_dotenv()

    api_key = os.getenv('ZHIPU_API_KEY')

    if not api_key:
        print("❌ FAIL: ZHIPU_API_KEY 未配置")
        print("提示: 请在 .env 文件中添加 ZHIPU_API_KEY")
        return False

    # 验证格式
    if len(api_key) < 20:
        print(f"❌ FAIL: API Key 格式无效（长度: {len(api_key)}）")
        return False

    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"长度: {len(api_key)} 字符")
    print("✅ PASS: ZHIPU_API_KEY 已配置")

    # 可选: 测试 SDK 导入
    try:
        from zhipuai import ZhipuAI
        print("✅ PASS: zhipuai SDK 已安装")
    except ImportError:
        print("⚠️  WARNING: zhipuai SDK 未安装（可稍后安装）")

    return True


def check_logs_directory():
    """检查 logs 文件夹"""
    print("\n" + "="*60)
    print("检查 4: logs 文件夹可写入性")
    print("="*60)

    logs_dir = Path("logs")

    if not logs_dir.exists():
        print("logs/ 文件夹不存在，正在创建...")
        logs_dir.mkdir(parents=True, exist_ok=True)

    # 测试写入权限
    test_file = logs_dir / "_write_test.tmp"
    try:
        test_file.write_text("test")
        test_file.unlink()
        print(f"logs/ 路径: {logs_dir.absolute()}")
        print("✅ PASS: logs/ 文件夹可写入")
        return True
    except Exception as e:
        print(f"❌ FAIL: 无法写入 logs/ 文件夹: {e}")
        return False


def check_project_structure():
    """检查项目结构"""
    print("\n" + "="*60)
    print("检查 5: 项目结构")
    print("="*60)

    required_dirs = [
        "src",
        "tests",
        "specs",
        ".specify",
    ]

    all_exist = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        exists = dir_path.exists() and dir_path.is_dir()
        status = "✅" if exists else "❌"
        print(f"{status} {dir_name}/")
        if not exists:
            all_exist = False

    if all_exist:
        print("\n✅ PASS: 项目结构完整")
    else:
        print("\n❌ FAIL: 部分目录缺失")

    return all_exist


def check_test_infrastructure():
    """检查测试基础设施"""
    print("\n" + "="*60)
    print("检查 6: 测试基础设施")
    print("="*60)

    checks = []

    # pytest.ini
    if Path("pytest.ini").exists():
        print("✅ pytest.ini 已配置")
        checks.append(True)
    else:
        print("❌ pytest.ini 缺失")
        checks.append(False)

    # tests/fixtures/data
    if Path("tests/fixtures/data").exists():
        print("✅ 测试数据已生成")
        checks.append(True)
    else:
        print("⚠️  测试数据未生成（可稍后生成）")
        checks.append(True)  # 不强制要求

    # reports/
    if Path("reports").exists():
        print("✅ reports/ 目录已创建")
        checks.append(True)
    else:
        print("❌ reports/ 目录缺失")
        checks.append(False)

    # issues/
    if Path("issues").exists():
        print("✅ issues/ 目录已创建")
        checks.append(True)
    else:
        print("❌ issues/ 目录缺失")
        checks.append(False)

    if all(checks):
        print("\n✅ PASS: 测试基础设施完整")
    else:
        print("\n⚠️  WARNING: 部分测试基础设施缺失")

    return all(checks)


def main():
    """运行所有环境验证测试"""
    print("\n" + "="*60)
    print("环境验证测试")
    print("CLI 客户端重构功能 - 设置阶段")
    print("="*60)

    results = []

    # 执行所有检查
    results.append(("Python 版本", check_python_version()))
    results.append(("uv 虚拟环境", check_uv_environment()))
    results.append(("智谱 API Key", check_zhipu_api_key()))
    results.append(("logs 文件夹", check_logs_directory()))
    results.append(("项目结构", check_project_structure()))
    results.append(("测试基础设施", check_test_infrastructure()))

    # 生成报告
    print("\n" + "="*60)
    print("验证报告")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 所有检查通过！环境配置正确。")
        print("可以继续下一阶段：基础设施（T011-T021）")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项检查失败，请修复后重试。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
