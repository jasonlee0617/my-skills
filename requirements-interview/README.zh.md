# Requirements Interview 中文说明

Requirements Interview 是一个逐轮澄清需求的 Codex Skill。它在输出完整方案前，每轮只提出一个会实质影响方案的问题，并根据用户最新回答继续追问，直到需求达到可决策状态。

## 适用场景

- 用户明确要求“一次只问一个问题”。
- 目标、范围或约束尚不完整，直接设计可能产生较大返工。
- 需要在方案输出前完成需求访谈或技术选型澄清。
- 多个合理实现方向依赖用户偏好，无法仅从工作区判断。

不适合用于事实已经完整、修改范围明确或用户要求立即实施的简单任务。

## 工作流程

1. 先检查文件、日志、配置和运行环境。
2. 找出当前对方案影响最大的一个未知项。
3. 每轮只提出一个实质问题。
4. 根据最新回答选择下一问题，不重复已确认内容。
5. 当剩余不确定性不会改变方案时停止访谈。
6. 陈述残余假设并输出一份决策完整的方案。

## 需求就绪检查

“95% 把握”不是数学概率，而是以下内容已经明确或被标记为不适用：

- 目标和成功结果。
- 当前状态及相关背景。
- 工作范围与明确排除项。
- 用户、操作者和下游使用方。
- 功能、安全及兼容性约束。
- 接口、依赖和关键权衡。
- 失败处理、回滚和验收标准。

## 安装

源码：

```text
/home/robot/my-skills/requirements-interview
```

用户级安装：

```bash
ln -sfnT \
  /home/robot/my-skills/requirements-interview \
  ~/.codex/skills/requirements-interview
```

验证：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /home/robot/my-skills/requirements-interview
test -f ~/.codex/skills/requirements-interview/SKILL.md && echo SKILL_OK
```

## 使用示例

```text
$requirements-interview
我想重新设计 ROS 2 机械臂抓取流程。请在给出最终方案前逐轮澄清需求，每轮只问一个问题。
```

## 行为边界

- 可以从工作区直接查明的事实不得反问用户。
- 不使用无关问题机械凑足访谈轮数。
- 用户明确要求立即实施时，除非存在阻塞性或安全关键未知项，否则应基于已声明假设继续。
- system、developer、安全规则和当前用户指令始终高于本 Skill。
