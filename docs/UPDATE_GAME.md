# 游戏本体更新后的翻译维护流程

适用对象：RyonaRPG 2026 日本語版更新、翻译仓库 `language/zh_CN` 需要跟随更新时。

本文只维护翻译仓库；不直接修改游戏目录的 LDB/LMU/LMT。旧游戏目录、旧 release 和旧 tag 应保留，便于回滚。

## 1. 先判断变化范围

不要看到游戏更新就直接全量重译。先确认更新类型：

| 变化 | 需要做什么 |
| --- | --- |
| 只改 exe、音频、脚本，文本/图片数据未变 | 跑 QA、部署、更新版本号即可 |
| 只改少量 `Map*.lmu` | 重导对应地图 PO，合并旧译文 |
| `RPG_RT.ldb` 变化 | 重导数据库/公共事件 PO，重生成物品/技能等相关图片 |
| `RPG_RT.lmt` 变化 | 重导 LMT，检查地图树、战斗文本 |
| core 大版本变化 | 按 core 重基线：全量重导、PO 合并、图片映射复核 |
| `Picture/*` 模板变化 | 重新生成受影响图片组，不能只沿用旧覆盖图 |

LDB 哈希只能说明数据库有没有变，**不能说明地图有没有变**。地图必须单独比较。

## 2. 自动化检查

仓库提供只读检查器：

```bash
python tools/update_check.py \
  --game-dir "D:\Games\RyonaRPG-new" \
  --old-game-dir "D:\Games\RyonaRPG-old"
```

它会：

- 计算新 `RPG_RT.ldb` 的 SHA-256，并与 `compat.json` 比较；
- 比较旧/新 `RPG_RT.ldb`、`RPG_RT.lmt`；
- 比较 1,425 个 `Map*.lmu`，列出新增/删除/变更；
- 比较 `Picture/Menu`、`Pict_op`、`SkillName`、`Interface`、`Ending`、`Mini_game`；
- 输出需要重导 PO、重生成图片或更新 `compat.json` 的建议。

只核对 compat 哈希、不做旧版本比较：

```bash
python tools/update_check.py --game-dir "D:\Games\RyonaRPG-new"
```

机器可读输出：

```bash
python tools/update_check.py \
  --game-dir "D:\Games\RyonaRPG-new" \
  --old-game-dir "D:\Games\RyonaRPG-old" \
  --json
```

退出码：

- `0`：未发现结构变化，或提供的旧目录与新版一致；
- `1`：LDB 哈希不一致，或检测到 LDB/LMT/地图/图片变化；
- `2`：路径、参数或读取错误。

检查器只读，不会修改游戏目录、`language/zh_CN` 或 `compat.json`。

## 3. 编辑器可视化检查

启动编辑器：

```bash
cd tools/localizer
python app.py
```

打开 `http://127.0.0.1:5010/update`，或在文本编辑器/图片工具顶部点“更新检查”。

页面流程：

1. 选择新游戏目录；
2. 可选选择旧游戏目录；
3. 点“运行检查”；
4. 查看 LDB 哈希、地图/图片变化数量、逐文件变化列表和处理建议。

检查同样只读。大版本首次检查会读取地图和约 5,000 张图片计算 SHA-256，通常需要几秒。

## 4. 导出新版本数据

使用 liblcf 的 `lcf2xml`，必须带 `--2k --encoding 932`：

```bash
lcf2xml --2k --encoding 932 RPG_RT.ldb
lcf2xml --2k --encoding 932 RPG_RT.lmt
```

地图逐个导出，避免一次传太多文件：

```bash
for f in Map*.lmu; do
  lcf2xml --2k --encoding 932 "$f"
done
```

输出写到当前目录的 `.edb`、`.emt`、`.emu`。建议在独立的临时目录执行，不要覆盖游戏根目录中的原文件。

编辑器图片工具可以自动生成 EDB：

- 在 `/images` 中选择 `lcf2xml.exe`；
- 点“从 LDB 导出”；
- 输出为 `tools/localizer/data/RPG_RT.edb`，并自动写入配置。

## 5. 重新生成并合并 PO

用现有 LcfTrans/导出流水线从新数据生成日文 PO 模板，保留旧 `language/zh_CN/*.po` 作为翻译记忆。

只改了部分地图时，只合并对应 `MapNNNN.po`；LDB/LMT 变化时再处理数据库和公共事件 PO。

可用 gettext 合并：

```bash
msgmerge --update --backup=none language/zh_CN/Map0001.po new/Map0001.po
```

合并后检查未翻译和 fuzzy：

```bash
msgattrib --untranslated language/zh_CN/Map0001.po
msgattrib --only-fuzzy language/zh_CN/Map0001.po
```

注意：

- 按“完整消息”翻译，不能按行翻译；
- PO 条目会合并连续 `10110`，不要按 PO 注释里的 `ID` 跨页分组；
- 源文变化后的 fuzzy 译文必须人工复核，不能直接接受；
- 保留控制符、`\n[...]`、`$x`、行宽和分页结构。

当前仓库没有内置 LcfTrans 的一键 PO 重导/合并脚本；这一步仍使用现有外部流水线，仓库侧负责合并后的编辑、QA、图片和发布。

## 6. 翻译新增/变更条目

使用编辑器：`http://127.0.0.1:5010/`。

也可以用 aiNiee/DeepSeek 批量处理新增条目，但必须遵守：

- 按消息翻译，不按行翻译；
- 保留 `HP`、`MP`、`EXP`、`LV`、`G` 等缩写；
- 保留刻意不译的拟声、乱码书页、密码和梗；
- 新增角色/术语先查术语表，必要时补充；
- 每行 ≤50 半角单元，目标 46–48。

## 7. QA

```bash
python tools/qa/run_all.py
python tools/localizer/cli.py misalign --json
```

如果更新了行级 TM 参考：

```bash
python tools/qa/build_tm_reference.py \
  --tm "D:\Games\RyonaRPG-new\ManualTransFile_translated.json"
```

必须达到 `QA OK`，重点检查：

- 0 空译；
- 0 行超宽、0 行首标点、0 跨行断码；
- 0 整段错位错误；
- 图片 manifest 无缺失。

## 8. 更新图片

数据库名称/说明变化：

```bash
python tools/images/build.py check \
  --game-dir "D:\Games\RyonaRPG-new" \
  --edb "D:\dump\RPG_RT.edb" \
  --kind all
```

`stale` 非 0 时执行：

```bash
python tools/images/build.py build \
  --game-dir "D:\Games\RyonaRPG-new" \
  --edb "D:\dump\RPG_RT.edb" \
  --kind all
```

其他图片组：

```bash
python tools/images/charselect_overrides.py --game-dir "D:\Games\RyonaRPG-new" --check
python tools/images/skillname_overrides.py --game-dir "D:\Games\RyonaRPG-new" --check
python tools/images/interface_overrides.py --game-dir "D:\Games\RyonaRPG-new" --check
python tools/images/ending_overrides.py --game-dir "D:\Games\RyonaRPG-new" --check
python tools/images/minigame_overrides.py --game-dir "D:\Games\RyonaRPG-new" --check
```

也可以在 `/images` 页面按图片组执行 check/build。新增/删除图片时同步更新 `_img_manifest.json`。

## 9. 更新元数据与版本

修改：

- `compat.json`
  - `game_version`
  - `game_ldb_sha256`
  - `translation_version`
- `CHANGELOG.md`
- 必要时更新 `docs/PRESERVED_JAPANESE.md` 的适用版本

版本号按 `x.y.z`：

- `x`：游戏 core 版本变化，需要重做翻译基线；
- `y`：游戏 up/内容更新；
- `z`：游戏本体未更新，仅翻译修正。

## 10. 部署与实机验证

先 dry-run：

```bash
python tools/deploy_to_game.py \
  --game-dir "D:\Games\RyonaRPG-new" \
  --dry-run
```

确认后部署：

```bash
python tools/deploy_to_game.py \
  --game-dir "D:\Games\RyonaRPG-new" \
  --with-launcher
```

脚本会备份现有 `language/zh_CN`，并在 LDB 哈希不一致时警告。

用 EasyRPG 以 `--language zh_CN` 启动，至少检查：

- 标题、菜单、物品/技能说明；
- 本次更新到的地图/事件；
- 战斗技能名和状态图标；
- 结局、Boss 文本等图片覆盖。

## 11. 提交、发布与回滚

```bash
python tools/qa/run_all.py
python tools/build_release.py
```

提交 PO、图片、manifest、`compat.json`、`CHANGELOG.md`，推送后打新 tag。已有 Release 资产的 tag 不要移动；修复发新的补丁版本。

回滚：

- 保留旧 release zip 和旧 `language/zh_CN` 备份；
- `tools/deploy_to_game.py` 每次部署前备份到 `backups/`；
- 新版本有严重问题时，部署旧 release 的 `language/zh_CN` 即可恢复。

## 12. 最短检查清单

- [ ] 用 `update_check.py` 或 `/update` 判断 LDB/LMT/地图/图片变化
- [ ] 新游戏目录与旧目录分开保存
- [ ] 重导对应数据，只合并受影响的 PO
- [ ] 新增/变更条目按完整消息翻译
- [ ] `run_all.py` + `misalign` 通过
- [ ] 受影响图片 check/build，manifest 完整
- [ ] 更新 `compat.json`、`CHANGELOG.md`、版本号
- [ ] dry-run 部署，EasyRPG 实机回归
- [ ] 提交、打 tag、发布
