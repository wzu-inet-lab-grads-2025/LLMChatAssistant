#!/usr/bin/env python3
"""
环境验证测试脚本 (T009)
Constitution: 真实测试，禁止mock
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_python_version():
    """检查Python版本"""
    print("=" * 60)
    print("检查Python版本...")
    print("=" * 60)

    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 11:
        print("✓ Python版本符合要求 (>=3.11)")
        return True
    elif version.major == 3 and version.minor == 10:
        print("⚠ 警告: Python版本是3.10，推荐使用3.11")
        print("  注意: 如果使用.venv虚拟环境，请确保虚拟环境使用3.11")
        # 检查.venv
        venv_python = project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            print(f"  检测到虚拟环境: {venv_python}")
        return True  # 允许3.10继续
    else:
        print("✗ Python版本不符合要求，需要3.11或更高")
        return False


def check_api_key():
    """检查智谱API Key"""
    print("\n" + "=" * 60)
    print("检查智谱API Key...")
    print("=" * 60)

    load_dotenv()
    api_key = os.getenv("ZHIPU_API_KEY")

    if api_key:
        print(f"✓ ZHIPU_API_KEY已配置")
        print(f"  Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"  长度: {len(api_key)} 字符")

        # 验证格式（智谱API key格式：id.secret）
        if '.' in api_key:
            parts = api_key.split('.')
            if len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0:
                print("  ✓ API Key格式正确")
                return True
            else:
                print("  ✗ API Key格式不正确")
                return False
        else:
            print("  ⚠ API Key格式可能不正确（缺少.分隔符）")
            return True  # 仍然允许继续
    else:
        print("✗ ZHIPU_API_KEY未配置")
        print("  请在.env文件中配置: ZHIPU_API_KEY=your_key_here")
        return False


def check_uv():
    """检查uv包管理器"""
    print("\n" + "=" * 60)
    print("检查uv包管理器...")
    print("=" * 60)

    import shutil
    uv_path = shutil.which("uv")

    if uv_path:
        print(f"✓ uv已安装: {uv_path}")
        try:
            result = os.popen("uv --version").read().strip()
            print(f"  版本: {result}")
            return True
        except:
            print("  ⚠ 无法获取uv版本")
            return True
    else:
        print("⚠ uv未找到")
        print("  注意: uv不是必需的，可以使用pip代替")
        return True  # uv不是必需的


def check_project_structure():
    """检查项目结构"""
    print("\n" + "=" * 60)
    print("检查项目结构...")
    print("=" * 60)

    required_dirs = [
        "src/client",
        "src/server",
        "src/protocols",
        "src/tools",
        "src/storage",
        "logs",
        "specs/001-cli-client-refactor/issues",
        "specs/001-cli-client-refactor/reports",
        "specs/001-cli-client-refactor/scripts",
    ]

    required_files = [
        "pytest.ini",
        ".env",
        "src/client/main.py",
        "src/client/tests/base.py",
        "src/client/tests/fixtures/test_data.py",
    ]

    all_ok = True

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} - 缺失")
            all_ok = False

    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - 缺失")
            all_ok = False

    return all_ok


def check_pytest():
    """检查pytest配置"""
    print("\n" + "=" * 60)
    print("检查pytest配置...")
    print("=" * 60)

    pytest_ini = project_root / "pytest.ini"
    if pytest_ini.exists():
        print("✓ pytest.ini存在")
        content = pytest_ini.read_text()
        if "testpaths" in content:
            print("  ✓ 测试路径已配置")
        if "log_file" in content:
            print("  ✓ 日志输出已配置")
        return True
    else:
        print("✗ pytest.ini不存在")
        return False


def check_logs_directory():
    """检查logs目录可写性"""
    print("\n" + "=" * 60)
    print("检查logs目录...")
    print("=" * 60)

    logs_dir = project_root / "logs"
    if logs_dir.exists():
        print(f"✓ logs目录存在: {logs_dir}")

        # 测试写入
        test_file = logs_dir / "test_write.tmp"
        try:
            test_file.write_text("test")
            test_file.unlink()
            print("  ✓ logs目录可写")
            return True
        except Exception as e:
            print(f"  ✗ logs目录不可写: {e}")
            return False
    else:
        print("✗ logs目录不存在")
        return False


def main():
    """运行所有验证检查"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "环境验证测试 (T009)" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")

    results = {
        "Python版本": check_python_version(),
        "API Key": check_api_key(),
        "uv": check_uv(),
        "项目结构": check_project_structure(),
        "pytest配置": check_pytest(),
        "logs目录": check_logs_directory(),
    }

    # 汇总结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n✓ 所有环境验证通过！可以继续实施。")
        return 0
    else:
        print(f"\n⚠ {total - passed} 项验证失败，请修复后再继续。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
