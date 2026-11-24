# RyonaRPG 中文翻译仓库：Agent 指南

本文件面向在本仓库工作的 Agent/维护者。开始任何修改前先读本文件、`README.md` 和 `compat.json`。

## 0. 当前状态

- 游戏原版：**Classic Japanese `core0163`**（Japanese maintenance edition based on core0163）。
- 当前 `RPG_RT.ldb` SHA-256：`5bedbdcf2507632a65d4b2bab4d500d0795982f62c5b02f1345a7ed8a7d4c76a`。
- 翻译版本：`0.1.0`，已发布 GitHub Release。
- 文本：46,878 条，0 空译；图片覆盖 4,940 项。
- 当前行宽：硬上限 50 半角单元；0 行 >50，54 行处于 47–50。
- 英文 Classic 参考：`RyonaRPG-classic-en-a8d5ca191a4c.zip`（2026-09-13，Git `a8d5ca191a4c`），**不是本补丁基础版本**。

## 1. 仓库结构

```text
language/zh_CN/          译文唯一源（PO + Meta.ini + Picture 覆盖图）
tools/localizer/         Flask 本地编辑器、只读 CLI（分类浏览、全文搜索、QA 面板、预览）
tools/qa/run_all.py      提交/发布 QA
tools/build_release.py   生成 release zip
tools/deploy_to_game.py  部署到游戏目录（带备份和哈希检查）
launcher/                启动中文版.bat / 安装说明
docs/                    保留日文说明等背景资料
compat.json              原版版本与 LDB 哈希
.github/workflows/       validate / release
```

不提交：`dist/`、`backups/`、`tools/localizer/data/`、`tools/localizer/backups/`、`__pycache__/`、`.venv/`。

## 2. 修改译文的正确流程

1. 只改 `language/zh_CN/*.po` 的 `msgstr`；保留 `msgctxt`、`msgid`、注释、BOM 和文件其余结构。
2. 不要直接改 LDB/LMU/LMT；游戏数据不在本仓库。
3. 本地编辑：

```bash
cd tools/localizer
python -m pip install -r requirements.txt
python app.py
```

默认读取本仓库 `language/zh_CN`。需要编辑游戏目录副本时设置 `RYONA_LANG_DIR`。

4. 保存后跑：

```bash
python tools/qa/run_all.py
```

5. 查看 `git diff`，确认只有预期的 PO/图片/manifest 变化；不要提交编辑器索引、备份或 release 产物。

## 3. QA 规则

`tools/qa/run_all.py` 必须返回 `QA OK`。当前门禁：

- 0 空译；
- 0 行 >50 半角单元；
- 0 行首标点（仅允许 `actors.name` 中源文自带的 2 条拆分片段）；
- 0 跨行断码（行尾 `\`、行尾 `\v`/`\c`/`\n` 后接 `[...]`、`$x` 被换行拆开）；
- 0 个 `\n`/`\N` 后不接 `[` 的裸角色名代码；
- 0 个未转义的角色编号文本（`actor_code_literal`，例如把 `\n[102]` 写成 `[102]`）；
- 0 弯引号、0 个 `。。`/`，，`；
- 0 处“标题 + 危険度”、`Name/Class/Type`、`・/※` 列表、字段标签或 `【说话人】` 标签被合并且丢失分行（`layout_merge_*`；`bracket_title` 和 `control_lines` 用 CLI `layout` 单独审阅，后者保留源文 `\>` 行结构）；
- `_img_manifest.json` 中 4,940 个图片全部存在。

行宽 47–50 为允许值（CLAUDE.md 上限 50），但新增文案应优先控制在 46–48。

## 4. 控制符与 EasyRPG 事实

- `\n[id]` / `\N[id]`：角色名；`0` = 队伍首位，**通常保留，不要改成 `\N[1]`**。无队伍时 EasyRPG 才警告 `Invalid Actor Id 0`。
- `\v[id]` / `\V[id]`：变量值，1–5000。
- `\c[id]` / `\C[id]`：颜色 0–19；越界 EasyRPG 静默重置为 0。
- `\s[id]` / `\S[id]`：文字速度 1–20，0 为默认。
- `\$` 金钱、`\_` 半角空格、`\!` 等待按键、`\.` 短停顿、`\|` 长停顿、`\^` 自动关闭、`\>`/`\<` 瞬间显示、`\\` 字面反斜杠。
- `$A`–`$Z` / `$a`–`$z`：ExFont 图形字，每个 2 单元且不可拆开。
- `\n[\v[X]]` 这类嵌套变量合法；代码、参数和 `$x` 不能跨行拆开。
- 地图消息**没有自动换行**；每行控制在 50 单元内，EasyRPG 每 4 行自动分页。
- `\N[0]`、源文 bare `\S`、`\v[5018]`、`\,`、`\1`、`\[6]`、`\~`、行尾 `\` 等是源文历史写法，不要盲目批量改写；只有确认是断码且影响显示时才修。

## 5. 图片

- 覆盖图已随仓库提交；普通对白修改不需要重新生成图片。
- 修改物品/技能/ABL/EX 名称或说明时，才需要从原游戏 `Picture/Menu` 模板和 LDB 重新生成。
- 图片生成脚本依赖游戏素材，默认不随公开仓库分发；生成后必须更新 `_img_manifest.json`。
- 所有菜单 PNG 为 P 模式，索引 0 为透明色键 `(255,156,0)`；禁止改成 RGBA。
- `_img_manifest.json` 路径必须使用 `/`。Windows 的 `Picture\Menu\...` 会让 Linux CI 找不到图片并导致 release 失败。

## 6. 发布与部署

- 修改版本：同时更新 `compat.json` 的 `translation_version` 和 `CHANGELOG.md`。
- 校验游戏版本：`compat.json` 的 `game_ldb_sha256` 必须与目标 `RPG_RT.ldb` 一致；不一致先警告并 QA。
- 本地构建：

```bash
python tools/qa/run_all.py
python tools/build_release.py
```

- 发布：推送 `v*` tag，GitHub Actions 运行 `validate` + `release`，生成 `RyonaRPG-zh_CN-<version>.zip` 并创建 Release。
- tag 一旦已有 Release 资产，不要再移动；修复发新补丁版本。
- 部署到游戏：

```bash
python tools/deploy_to_game.py --game-dir "D:\Games\RyonaRPG" --with-launcher
```

脚本会备份现有 `language/zh_CN` 并检查 LDB 哈希；先跑 `--dry-run` 更安全。

## 7. 已知坑点

1. 不要按 PO 注释里的 `ID` 跨页合并消息；跨页必须看 LMU 连续 `10110`。
2. 不要把一条消息按行拆开翻译；先拼回完整消息再译。
3. 空 `msgid` 是文件头；构造字典时必须 `tr.pop('', None)`。
4. PO 文件头/空文本不能渲染进图片。
5. `_img_manifest.json` 反斜杠会导致 Linux CI 失败。
6. `\n`/`[62]` 拆开会出现字面 `[62]` 和 `Invalid Actor Id 0`；`$k`/`$g` 拆开也会坏。
7. `\N[0]` 不是错误，是队伍首位写法；不要固定成 `\N[1]`。
8. 源文自身存在少量异常控制符；修复前确认是译文引入还是源文遗留。
9. CRLF：PO/MD/JSON 按 LF 提交；Windows 写 JSON 时用 `newline='\n'`。
10. 旧目录 `E:\ryonarpg\RyonaRPG_Localizer` 不是主仓库；以 `tools/localizer` 为准。
11. 女主人公称呼：`\N[\V[6]]くん/さん` 不译“先生/君”；现代汉语优先省略敬称或用“你”，正式场合用“小姐/女士”。`くん` 也不是“先生”，`聖女くん` 用“圣女”。NPC 的“先生/小姐”等称呼按角色性别和关系单独判断，不做全局替换；史莱姆、猫、马、妖怪、触手、士兵、佣兵、警卫等非人类/职业角色不要默认加“先生”。

## 8. 相关文档

- `README.md`：用户安装、部署、发布说明。
- `docs/LOCALIZER_CLI.md`：CLI 与 Flask JSON API 的命令、字段和 Agent 使用建议。
- `compat.json`：原版版本、LDB 哈希、翻译版本。
- `docs/PRESERVED_JAPANESE.md`：刻意保留日文的背景说明。
- 游戏工程侧更详细的翻译/图片流水线见游戏目录的 `AGENT.md`；本仓库以 `language/zh_CN` 和发布流程为准。
