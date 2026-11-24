# RyonaRPG 本地化编辑器

本地单用户编辑器，用来安全修改 `language/zh_CN/*.po` 译文，并检查本作特有的显示限制。

## 启动

```bash
cd tools/localizer
python -m pip install -r requirements.txt
python app.py
```

浏览器打开 `http://127.0.0.1:5010/`。

默认读取本仓库的 `language/zh_CN`。如果要对游戏目录中的副本做测试，可用环境变量覆盖：

```bash
set RYONA_LANG_DIR=D:\some\language\zh_CN
set RYONA_PORT=5010
python app.py
```

## 功能

- **分类浏览**：搜索框为空时，左侧按“地图 / 角色 / 物品 / 技能 / 状态与术语 / 全部 PO 文件”分组；进入分组后每条记录同时显示原文和译文，可筛选分组并分页加载。
- **全库 QA 面板**：扫描全部 46,878 条译文，按错误 / 警告 / 提示和问题类型筛选；点击问题直接打开对应条目。行首省略号归为提示，不阻塞保存；`layout_merge_danger` 会提示标题与危险度被合并。
- **全库全文搜索**：中日文、文件名、上下文；输入游戏里看到的中文即可反查 PO 条目。搜索按单条消息匹配；如果一句话跨多条消息/分页，建议搜索其中一段。
- **安全编辑**：只替换目标条目的 `msgstr`，保留 `msgctxt`、`msgid`、注释和文件其余结构。
- **保存前校验**：每行 ≤50 半角单元、行首/行尾标点、跨行断码、角色名控制符 `\n[...]`/`\N[...]`、ExFont `$x` 拆分、空译、假名、重复标点、花引号、控制符差异。
- **消息预览**：右侧同时显示日文原版和中文译文，各为 320×80、12px 字体、每 4 行一页，方便对照换行与分页。
- **备份**：每次保存前把原 PO 复制到 `backups/`，文件名带时间戳。
- **索引重建**：保存后自动更新索引；也可点“重建索引”。

## CLI 与接口

浏览器之外，可以用 CLI 做查询、浏览、校验和 QA 分析：

```bash
python tools/localizer/cli.py status --json
python tools/localizer/cli.py search "门水晶" --json
python tools/localizer/cli.py browse maps --group Map0002.po --json
python tools/localizer/cli.py entry Map0002.po 0 --json
python tools/localizer/cli.py issues --severity warning --json
python tools/localizer/cli.py layout --kind danger_label --json
```

CLI 默认只读，不提供保存命令。Flask JSON API、字段说明和 Agent 使用建议见 [docs/LOCALIZER_CLI.md](../../docs/LOCALIZER_CLI.md)。

## 安全边界

- 只写 `language/zh_CN/*.po`，不直接修改 LDB/LMU/LMT。
- 保存前有错误会拒绝写入；警告允许保存，但需要人工确认。
- 仍在游戏内用 EasyRPG Player 做最终确认；预览只是近似，不能替代实机。
- 修改道具/技能/ABL/EX 名称或说明后，图片需要另行重生成。

## 目录

- `po_store.py`：PO 解析、SQLite 索引、搜索、保存。
- `qa_store.py`：全库 QA 扫描、问题分类与筛选缓存。
- `layout.py`：源文标题/换行结构与译文差异检查。
- `validators.py`：行宽、标点、断码、控制符校验。
- `cli.py`：只读 CLI，支持 `--json`。
- `preview.py`：消息窗口 PNG 预览。
- `app.py`：Flask 路由。
- `data/index.db`：搜索索引（可删除后重建）。
- `backups/`：保存前备份。
