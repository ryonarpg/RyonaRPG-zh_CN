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
- **全库 QA 面板**：扫描全部 46,878 条译文，按错误 / 警告 / 提示和问题类型筛选；点击问题直接打开对应条目。行首省略号归为提示，不阻塞保存；版式检查覆盖危险度、职业字段、项目符号和字段标签的异常合并。
- **QA 白名单**：确认某个 QA 问题不是错误后，可将其加入白名单；白名单视图可查看已确认问题并移出。白名单保存在 `qa_whitelist.json`，按条目原文/译文哈希匹配，修改条目后不会继续屏蔽新问题。
- **原数据乱码页**：源数据本身完全乱码的 53 条已复制原文为译文并加入白名单；不要用机器翻译继续改写这些内容。
- **全库全文搜索**：中日文、文件名、上下文；输入游戏里看到的中文即可反查 PO 条目。搜索按单条消息匹配；如果一句话跨多条消息/分页，建议搜索其中一段。
- **安全编辑**：只替换目标条目的 `msgstr`，保留 `msgctxt`、`msgid`、注释和文件其余结构。
- **保存前校验**：每行 ≤50 半角单元、行首/行尾标点、跨行断码、角色名控制符 `\n[...]`/`\N[...]`、未转义的角色编号、ExFont `$x` 拆分、空译、假名、HP/MP 被译成中文、重复标点、花引号、控制符差异。
- **整段错位检查**：用行级 TM 参考检测译文是否实际对应上一条/下一条源文；同一方向连续 3 个及以上候选会在 `run_all.py` 中失败，2 个和单条候选只作提示。
- **消息预览**：右侧同时显示日文原版和中文译文，各为 320×80、12px 字体、每 4 行一页，方便对照换行与分页。
- **图片工具**：打开 `/images`，用系统目录选择器设置游戏路径和 `RPG_RT.edb`；按 Menu/Pict_op/SkillName/Interface/Ending/Mini_game 浏览原版与中文覆盖图，查看并排预览、透明色键和像素差异，并直接运行 `check`/`build` 生成脚本（后台任务与日志）。配置保存在 `data/image_config.json`。
- **EDB 自动导出**：选择已有的 `lcf2xml.exe` 后点“从 LDB 导出”，编辑器会从 `RPG_RT.ldb` 生成 `data/RPG_RT.edb` 并自动填入配置。liblcf 官方 release 页目前只提供源码包，没有可靠的官方 Windows 预编译包，因此编辑器不自动下载；可使用已有二进制、MSYS2 包（`mingw-w64-liblcf`）或自行构建。官方项目：https://github.com/EasyRPG/liblcf/releases
- **游戏更新检查**：打开 `/update` 选择新旧游戏目录，比较 LDB、LMT、地图和图片，列出需要重导 PO/重生成图片的部分；同一逻辑可用 `python tools/update_check.py --json`。流程见 `docs/UPDATE_GAME.md`。
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
python tools/localizer/cli.py misalign --json
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
- `qa_whitelist.py` / `qa_whitelist.json`：QA 白名单读写；按条目译文哈希匹配。
- `layout.py`：源文标题/换行结构与译文差异检查。
- `misalignment.py`：基于行级 TM 的整段译文错位检测。
- `validators.py`：行宽、标点、断码、控制符校验。
- `cli.py`：只读 CLI，支持 `--json`。
- `preview.py`：消息窗口 PNG 预览。
- `image_store.py`：图片列表、原版/覆盖图预览、`.xyz` 解码、像素差异和生成任务。
- `templates/images.html`、`static/images.js`、`static/images.css`：图片工具页面。
- `app.py`：Flask 路由。
- `data/index.db`：搜索索引（可删除后重建）。
- `data/image_config.json`：本地图片工具配置（游戏目录、EDB、字体，不提交）。
- `backups/`：保存前备份。
