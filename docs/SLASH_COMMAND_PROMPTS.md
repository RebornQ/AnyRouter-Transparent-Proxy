# Slash Command 设计

## 1. 设计规范文档: spec-start

请用 WebFetch 阅读文档 `https://code.claude.com/docs/zh-CN/slash-commands`，根据文档帮我设计一个 SlashCommand，放到 ~/.claude/commands/spec-workflow 目录下，其内容大致如下：

```markdown
使用 Spec 开发 “XXX” 功能，要求如下：
- xxx
- xxx
- xxx
- xxx

额外要求如下：
1. 必须先使用 mcp__spec-workflow 工具，spec-workflow-guide 启动 Spec 开发流程，spec-status 读取最新状态
2. 及时更新 Spec 的 Task 文档的任务状态，任务开始更新为进行中，结束时更新为已完成
3. Task 文档里面的每一个开发任务都要求遵循全局指令的 Workflow，且无论 Phase 2 的多模型协作是否可以跳过，Phase 5 的审计都必须执行
4. 生成的文档要求用中文输出
5. 生成完文档后结束任务，后续再手动执行 Implement 流程
```

示例：
```markdown
使用 Spec 开发 “配置管理改版” 功能，要求如下：
- 允许编辑配置
- 保存配置后提示确认重启后端服务
- 配置保存在 .env
- 配置管理页面默认为只读，需要用户输入 DASHBOARD_API_KEY 认证成功后解锁编辑，若没配置 DASHBOARD_API_KEY，则只能只读模式不允许编辑。后端调用 API 保存配置时要校验 DASHBOARD_API_KEY 通过才允许保存

额外要求如下：
1. 必须先使用 mcp__spec-workflow 工具，spec-workflow-guide 启动 Spec 开发流程，spec-status 读取最新状态
2. 及时更新 Spec 的 Task 文档的任务状态，任务开始更新为进行中，结束时更新为已完成
3. Task 文档里面的每一个开发任务都要求遵循全局指令的 Workflow，且无论 Phase 2 的多模型协作是否可以跳过，Phase 5 的审计都必须执行
4. 生成的文档要求用中文输出
5. 生成完文档后结束任务，后续再手动执行 Implement 流程
```

### 调用示例

```
/sw:spec-start 配置管理改版

- 允许编辑配置
- 保存配置后提示确认重启后端服务
- 配置保存在 .env
- 配置管理页面默认为只读，需要用户输入 DASHBOARD_API_KEY 认证成功后解锁编辑，若没配置 DASHBOARD_API_KEY，则只能只读模式不允许编辑。后端调用 API 保存配置时要校验 DASHBOARD_API_KEY 通过才允许保存
```

## 2. 实现 Task: spec-continue

请用 WebFetch 阅读文档 `https://code.claude.com/docs/zh-CN/slash-commands`，根据文档帮我设计一个 SlashCommand，放到 ~/.claude/commands/spec-workflow 目录下，其内容大致如下：

```markdown
继续实施 spec 任务，按照 tasks.md 中的顺序执行，只完成一个任务即可。请先调用 Spec 的 mcp 工具查看状态（不要通过遍历文件的方式）

额外要求如下：
1. 必须先使用 mcp__spec-workflow 工具，spec-workflow-guide 启动 Spec 开发流程，spec-status 读取最新状态，当前 specName 为 "xxxx"
2. 及时更新 Spec 工具的 Task 的任务状态，任务开始更新为进行中，结束时更新为已完成。每个任务完成之后都要调用 spec mcp 工具 log-implementation 记录实现细节的日志
3. 每完成一个任务后进行总结，然后暂停询问我是否继续下一个任务
4. Task 文档里面的每一个开发任务都要求遵循全局指令的 Workflow，且无论 Phase 2 的多模型协作是否可以跳过，Phase 5 的审计都必须执行
```

其中 specName 要作为参数传入

### 调用示例

```
/sw:spec-continue config-management-revamp
```

# 一些 Slash Command 调用示例

## /zcf:init-project

```shell
/zcf:init-project AnyRouter 透明代理 - AI 上下文索引 要求尽量精简，只写必要事项
```

## /review

```shell
/review 请帮我 review 一下 git 4c9b8531c193aac1781ddab67df73de4ea074621 的代码
```