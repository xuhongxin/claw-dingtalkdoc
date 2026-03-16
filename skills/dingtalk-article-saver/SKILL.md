---
name: dingtalk-article-saver
description: Use when the user wants to save a web article into DingTalk Docs, especially when they provide an article URL and expect extraction, English-to-Chinese translation, AI-generated title, summary, tags, and document creation in a fixed DingTalk folder.
---

# DingTalk Article Saver

将网页文章提取后保存到钉钉文档。目标文件夹固定为 `OpenClawDingTalk`。如果文件夹不存在，自动创建。每篇文章单独生成一篇新文档。

## 何时使用

用户提到这些意图时使用：

- 保存文章到钉钉文档
- 把网页链接沉淀到 DingTalk Docs
- 收藏文章到钉钉知识库
- 输入一个 URL，提取正文并写入钉钉文档

不要在这些场景使用：

- 用户要编辑已有钉钉文档的某一段
- 用户要管理审批、日程、会议室
- 用户只要摘要，不需要保存到钉钉文档

## 运行前提

先设置环境变量 `DINGTALK_DOC_MCP_ENDPOINT`，值为可用的钉钉文档 MCP endpoint。

示例：

```bash
export DINGTALK_DOC_MCP_ENDPOINT='https://mcp-gw.dingtalk.com/server/...'
```

## 固定规则

- 文件夹名称固定为 `OpenClawDingTalk`
- 找不到就新建该文件夹
- 每篇文章一篇新文档，不要追加到旧文档
- 如果原文是英文，先翻译成中文，再保存
- 文档标题必须由 AI 生成；只有在无法可靠生成时，才回退到网页原标题
- 输出内容必须包含：
  - `文章分类标签`
  - `文章内容概述`
  - `文章正文`
  - `文章引用来源`

## 操作流程

### 1. 提取文章

运行：

```bash
python3 skills/dingtalk-article-saver/scripts/save_to_dingtalk_doc.py extract "<ARTICLE_URL>"
```

脚本会返回 JSON，包含：

- `title`
- `content`
- `url`
- `language`

### 2. 生成保存内容

基于提取结果执行以下规则：

- 如果 `language` 是 `en`，先把正文翻译成中文
- 用文章内容生成一个简洁的中文标题
- 生成 3-5 个中文标签
- 生成中文概述

### 3. 组装 Markdown

必须按这个结构组织：

```markdown
# {AI生成标题}

## 文章分类标签
- 标签1
- 标签2

## 文章内容概述
{中文概述}

## 文章正文
{中文正文}

## 文章引用来源
- 原始链接: {原文 URL}
- 抓取时间: {YYYY-MM-DD HH:MM}
- 原文语言: 中文/英文
```

### 4. 保存到钉钉文档

运行：

```bash
python3 skills/dingtalk-article-saver/scripts/save_to_dingtalk_doc.py save \
  --title "<AI_TITLE>" \
  --markdown "<MARKDOWN>"
```

脚本会：

- 读取本地缓存的 folder id
- 如果没有缓存，则查找 `OpenClawDingTalk`
- 如果仍不存在，则自动创建该文件夹
- 在该文件夹下创建一篇新文档

## 失败处理

- 提取失败：不要保存空文档，先向用户说明 URL 无法读取或正文提取失败
- 内容过短：说明文章内容不足，询问是否仍然保存
- MCP 写入失败：返回错误信息，并保留已生成的标题、摘要、正文和来源，便于重试
- 英文翻译不完整：不要混存半截英文正文，先完成中文翻译再保存
