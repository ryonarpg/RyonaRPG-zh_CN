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
hpmp_chinese          HP/MP 被译成中文（建议保留 HP/MP）
extra_code            多余控制符
missing_actor_code    角色名控制符丢失
actor_code_literal    角色编号未转义（如把 \n[102] 写成 [102]）
actor_code_misplaced  角色名控制符错位
unbound_var           变量控制符未绑定
layout_merge_danger   标题与危险度未分行
layout_merge_class    职业字段未分行
layout_merge_bullet   项目符号分行丢失
layout_merge_field    字段标签与说明未分行
layout_merge_speaker  说话人标签与台词合并
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
- `speaker_lines`：源文的 `【说话人】` 标签独立成行，译文与台词合并。
- `bracket_title`：其他 `[标题]` / `［标题］` 首行结构，译文行数少于源文。

这是人工审核候选，不自动改写。`layout` 默认不返回非零退出码；CI 可用 `--json` 自行判断。

维护时对 `control_lines` 的安全重排规则是：源文每行以 `\>` 开头、目标 `\>` 数量与源文行数一致、按 `\>` 重建后每行 ≤50 单元；不满足这些条件的条目保留在候选清单中人工处理。`bracket_title` 同样只作为候选。

### `misalign`

```bash
python tools/localizer/cli.py misalign
python tools/localizer/cli.py misalign --file Map1156.po --json
python tools/localizer/cli.py misalign --reference tools/qa/tm_reference.json.gz --json
```

检查“整段译文错位”：译文实际对应上一条或下一条源文，而不是当前源文。使用旧版行级翻译记忆 `tools/qa/tm_reference.json.gz` 作参照；该文件由 `tools/qa/build_tm_reference.py` 从游戏目录的 `ManualTransFile_translated.json` 生成，只保留当前 PO 源文行需要的条目。

判定规则：

- 当前条目、上一条、下一条分别计算译文与对应 TM 译文的中文字符集合 Dice 相似度；
- 当前相似度 ≤0.45，且相邻条目相似度 ≥0.45、至少高 0.18，并且 TM 覆盖足够时，记为候选；
- 连续 3 个及以上、方向一致（都偏向 `prev` 或都偏向 `next`，允许间隔 2 条）的候选记为 **run**，CI 会失败；
- 2 个连续或单条候选记为 **short / single**，只作为人工复核提示，不阻塞 QA。

输出字段：

```text
skipped       参考文件缺失时为 true
reference     TM 参考路径
summary       files_scanned / files_with_flags / flags / runs / short_runs / singles
runs[]        file, start_block, end_block, direction, count, flags[]
singles[]     单条候选，含 margin、self、best、source、translation、tm
```

`--file` 只扫描一个 PO 文件；`--limit` 控制文本输出的条目数。有 run 时退出码为 `1`，只有 short/single 时为 `0`，参考文件缺失时为 `2`。

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
  "items": [{"id": "f440f96b7cf7dffa836eab8d", "file": "...", "block": 54, "ctx": "", "severity": "error", "code": "...", "message": "...", "source": "...", "translation": "..."}]
}
```

`items[].id` 是白名单操作的稳定标识，由文件、block、问题代码、行号、当前原文和译文共同计算。

### `GET /api/whitelist`

返回已确认问题：

```json
{
  "total": 1,
  "entries": [{
    "id": "f440f96b7cf7dffa836eab8d",
    "file": "Map0001.po",
    "block": 77,
    "code": "kana",
    "line": 0,
    "severity": "warning",
    "label": "残留假名",
    "message": "...",
    "note": "",
    "created_at": "2026-11-24T22:00:00"
  }]
}
```

白名单保存在 `tools/localizer/qa_whitelist.json`，应随仓库提交。

### `POST /api/whitelist`

```json
{"id": "f440f96b7cf7dffa836eab8d", "note": "可选备注"}
```

把当前 QA 问题加入白名单；加入后该问题从 `/api/issues` 的结果和统计中排除。

### `POST /api/whitelist/remove`

```json
{"id": "f440f96b7cf7dffa836eab8d"}
```

移出白名单；下次 QA 扫描时问题会重新出现。

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

### `POST /api/deploy`

把仓库 `language/zh_CN` 增量同步到已配置的游戏目录：

```json
{"game_dir": "D:\\Games\\RyonaRPG"}
```

`game_dir` 可省略，使用图片工具/更新检查保存的游戏目录。行为：

- 只复制大小或 mtime 变化的文件；图片很多时不会每次全量复制。
- 只备份即将被覆盖的目标文件到 `backups/deploy_<时间>_zh_CN`。
- 校验 `RPG_RT.ldb` 哈希，不一致时返回警告。
- 不会删除游戏目录中仓库没有的额外文件。
- 部署后需要重启 EasyRPG，PO 不会热加载。

编辑器条目的“保存并部署”和“自动部署”调用此接口；命令行等价于：

```bash
python tools/deploy_to_game.py --game-dir "D:\Games\RyonaRPG" --incremental
```

### `POST /api/reindex`

重建 PO 搜索索引和 QA 缓存，不修改译文。

### 图片工具（`/images` 与 `/api/image/*`）

浏览器打开 `http://127.0.0.1:5010/images`，可选择游戏目录、`RPG_RT.edb` 或 `lcf2xml.exe`，按图片组浏览原版/中文覆盖图，查看并排预览、像素差异，或调用生成脚本。游戏目录、EDB、lcf2xml 和字体保存在 `tools/localizer/data/image_config.json`（本地文件，不提交）。

- `GET /api/image/config`：返回配置、路径校验结果、图片组和 Menu 生成范围。
- `POST /api/image/config`：保存 `{game_dir, edb_path, lcf2xml, font}`。
- `POST /api/image/pick`：打开系统目录/文件选择器，参数 `{kind: "dir"|"file", title}`。
- `POST /api/image/export-edb`：用配置的 `lcf2xml` 从游戏 `RPG_RT.ldb` 导出 `tools/localizer/data/RPG_RT.edb`，成功后自动写入 `edb_path`；返回 `job_id`。
- `GET /api/image/list?family=Menu&q=&offset=0&limit=100`：列出原版/覆盖图；`family` 取 `Menu`、`Pict_op`、`SkillName`、`Interface`、`Ending`、`Mini_game`、`All`。
- `GET /api/image/preview?path=Picture/...&side=source|override&alpha=1`：返回 PNG；`.xyz` 会即时解码，`alpha=0` 显示原始透明色键。
- `GET /api/image/compare?path=Picture/...`：返回尺寸、像素差异数和差异范围。
- `POST /api/image/generate`：`{family, mode: "check"|"build", kind}`，返回 `job_id`；任务在后台运行，`build` 会直接写入 `language/zh_CN`。
- `GET /api/image/job/<job_id>`：读取任务状态、退出码和日志。

生成命令只来自固定注册表：Menu 使用 `tools/images/build.py`，其余图片组使用对应的 `tools/images/*_overrides.py`。工具不接受任意命令。

### 游戏更新检查（`/update`）

`http://127.0.0.1:5010/update` 用于比较新旧游戏目录的 `RPG_RT.ldb`、`RPG_RT.lmt`、`Map*.lmu` 和图片组，输出重导 PO/重生成图片的建议。检查只读。

- `POST /api/update/check`：请求 `{game_dir, old_game_dir}`；`old_game_dir` 可省略，此时只核对 compat 哈希。
- 同一逻辑也可用 CLI：`python tools/update_check.py --game-dir <新目录> --old-game-dir <旧目录>`，支持 `--json`。
- 完整更新流程见 [UPDATE_GAME.md](UPDATE_GAME.md)。

## 4. Agent 使用建议

1. 先用 `search` 或 `browse` 定位条目，记录 `file` 和 `block`。
2. 用 `entry --json` 读取完整上下文、校验和预览页数。
3. 修改后先 `check`；有 `error` 不要保存。
4. 需要批量分析时使用 `issues --json`、`layout --json` 和 `misalign --json`，不要逐条启动浏览器。
5. 需要实机效果时再用编辑器或部署脚本；`preview` 只是近似结果。

当前不提供 MCP 服务。对 Agent 来说，CLI 的 `--json` 稳定输出比额外维护 MCP 进程更简单；如果未来出现多客户端统一集成需求，可在这些函数之上增加只读 MCP 包装。
