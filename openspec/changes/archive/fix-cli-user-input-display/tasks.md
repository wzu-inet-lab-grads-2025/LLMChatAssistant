# 实施任务

## 1. 修改 ClientUI.input() 方法
- [x] 1.1 添加 `clear_after_input` 参数（默认 False 以保持向后兼容）
- [x] 1.2 在 input 方法返回前，如果 `clear_after_input=True`，使用 ANSI 转义序列清除当前行
- [x] 1.3 更新方法文档字符串，说明新参数的用途

## 2. 修改 ClientMain 主循环
- [x] 2.1 更新 `ui.input()` 调用，传入 `clear_after_input=True`
- [x] 2.2 验证用户输入后不再显示 "User>" 提示符行
- [x] 2.3 确保 `print_message()` 显示的 Panel 正常显示

## 3. 测试验证
- [x] 3.1 启动 CLI 客户端，输入测试消息
- [x] 3.2 验证输入后直接显示格式化的 Panel 框
- [x] 3.3 验证没有重复的 "User>" 提示符行
- [x] 3.4 测试多行输入和特殊字符
