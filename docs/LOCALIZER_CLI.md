# 本地化工具 CLI 与接口文档

本工具面向两类调用者：

- 人类维护者：用浏览器打开本地编辑器。
- Agent / 脚本：通过 `tools/localizer/cli.py` 或本地 Flask JSON API 读取、筛选和校验翻译。

CLI 默认只读，不提供保存命令。保存仍应通过浏览器编辑器或显式调用 `/api/save`，因为 PO 写入需要备份和人工确认。

## 1. 环境

```bash
cd tools/localizer
python -m pip install -r requirements.txt
```

默认语言目录是本仓库的 `language/zh_CN`。要读取游戏目录中的副本，设置：

```bash
set RYONA_LANG_DIR=D:\Games\RyonaRPG\language\zh_CN
```

CLI 不需要启动 Flask；它直接读取本地 SQLite 索引和 PO 文件。

## 2. CLI

入口：

```bash
python tools/localizer/cli.py <命令> [参数]
```

所有查询命令都支持 `--json`，Agent 应优先使用 JSON 输出。

### `status`

```bash
python tools/localizer/cli.py status
python tools/localizer/cli.py status --qa --json
```

`--qa` 会额外扫描全库 QA；首次扫描约 0.7 秒，之后在当前进程内缓存。

### `search`

```bash
python tools/localizer/cli.py search "门水晶"
python tools/localizer/cli.py search "门水晶" --mode cn --limit 10 --json
```

- `--mode both|jp|cn`：搜索中日文、仅原文、仅译文。
- 结果条目包含 `file`、`block`、`ctx`、`msgid`、`msgstr`、`snippet`。

### `browse`

```bash
python tools/localizer/cli.py browse maps
python tools/localizer/cli.py browse maps --group Map0002.po --limit 20 --json
python tools/localizer/cli.py browse actors --json
```

分类 id：

```text
maps      地图
actors    角色
items     物品
skills    技能
database  状态/术语
files     全部 PO 文件
```

省略 `--group` 时返回分组列表；指定 `--group` 时返回该分组的条目和原文/译文。

### `entry`

```bash
python tools/localizer/cli.py entry Map0002.po 0
python tools/localizer/cli.py entry Map0002.po 0 --json
```

返回原文、译文、上下文、行宽指标、分页数和当前校验问题。条目由 `file + block` 唯一标识；`block` 是 PO 文件内的序号，不是事件 ID。

### `check`

```bash
python tools/localizer/cli.py check Map0002.po 0
python tools/localizer/cli.py check Map0002.po 0 --json
```

有 `error` 时退出码为 `1`，只有 warning/info 时退出码为 `0`。适合放入提交前检查脚本。

### `issues`

```bash
python tools/localizer/cli.py issues --severity error
python tools/localizer/cli.py issues --severity warning --code layout_merge_danger --json
python tools/localizer/cli.py issues --refresh --limit 100
```

返回全库 QA 摘要、当前筛选总数和条目列表。常用问题代码：

```text
empty                 空译
width_error           行宽超过 50
width_warn            行宽 47–50
line_start_punct      行首标点（错误）
line_start_ellipsis   行首省略号（提示）
line_end_open         行尾开引号/括号
unclosed_code         控制符未闭合
split_code            控制符跨行
exfont_split          ExFont 控制符被拆开
kana                  残留假名
extra_code            多余控制符
missing_actor_code    角色名控制符丢失
actor_code_literal    角色编号未转义（如把 \n[102] 写成 [102]）
actor_code_misplaced  角色名控制符错位
unbound_var           变量控制符未绑定
layout_merge_danger   标题与危险度未分行
layout_merge_class    职业字段未分行
layout_merge_bullet   项目符号分行丢失
layout_merge_field    字段标签与说明未分行
```

### `layout`

```bash
python tools/localizer/cli.py layout
python tools/localizer/cli.py layout --kind danger_label --json
python tools/localizer/cli.py layout --kind class_fields --json
python tools/localizer/cli.py layout --kind bracket_title --limit 20
```

检查源文中的独立标题行在译文里被合并的情况：

- `danger_label`：源文首行是 `[地名]`，第二行是 `危険度 …`，译文变成一行。
- `class_fields`：源文 `Name :` / `Class:` / `Type :` 分行，译文合并为一行。
- `bullet_lines`：源文有多条 `・` / `※` 项目符号行，译文合并或丢失项目符号。
- `field_lines`：源文的 ASCII 字段标签/说明分行，译文被合并为一行。
- `control_lines`：源文有独立的 `\>` 控制行，译文行首 `\>` 结构被合并。
- `bracket_title`：其他 `[标题]` / `［标题］` 首行结构，译文行数少于源文。

这是人工审核候选，不自动改写。`layout` 默认不返回非零退出码；CI 可用 `--json` 自行判断。

维护时对 `control_lines` 的安全重排规则是：源文每行以 `\>` 开头、目标 `\>` 数量与源文行数一致、按 `\>` 重建后每行 ≤50 单元；不满足这些条件的条目保留在候选清单中人工处理。`bracket_title` 同样只作为候选。

## 3. Flask JSON API

启动：

```bash
cd tools/localizer
python app.py
```

默认 `http://127.0.0.1:5010/`。可用 `RYONA_PORT` 改端口。

所有响应都是 UTF-8 JSON；错误通常为：

```json
{"error": "错误说明"}
```

### `GET /api/status`

```json
{
  "entries": 46878,
  "files": 1049,
  "lang_dir": "...",
  "backup_dir": "..."
}
```

### `GET /api/search`

参数：`q`、`mode=both|jp|cn`。

```json
{
  "items": [{"file": "Map0002.po", "block": 0, "ctx": "", "msgid": "...", "msgstr": "...", "snippet": "..."}],
  "total": 16,
  "query": "门水晶",
  "used_fts": true
}
```

### `GET /api/browse`

参数：

```text
dim=maps|actors|items|skills|database|files
group=<分组 id>        可选；省略时返回 groups
offset=0
limit=50              最大 200
```

无 `group` 时返回 `categories`、`groups`、`entry_count`；有 `group` 时返回 `items`、`total`、`group_label`。

### `GET /api/entry`

参数：`file`、`block`。

返回：

```json
{
  "file": "Map0002.po",
  "block": 0,
  "ctx": "",
  "msgid": "...",
  "msgstr": "...",
  "comments": [],
  "issues": [],
  "metrics": [{"line": 1, "cells": 12, "text": "..."}],
  "pages": 1,
  "source_preview": ["data:image/png;base64,..."],
  "preview": ["data:image/png;base64,..."]
}
```

`source_preview` 是日文原版预览，`preview` 是中文译文预览。

### `POST /api/check`

请求：

```json
{"msgid": "...", "msgstr": "...", "ctx": ""}
```

返回校验问题、行宽、分页数和中文预览。`ctx` 可省略；传入 `actors.name` 时会避免把源文自带的拆行片段误报为行首标点。

### `GET /api/issues`

参数：

```text
severity=error|warning|info  可选
code=<问题代码>               可选
offset=0
limit=50                     最大 200；0 表示只取 summary
refresh=1                    强制重新扫描
```

返回：

```json
{
  "summary": {
    "scanned": 46878,
    "total": 3017,
    "entries": 2976,
    "by_severity": {"error": 12, "warning": 538, "info": 2467},
    "by_code": [{"code": "line_start_punct", "label": "行首标点", "severity": "error", "count": 12}]
  },
  "total": 12,
  "items": [{"file": "...", "block": 54, "ctx": "", "severity": "error", "code": "...", "message": "...", "source": "...", "translation": "..."}]
}
```

### `POST /api/save`

请求：

```json
{"file": "Map0002.po", "block": 0, "msgid": "...", "msgstr": "..."}
```

行为：

- 先校验；存在 `error` 时返回 HTTP 400。
- 写入前把原 PO 备份到 `tools/localizer/backups/`。
- 只替换目标条目的 `msgstr`，保留其余 PO 结构。
- 成功后更新 SQLite 索引和 QA 缓存。

Agent 不应在未展示 diff/未经确认时调用 `/api/save`。

### `POST /api/reindex`

重建 PO 搜索索引和 QA 缓存，不修改译文。

## 4. Agent 使用建议

1. 先用 `search` 或 `browse` 定位条目，记录 `file` 和 `block`。
2. 用 `entry --json` 读取完整上下文、校验和预览页数。
3. 修改后先 `check`；有 `error` 不要保存。
4. 需要批量分析时使用 `issues --json` 和 `layout --json`，不要逐条启动浏览器。
5. 需要实机效果时再用编辑器或部署脚本；`preview` 只是近似结果。

当前不提供 MCP 服务。对 Agent 来说，CLI 的 `--json` 稳定输出比额外维护 MCP 进程更简单；如果未来出现多客户端统一集成需求，可在这些函数之上增加只读 MCP 包装。
