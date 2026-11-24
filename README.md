# RyonaRPG 简体中文翻译

本仓库只维护中文翻译覆盖层、启动脚本和工具，不包含完整游戏本体。

## 对应原版版本

- **日文原版**：Classic Japanese，`core0163`（Japanese maintenance edition based on core0163）。
- 本补丁使用该版本的 `RPG_RT.ldb`；校验哈希见 `compat.json`。
- 英文 Classic 仅作参考：`RyonaRPG-classic-en-a8d5ca191a4c.zip`（2026-09-13，Git `a8d5ca191a4c`，SHA-256 `738919261550ac649f6367b7cac7168f68fed04d21f1d4c33426460404774b3c`），**不是本补丁的基础版本**。
- 当前翻译版本：`0.1.0`。

## 目录

```text
language/zh_CN/      译文源（PO + Meta.ini + Picture 覆盖图）
launcher/            启动中文版的批处理和安装说明
tools/localizer/     本地 PO 编辑器
tools/qa/            提交/发布前自动校验
tools/build_release.py
tools/deploy_to_game.py
docs/                保留日文说明等背景资料
```

## 日常修改

1. 用本地编辑器打开 `tools/localizer`：

```bash
cd tools/localizer
python -m pip install -r requirements.txt
python app.py
```

浏览器打开 `http://127.0.0.1:5010/`。默认读取本仓库的 `language/zh_CN`，可通过 `RYONA_LANG_DIR` 指向游戏目录。

2. 只修改 `language/zh_CN/*.po` 的 `msgstr`，不要直接改 LDB/LMU/LMT。
3. 保存后运行校验：

```bash
python tools/qa/run_all.py
```

4. 提交前查看 `git diff`；图片变化单独检查 `language/zh_CN/Picture`。

## 发布

打 `v*` 标签后，GitHub Actions 会运行 QA 并生成：

```text
RyonaRPG-zh_CN-vX.Y.Z.zip
├─ 启动中文版.bat
├─ 安装说明.txt
├─ compat.json
└─ language/zh_CN/...
```

也可以本地构建：

```bash
python tools/build_release.py
```

产物在 `dist/`，不进入 Git。

## 其他使用者如何配置游戏本体

仓库不包含游戏本体。使用者需要自行安装 RyonaRPG 2026 日本語版（含 `EasyRPG Player.exe`、`RPG_RT.ldb` 等），然后任选一种方式：

**方式 A：直接使用 release**

下载 release 中的 `RyonaRPG-zh_CN-vX.Y.Z.zip`，解压到游戏根目录，双击“启动中文版.bat”。

**方式 B：从仓库部署**

克隆仓库后，把整个仓库的 `language/zh_CN` 复制到游戏根目录的 `language/zh_CN`，或使用部署脚本（会先备份现有翻译）：

```bash
python tools/deploy_to_game.py --game-dir "D:\Games\RyonaRPG" --with-launcher
```

`--game-dir` 必须指向包含 `RPG_RT.ldb` 的游戏根目录。`compat.json` 记录了当前兼容的 `RPG_RT.ldb` 哈希；哈希不一致时脚本会警告。

**只做翻译/编辑**

不需要游戏本体：`tools/localizer` 默认读取仓库 `language/zh_CN`。需要实机预览时，再用上面的部署脚本或把仓库 `language/zh_CN` 复制到游戏目录。

**图片重生成**

需要游戏本体的 `Picture/Menu` 模板和 LDB。当前生成的覆盖图已经随仓库提交，常规文字修改不需要重新生成图片；修改道具/技能/ABL/EX 名称或说明时才需要。

## 注意

- 游戏本体、LDB/LMU/LMT、音频、原始图片和 EasyRPG Player 二进制不属于本仓库；用户需自备游戏。
- 本仓库的 `Picture` 是中文覆盖图，不是完整游戏素材。
- 修改道具/技能/ABL/EX 名称或说明后，仍需要对应的图片生成流程；生成图应与 PO 同步提交或在发布前生成。图片生成脚本依赖原游戏图片模板，默认不随仓库分发，避免把游戏素材纳入 Git。
