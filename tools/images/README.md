# 菜单图片生成与校验

本目录把中文化使用的菜单图片生成脚本纳入仓库，便于 clone 后在本地重新生成、检查和提交 `language/zh_CN/Picture/Menu`。

仓库**不包含**游戏素材、`RPG_RT.edb`、字体或原版生成工具。使用时需要你自己拥有的原版游戏目录。

## 依赖

```bash
python -m pip install -r tools/images/requirements.txt
```

另外需要：

- 原版游戏目录：包含 `RPG_RT.ldb` 和 `Picture/Menu` 模板。
- `RPG_RT.edb`：用 liblcf 的 `lcf2xml` 从原版 LDB 导出。
- 中文字体：默认 Windows 的 `C:\Windows\Fonts\simsun.ttc`；其他系统用 `--font` 指定。

导出 EDB（必须带 `--encoding 932`，否则日文会乱码）：

```bash
lcf2xml --2k --encoding 932 "D:\Games\RyonaRPG\RPG_RT.ldb"
```

输出文件 `RPG_RT.edb` 会出现在当前目录。也可以把 `lcf2xml` 路径传给工具，让它自动导出：

```bash
python tools/images/build.py check \
  --game-dir "D:\Games\RyonaRPG" \
  --lcf2xml "C:\tools\lcf2xml.exe" \
  --kind all
```

## 命令

```bash
# 生成到仓库默认目录 language/zh_CN/Picture/Menu
python tools/images/build.py build --game-dir "D:\Games\RyonaRPG" --edb "D:\dump\RPG_RT.edb" --kind all

# 只检查：生成到临时目录，与仓库现有图片比较，不修改仓库
python tools/images/build.py check --game-dir "D:\Games\RyonaRPG" --edb "D:\dump\RPG_RT.edb" --kind all

# 只校验现有图片：P 模式、调色板、尺寸、manifest
python tools/images/build.py validate --game-dir "D:\Games\RyonaRPG"
```

退出码：

- `0`：全部通过。
- `1`：`check` 发现 stale/missing/extra/invalid，或 `build` 后校验失败。
- `2`：参数/路径错误。

`check` 会重新渲染到临时目录，不写入仓库；`build` 会直接覆盖 `language/zh_CN/Picture/Menu` 下的对应图片。

## `--kind`

| kind | 内容 | 需要 EDB |
| --- | --- | --- |
| `items` | `Item/Name`、`Item/Desc` | 是 |
| `skills` | `Skill/Name`、`Skill/Desc` | 是 |
| `abl` | `ABL` | 否 |
| `ex` | `EX` | 否 |
| `itm` | `ITM` | 否 |
| `labels` | `MN_ST_*`、`MN_Wpn_*`、`MN_Mode_*`、`MN_OPT_*` 等 | 否 |
| `menu_rest` | `ItemSelector`、`CraftMenu`、`aptSet`、`cvSet`、`MN_MSG` | 否 |
| `mn_main` | `MN_Main_000001`–`009003` | 否 |
| `br_pages` | `MN_BR_0440`、`MN_BR_0602` | 否 |
| `sub_lists` | `MN_Sub_000100/003100/004100/005100` | 否 |
| `cat_menu` | `MN_Sub_001100` | 否 |
| `status_panel` | `MN_Main_000000` | 否 |
| `sub_000200` | `MN_Sub_000200` | 否 |
| `all` | 以上全部 | 是 |

`--kind` 也支持逗号分隔，例如 `--kind items,skills`。

## 判断是否需要更新

`check` 的判定方式：

1. 用当前 PO、EDB 和原版模板重新渲染所有选中图片到临时目录。
2. 与仓库 `Picture/Menu` 中的同名图片比较尺寸、透明色键和 RGB 像素。
3. 输出 `stale`（内容不同）、`missing`（仓库缺图）、`extra`（仓库多图，仅 `all`）和 `invalid`（格式错误）。

当前仓库执行 `--kind all` 的期望结果是：

```text
generated 4940 | stale 0 | missing 0 | extra 0 | invalid 0
```

如果改了 PO 但没有重新生成对应图片，`check` 会把对应文件列为 `stale`。

## 图片正确性校验

`validate` 检查：

- PNG 可打开，模式为 `P`。
- 调色板存在；透明图索引 0 必须是 `(255,156,0)`。全屏不透明图（例如 `MN_Main_000000.png`）允许索引 0 使用背景色。
- 有原版模板时，尺寸必须与模板一致；`ABL`/`EX`/`ITM` 按已知尺寸校验。
- `_img_manifest.json` 中的路径全部存在；`--kind all` 时还检查目录中没有 manifest 之外的 PNG。

`build` 写完后会自动执行同样校验。

## 修改文本后的推荐流程

1. 在编辑器保存 PO。
2. 判断哪些图片受影响：
   - 物品名称/说明 → `items`
   - 技能名称/说明 → `skills`
   - ABL/EX/ITM 名称 → `abl`/`ex`/`itm`
   - 菜单标签 → 对应 `labels`/`menu_*` 等
3. 运行 `check --kind ...`，查看 `stale` 列表。
4. 运行 `build --kind ...` 更新。
5. 再运行 `check --kind ...` 和 `python tools/qa/run_all.py`。
6. 提交 PO + PNG。只有新增/删除图片时才需要更新 `_img_manifest.json`；同名替换不需要。

## 字体

生成结果依赖字体。仓库当前图片使用 Windows `simsun.ttc`（12px 位图化前的抗锯齿阈值渲染）。使用其他字体可能得到不同像素，`check` 会因此报 `stale`，即使文字内容正确。需要复现当前图片时请使用同一字体。

## 目录

```text
tools/images/
  build.py           CLI：build / check / validate
  scripts/           各类生成器（由 build.py 调用）
  data/              ITM ID 对照表
  requirements.txt
```

## 限制

- `check` 只能判断“重新渲染结果是否与仓库图片一致”，不能判断译文语义是否正确。
- `check`/`build` 需要原版素材；CI 不运行图片生成，release 只会打包仓库中已提交的 PNG。
- 不要把原版游戏素材、EDB、字体或原版 `.exe` 工具提交到本仓库。
