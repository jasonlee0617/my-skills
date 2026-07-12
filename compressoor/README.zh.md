# Compressoor 中文说明

[English](./README.md) | 简体中文

Compressoor 是面向 Codex 与 Claude Code 的精简运行策略。它强调先使用工具完成工作，抑制工具调用前后的重复说明，并将最终回复控制为简洁、专业、可核验的结果摘要。

## 主要能力

- 工具优先：能够通过工具推进任务时，直接进入工具循环。
- 降低对话开销：避免确认语、思考前言、重复计划和过程旁白。
- 上下文压缩：压缩交接记录、评审意见、约束摘要和长提示词。
- 会话级注入：通过启动与恢复钩子持续加载运行规则。
- 可量化评估：提供提示词压缩基准和 token 节省统计。

## 目录结构

```text
compressoor/
├── skills/compressoor/       # Codex Skill 与安装脚本
├── plugins/compressoor/      # Codex 插件
├── .claude-plugin/           # Claude Code 插件清单
├── benchmarks/               # 压缩效果基准
└── tests/                    # 自动化测试
```

## 本机用户级安装

本机源码位于：

```text
/home/robot/my-skills/compressoor
```

Codex 用户级 Skill 使用软链接安装：

```bash
ln -sfnT \
  /home/robot/my-skills/compressoor/skills/compressoor \
  ~/.codex/skills/compressoor
```

如需安装完整运行策略和会话钩子，在仓库根目录执行：

```bash
python3 skills/compressoor/scripts/install_codex_compressoor.py --force
```

该命令可能更新用户级 `AGENTS.md`、hooks 和插件链接。执行前应先检查现有全局配置，避免覆盖不相关规则。

## 使用场景

- 长时间、频繁调用工具的编码任务。
- 希望减少无效状态更新和 token 消耗的会话。
- 需要把长交接内容压缩为可复用摘要。
- 需要比较不同压缩策略效果的基准测试。

## 行为边界

- Compressoor 优化表达和上下文体积，不降低验证要求。
- 安全警告、阻塞条件、失败原因和关键风险不能为了简短而省略。
- 上级 system、developer、项目规则和用户指令始终优先。

## 验证

```bash
test -f ~/.codex/skills/compressoor/SKILL.md && echo SKILL_OK
readlink -f ~/.codex/skills/compressoor
```

修改 Skill 或钩子后，应重新运行安装脚本，并新开 Codex 会话验证规则是否生效。
