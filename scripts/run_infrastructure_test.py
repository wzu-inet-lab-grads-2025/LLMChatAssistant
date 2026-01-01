#!/usr/bin/env python3
"""
基础设施测试脚本 (T020)
Constitution: 100% 真实测试，禁止mock
"""

import subprocess
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_pytest_with_markers(marker: str, description: str):
    """运行特定标记的pytest测试"""
    print(f"\n{'='*60}")
    print(f"运行: {description}")
    print(f"{'='*60}")

    cmd = [
        sys.executable, "-m", "pytest",
        f"src/client/tests/",
        "-v",
        "-m", marker,
        "--tb=short",
        "-x"  # 遇到第一个失败就停止
    ]

    print(f"命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"✓ {description} - 通过")
        return True
    else:
        print(f"✗ {description} - 失败 (退出码: {result.returncode})")
        return False


def main():
    """运行所有基础设施测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "基础设施测试 (T020)" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")

    results = {}

    # 测试1: 测试文件收集（确保pytest能找到所有测试）
    print("\n" + "="*60)
    print("测试1: 测试文件收集")
    print("="*60)

    cmd = [sys.executable, "-m", "pytest", "src/client/tests/", "--collect-only", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        test_count = result.stdout.count("test_")
        print(f"✓ 收集到 {test_count} 个测试")
        results["测试收集"] = True
    else:
        print("✗ 测试收集失败")
        print(result.stdout)
        print(result.stderr)
        results["测试收集"] = False

    # 测试2: 导入测试（确保所有模块可以正常导入）
    print("\n" + "="*60)
    print("测试2: 模块导入验证")
    print("="*60)

    modules_to_test = [
        ("src.client.tests.base", "BaseCLITest"),
        ("src.client.tests.fixtures.server", "NPLTServer"),
        ("src.client.tests.fixtures.client", "NPLTClient"),
        ("src.client.tests.fixtures.test_data", "DataFileGenerator"),
        ("src.client.tests.helpers.assertions", "AssertionHelper"),
        ("src.client.tests.helpers.validators", "ValidationHelper"),
        ("src.client.tests.utils.test_utils", "TestUtils"),
    ]

    all_imports_ok = True
    for module_name, class_name in modules_to_test:
        try:
            exec(f"from {module_name} import {class_name}")
            print(f"  ✓ {module_name}.{class_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}.{class_name} - {e}")
            all_imports_ok = False

    results["模块导入"] = all_imports_ok

    # 测试3: pytest.ini配置验证
    print("\n" + "="*60)
    print("测试3: pytest.ini配置验证")
    print("="*60)

    pytest_ini = Path("pytest.ini")
    if pytest_ini.exists():
        content = pytest_ini.read_text()
        checks = {
            "testpaths": "testpaths" in content,
            "log_file": "log_file" in content,
            "markers": "markers" in content,
        }

        for check_name, check_result in checks.items():
            status = "✓" if check_result else "✗"
            print(f"  {status} {check_name}")

        results["pytest配置"] = all(checks.values())
    else:
        print("  ✗ pytest.ini 不存在")
        results["pytest配置"] = False

    # 汇总结果
    print("\n" + "="*60)
    print("基础设施测试结果汇总")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n✓ 所有基础设施测试通过！")
        print("  - 测试框架配置正确")
        print("  - 所有模块可以正常导入")
        print("  - 测试文件可以正常收集")
        return 0
    else:
        print(f"\n✗ {total - passed} 项测试失败，请修复后再继续。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
