#!/bin/bash
# CLI客户端启动脚本
#
# 使用方法:
#   ./start_client.sh
#
# 系统会自动使用 prompt_toolkit 来正确处理中文宽字符

echo "========================================"
echo "启动CLI客户端"
echo "========================================"
echo ""
echo "系统已启用 prompt_toolkit 以正确处理中文输入"
echo "如果遇到输入问题，请查看 docs/chinese_input_fix.md"
echo ""
echo "========================================"
echo ""

# 启动客户端
python3 -m clients.cli.main "$@"
