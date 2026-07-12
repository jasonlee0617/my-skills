# Agent 上下文工程 Skills 中文说明

[English](./README.md) | 简体中文

这是一个面向生产级 AI Agent 的上下文工程 Skill 集合，覆盖上下文构成、退化诊断、压缩优化、记忆系统、工具设计、多智能体协作、评估与 Agent Harness 等主题。

## 什么是上下文工程

上下文工程关注进入模型注意力范围的全部信息，包括系统提示、工具定义、检索文档、消息历史、记忆和工具输出。其目标不是简单增加上下文，而是用尽可能少的高价值信息，提高模型完成任务的可靠性。

上下文过长或组织不当时，常见问题包括：

- 中间信息被忽略（lost in the middle）。
- 无关信息分散注意力。
- 旧信息污染当前判断。
- 指令、记忆和工具结果相互冲突。
- token 成本增加，但任务质量没有同步提升。

## Skill 分类

### 基础能力

| Skill | 用途 |
|---|---|
| `context-fundamentals` | 理解上下文窗口、注意力预算和上下文组成 |
| `context-degradation` | 识别上下文污染、干扰、冲突和中间信息丢失 |
| `context-compression` | 为长会话、轨迹和工具输出设计压缩策略 |

### 架构能力

| Skill | 用途 |
|---|---|
| `multi-agent-patterns` | 设计编排式、对等式和分层多智能体协作 |
| `memory-systems` | 设计短期记忆、长期记忆和图式记忆 |
| `tool-design` | 设计清晰、可恢复、便于 Agent 使用的工具接口 |
| `filesystem-context` | 使用文件系统保存、发现和共享上下文 |
| `hosted-agents` | 设计远程沙箱、后台 Agent 和多客户端运行环境 |

### 运行与评估

| Skill | 用途 |
|---|---|
| `context-optimization` | 使用缓存、分区、遮罩和预算分配优化上下文 |
| `latent-briefing` | 在运行时可控时通过潜在表示传递任务状态 |
| `evaluation` | 建立确定性检查、回归测试和质量门禁 |
| `advanced-evaluation` | 使用 LLM-as-a-Judge、成对比较和评分量表 |
| `harness-engineering` | 设计持久日志、回滚、指标锁定和审批边界 |

### 开发与认知建模

| Skill | 用途 |
|---|---|
| `project-development` | 从需求判断到部署规划完整设计 LLM 项目 |
| `bdi-mental-states` | 使用信念、愿望和意图建模 Agent 心智状态 |

## 本机使用方式

完整源码位于：

```text
/home/robot/my-skills/context-engineering-skills
```

按需安装单个 Skill，避免一次加载无关能力。例如安装上下文压缩：

```bash
ln -sfnT \
  /home/robot/my-skills/context-engineering-skills/skills/context-compression \
  ~/.codex/skills/context-compression
```

验证：

```bash
test -f ~/.codex/skills/context-compression/SKILL.md && echo SKILL_OK
readlink -f ~/.codex/skills/context-compression
```

## 选择建议

- 长会话需要保留关键状态：使用 `context-compression`。
- Agent 回答随上下文增长而变差：使用 `context-degradation`。
- 需要跨会话保存知识：使用 `memory-systems`。
- 工具参数难用、错误难恢复：使用 `tool-design`。
- 设计多个 Agent 的职责与交接：使用 `multi-agent-patterns`。
- 建立可复现的质量标准：使用 `evaluation` 或 `advanced-evaluation`。
- 构建长期自主运行系统：使用 `harness-engineering`。

## 设计原则

- 渐进加载：只在任务需要时加载对应 Skill。
- 高信号优先：保留会改变决策的信息，移除重复背景。
- 平台无关：核心方法不依赖特定模型或 Agent 产品。
- 可验证：上下文优化必须通过任务质量、成本和稳定性指标验证。

上游仓库包含更多示例、研究资料和完整安装说明；本文件提供本机学习与选型所需的中文索引。
