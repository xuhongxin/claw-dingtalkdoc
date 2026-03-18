---
name: dingtalk-article-reader
description: Use when the user wants to read or retrieve an article from DingTalk Docs, especially when they provide a document name, keyword, or document ID/URL and expect the full content to be returned for further analysis.
---

# DingTalk Article Reader

从钉钉文档读取指定文章内容，返回给宿主 Agent 进行后续分析。

## 何时使用

用户提到这些意图时使用：

- 读取钉钉文档中的某篇文章
- 获取钉钉知识库里的指定文档
- 从钉钉文档拉取内容进行分析、总结、翻译
- 提供了文档名称、关键词、文档 ID 或文档链接

不要在这些场景使用：

- 用户要写入或修改钉钉文档
- 用户要管理审批、日程、会议室
- 用户要读取的是非钉钉文档的网页内容

## MCP StreamableHttp URL 的获取与识别

### 什么是 StreamableHttp URL

钉钉文档 MCP 网关 URL，格式为：

```
https://mcp-gw.dingtalk.com/server/<server_id>?key=<api_key>
```

该 URL 对应用户所在组织的钉钉文档空间，所有读取操作都通过它访问。

### 识别规则

在当前对话的历史消息中，按以下顺序查找可用的 StreamableHttp URL：

1. 用户消息中包含 `mcp-gw.dingtalk.com` 的字符串，视为有效 URL
2. 本地缓存文件 `skills/dingtalk-article-reader/.state.json` 中的 `endpoint` 字段

只要找到其中任意一个，就直接使用，**不要再次向用户索要**。

### 何时向用户索要

仅在以下两个条件**同时成立**时，才向用户发送配置提示：

1. 当前对话历史中没有包含 `mcp-gw.dingtalk.com` 的消息
2. 本地缓存文件不存在或其中没有 `endpoint` 字段

发送的固定提示文案：

```text
需要钉钉文档的 MCP 接入地址才能继续，请按以下步骤获取：

1. 登录：https://mcp.dingtalk.com/
2. 点击"钉钉文档"
3. 复制 StreamableHttp URL
4. 粘贴到当前对话
```

用户粘贴 URL 后，立即继续读取流程，**不要再次确认**。

### URL 缓存

每次成功使用某个 endpoint 完成读取后，运行以下命令将其写入本地缓存，方便下次对话复用：

```bash
python3 skills/dingtalk-article-reader/scripts/read_from_dingtalk_doc.py save-endpoint \
  --endpoint "<STREAMABLE_HTTP_URL>"
```

## 操作流程

### 情况 A：用户提供了文档 ID 或文档链接

直接运行：

```bash
python3 skills/dingtalk-article-reader/scripts/read_from_dingtalk_doc.py get \
  --endpoint "<STREAMABLE_HTTP_URL>" \
  --node-id "<DOC_ID_OR_URL>"
```

### 情况 B：用户提供了文档名称或关键词

先搜索：

```bash
python3 skills/dingtalk-article-reader/scripts/read_from_dingtalk_doc.py search \
  --endpoint "<STREAMABLE_HTTP_URL>" \
  --keyword "<KEYWORD>"
```

脚本返回匹配文档列表（JSON），包含 `nodeId`、`title`、`url`、`contentType`。

- 如果只有一条结果，直接用该 `nodeId` 执行情况 A 的 `get` 命令
- 如果有多条结果，向用户展示列表，请用户确认目标文档后再执行 `get`
- 如果结果为空，告知用户并建议换关键词或直接提供文档链接

### 情况 C：用户要浏览某个文件夹或知识库

```bash
python3 skills/dingtalk-article-reader/scripts/read_from_dingtalk_doc.py list \
  --endpoint "<STREAMABLE_HTTP_URL>" \
  [--folder-id "<FOLDER_ID>"] \
  [--workspace-id "<WORKSPACE_ID>"]
```

不传任何 ID 时，列出用户"我的文档"根目录。返回节点列表后，用户从中选择目标文档再执行 `get`。

## 输出格式

`get` 命令成功后，脚本输出 JSON：

```json
{
  "nodeId": "abc123",
  "title": "文档标题",
  "url": "https://alidocs.dingtalk.com/i/nodes/abc123",
  "content": "# 文档标题\n\n正文 Markdown 内容...",
  "fetched_at": "2024-01-01 12:00"
}
```

将 `content` 字段的内容直接交给宿主 Agent 进行后续分析（摘要、翻译、问答等）。

## 失败处理

- 搜索无结果：告知用户未找到匹配文档，建议换关键词或提供文档链接
- 无权限：说明当前账号对该文档没有下载权限，请用户确认文档共享设置
- 文档类型不支持：`get_document_content` 仅支持钉钉在线文档（alidoc），其他类型（PDF、docx 等）会返回错误，需告知用户
- MCP 调用失败：返回错误信息，建议用户检查 StreamableHttp URL 是否有效或重新从 mcp.dingtalk.com 获取
