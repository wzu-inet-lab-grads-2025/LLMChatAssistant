# 中文输入法宽字符处理说明

**问题**: CLI客户端删除中文时显示残留
**根本原因**: Python底层输入处理对中文字符宽度计算不准确
**解决方案**: 使用 prompt_toolkit 正确处理宽字符
**状态**: ✅ 已修复（系统默认启用）

---

## 🐛 问题描述

### 症状

在CLI客户端中使用中文输入法时：
1. **输入中文**: 正常显示
2. **删除中文**: 实际内容删除，但显示有残留
3. **继续输入**: 新文字位置错乱

### 示例

```
输入: 你好abc
切换到英文输入法
删除: "abc"      (按3次退格)
预期显示: "你好"
实际显示: "你好" + "ab" (残留)
```

---

## 🔍 根本原因

### Python 底层输入处理的局限性

**核心问题**: Python 的底层输入处理（Windows 的 msvcrt，Linux/macOS 的 readline）对中文字符宽度计算不准确。

#### 技术细节

1. **字符宽度差异**:
   - ASCII字符: 宽度1 (如 'a', '1', '+')
   - 中文字符: 宽度2 (如 '你', '好', '测')
   - 全角字符: 宽度2 (如 'Ａ', 'Ｂ', '＋')

2. **Python input() 的问题**:
   ```python
   # Python 内置 input() 使用系统底层输入处理
   user_input = input("请输入: ")
   # 问题: 底层无法正确计算中文字符宽度
   # 结果: 删除时出现显示残留
   ```

3. **为什么出现残留**:
   - 输入 "你好abc" (2+1+1+1 = 5个字符，但显示宽度是 2*2+3 = 7)
   - 底层认为 "abc" 的删除位置在索引 5
   - 实际显示宽度应该是 7，导致光标位置错误
   - 删除后，实际内容已删除，但终端显示未正确更新

---

## ✅ 解决方案

### 使用 prompt_toolkit（系统默认方案）

**原理**: prompt_toolkit 不依赖系统的底层输入行，而是完全重写了基于文本界面的行编辑器，能完美处理中文宽字符、Backspace 删除、光标移动。

**优点**:
- ✅ 完美支持中文输入法
- ✅ 正确处理宽字符宽度
- ✅ 无残留，无错位
- ✅ 支持所有输入法
- ✅ 提供高级编辑功能（历史搜索、自动补全等）

**实现状态**:
- ✅ 系统已自动启用
- ✅ 无需任何配置
- ✅ 自动回退到 Rich input（如果 prompt_toolkit 不可用）

### 技术实现

**文件**: `clients/cli/ui.py`

**导入部分** (Line 28-38):
```python
# 尝试导入 prompt_toolkit 以支持更好的中文输入处理
# prompt_toolkit 能正确处理中文宽字符，解决删除残留问题
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.patch_stdout import patch_stdout

    HAS_PROMPT_TOOLKIT = True
except ImportError:
    # 如果没有安装，回退到Rich input
    HAS_PROMPT_TOOLKIT = False
```

**初始化** (Line 182-187):
```python
# 初始化 prompt_toolkit PromptSession（如果可用）
# prompt_toolkit 能正确处理中文宽字符，解决删除残留问题
if HAS_PROMPT_TOOLKIT:
    self.session = PromptSession()
else:
    self.session = None
```

**输入处理** (Line 725-743):
```python
# 如果 prompt_toolkit 可用，使用它来处理输入
# prompt_toolkit 能正确处理中文宽字符，解决删除残留问题
if HAS_PROMPT_TOOLKIT and self.session is not None:
    # 使用 Rich 的 console.capture() 将带 Rich 标签的 prompt 转换为 ANSI 代码
    with self.console.capture() as capture:
        self.console.print(prompt, end="")

    ansi_prompt = capture.get()

    # 使用 prompt_toolkit 的 PromptSession 来获取输入
    # patch_stdout() 确保 Rich 的输出（如流式响应）不会干扰 prompt_toolkit 的输入编辑器
    try:
        with patch_stdout():
            user_input = self.session.prompt(ANSI(ansi_prompt))
        return user_input.strip()
    except EOFError:
        return ""
    except KeyboardInterrupt:
        return ""
```

---

## 🧪 验证方法

### 安装依赖

```bash
# 使用 uv 安装依赖（推荐）
uv sync

# 或使用 pip
pip install prompt-toolkit
```

### 测试步骤

#### 测试1: 基本中文输入删除

```bash
# 启动客户端
python3 -m clients.cli.main

# 测试操作:
User> 你好abc        (中文输入法输入 "你好"，切换英文输入 "abc")
User> 你好            (按3次退格删除 "abc")
# 预期: 无残留，正常显示 "你好"
```

#### 测试2: 混合输入

```bash
User> test测试123     (中英文混合)
User> test测试        (按3次退格删除 "123")
User> test            (按2次退格删除 "测试")
User>                 (按4次退格删除 "test")
# 预期: 每次删除都完全清除，无残留
```

#### 测试3: 输入法频繁切换

```bash
User> hello           (英文输入法)
User> hello你好       (切换中文输入法)
User> hello你好world  (切换回英文输入法)
User> hello你好       (按5次退格删除 "world")
# 预期: 删除位置正确，无残留
```

---

## 📊 方案对比

| 方案 | 中文支持 | 残留问题 | 高级功能 | 推荐度 |
|------|---------|---------|---------|--------|
| prompt_toolkit (系统默认) | ⭐⭐⭐⭐⭐ | ✅ 无 | ✅ 完整 | ⭐⭐⭐⭐⭐ |
| Rich input (回退方案) | ⭐⭐⭐ | ❌ 有 | ⚠️ 基础 | ⭐⭐⭐ |

---

## 🔧 依赖管理

### pyproject.toml 配置

```toml
dependencies = [
    "zai-sdk>=0.1.0",
    "rich>=13.0.0",
    "numpy>=1.24.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
    "sniffio>=1.3.0",
    "faiss-cpu>=1.7.0",
    "aiohttp>=3.9.0",
    "prompt-toolkit>=3.0.0",  # 修复中文输入法宽字符问题
]
```

### 版本要求

- **最低版本**: prompt-toolkit >= 3.0.0
- **推荐版本**: prompt-toolkit >= 3.0.36 (最新稳定版)

---

## 💡 常见问题

### Q1: 如何确认 prompt_toolkit 已启用？

**A**: 启动客户端时查看日志，或运行以下测试:

```python
python3 -c "from prompt_toolkit import PromptSession; print('✅ prompt_toolkit 已安装')"
```

### Q2: 如果不想使用 prompt_toolkit 怎么办？

**A**: 不推荐，但如果必须禁用:

```bash
# 方案1: 卸载 prompt_toolkit
pip uninstall prompt-toolkit

# 方案2: 修改代码设置 HAS_PROMPT_TOOLKIT = False
```

**注意**: 禁用后中文输入可能出现残留问题。

### Q3: prompt_toolkit 与 Rich 的兼容性？

**A**:
- ✅ 完全兼容
- ✅ 使用 `patch_stdout()` 防止输出干扰
- ✅ 使用 ANSI 转换处理 Rich 格式

---

## 🎯 效果验证

### 修复前 (使用 Python 内置 input())

```
输入: 你好abc
删除: abc (按3次退格)
预期: 你好
实际: 你好ab (残留!)
```

### 修复后 (使用 prompt_toolkit)

```
输入: 你好abc
删除: abc (按3次退格)
预期: 你好
实际: 你好 ✅ (完全正常)
```

---

## 📝 技术参考

### prompt_toolkit 的优势

1. **完全重写行编辑器**:
   - 不依赖系统底层输入处理
   - 自己实现字符宽度计算
   - 正确处理所有Unicode字符

2. **跨平台一致性**:
   - Windows, Linux, macOS 行为一致
   - 不受终端类型影响
   - 不受输入法影响

3. **丰富的功能**:
   - 历史记录搜索 (Ctrl+R)
   - 自动补全
   - 多行编辑
   - Vi/Emacs 模式
   - 语法高亮

### patch_stdout() 的作用

```python
# 防止 Rich 输出干扰 prompt_toolkit 输入
with patch_stdout():
    user_input = self.session.prompt(prompt)

# 原理:
# - patch_stdout() 拦截 stdout 输出
# - 将输出重定向到 prompt_toolkit 的输出区域
# - 避免输出破坏输入行的显示
```

---

## ✅ 结论

### 问题状态: **已解决** ✅

**解决方案**: 使用 prompt_toolkit 正确处理中文宽字符

**推荐用法**:
```bash
# 确保安装依赖
uv sync

# 直接启动（自动使用 prompt_toolkit）
python3 -m clients.cli.main
```

**效果**:
- ✅ 完美支持中文输入法
- ✅ 无残留问题
- ✅ 全半角切换正常
- ✅ 删除操作准确
- ✅ 提供高级编辑功能

**系统状态**: 默认启用，无需配置

---

**文档版本**: 3.0.0 (正确技术方案)
**维护者**: Claude Code (CLI客户端重构自动化工具)
**最后更新**: 2026-01-01 23:00

**参考文献**:
- [prompt_toolkit 官方文档](https://python-prompt-toolkit.readthedocs.io/)
- [Unicode 宽字符标准](https://www.unicode.org/reports/tr11/)
