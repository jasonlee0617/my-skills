# Cleanup — 清理 AI 开发过程中产生的临时文件

自动清理 pytest 缓存、Python 字节码缓存、CMake 临时文件等可重新生成的工作区产物。

## 使用方式

在 Claude Code 中执行：

```
/cleanup
```

AI 会先扫描列出所有可清理的产物，确认后执行删除。

## 安全边界

- 只删除 `.gitignore` 中已声明且可重新生成的文件
- 绝不删除 `build/`、`install/`、`log/` 目录（需用户明确确认）
- 绝不删除 git 跟踪的文件、配置文件、权重文件、数据集
- `.pytest_cache` 和 `__pycache__` 始终安全删除，下次运行测试/代码时自动重新生成
