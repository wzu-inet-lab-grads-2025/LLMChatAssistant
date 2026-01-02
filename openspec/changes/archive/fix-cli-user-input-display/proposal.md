# 变更：修复 CLI 用户输入显示问题

## 为什么
当前 CLI 客户端在用户输入后，会同时显示原始的 "User> 输入内容" 和格式化的 Panel，造成重复显示。用户期望的是直接显示格式化的 Panel 框，不需要显示 "User>" 提示符行。

## 变更内容
- 修改 `ClientUI.input()` 方法，添加选项在返回前清除输入行
- 修改 `ClientMain` 主循环，使用新的清除选项
- 确保用户输入后直接显示格式化的 Panel 框（╭─ USER ─╮）

## 影响
- 受影响规范：`cli-ui`（CLI 用户界面）
- 受影响代码：
  - `clients/cli/ui.py` - ClientUI 类
  - `clients/cli/main.py` - ClientMain 主循环
