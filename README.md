# 生活照＋文学手抄 Skill

可移植的本地合成流程。包含 Skill 指令、轻微日系胶片调色、四种布局的 Pillow 引擎、独立重算校验、使用示例和自测。无需 API Key、图像生成模型或网络服务；**查证外部文学出处/版权**时由执行者使用可用的检索渠道。

本项目不附带任何私人照片或真实手抄图库，使用者自带素材。示例图完全由脚本绘制，标为测试图，不是真实生活照、真实手抄或文学摘句。包内测试图不是审美参考图库。

[下载完整安装包 ZIP](https://github.com/pengyongqi229/life-photo-literary-collage/archive/refs/tags/v1.1.0.zip) · [查看发布版本](https://github.com/pengyongqi229/life-photo-literary-collage/releases) · [四种布局测试预览](examples/layout-preview.png)

## 从 GitHub 安装

仓库地址：<https://github.com/pengyongqi229/life-photo-literary-collage>。

**在 Codex 中安装：** 把下面这句话发给 Codex，由它从公开仓库安装：

> 使用 $skill-installer，从 https://github.com/pengyongqi229/life-photo-literary-collage 安装 life-photo-literary-collage，并按 README 准备 Python 和 Pillow。

**跨工具安装：** 若已安装 Node.js 22.20 或更新版本，可使用 [skills CLI](https://github.com/vercel-labs/skills)，按提示选择 Codex、Claude Code 等支持的工具：

```bash
npx skills add pengyongqi229/life-photo-literary-collage --skill life-photo-literary-collage -g
```

该命令安装 Skill 文件，不会自动配置本项目的 Python/Pillow 环境。Skill 本体不需要 Node.js；只有使用此安装命令时需要。

## 安装

1. 下载并解压 ZIP，将解压得到的文件夹重命名为 `life-photo-literary-collage`（GitHub 的下载文件夹名可能带版本号后缀）。
2. Codex 当前版本可将整个文件夹放进 `~/.agents/skills/`；若使用 `$skill-installer`，以安装器实际报告的位置为准（部分版本使用 `~/.codex/skills/`）。Claude Code 用户可放进 `~/.claude/skills/`。保留整个文件夹结构；若当前会话未发现新 Skill，开启新会话后调用。安装目录参考 [Codex 官方文档](https://learn.chatgpt.com/docs/build-skills) 和 [Claude Code 官方文档](https://code.claude.com/docs/en/skills)。
3. 使用 Python 3.10 或更新版本创建独立环境并安装依赖。下面命令在 **Skill 文件夹**内执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows 对应使用 `py -3 -m venv .venv` 和 `.venv\Scripts\python.exe -m pip install -r requirements.txt`。后续的 `python` 均指此环境的解释器；也可先激活环境再执行。

在其他支持目录式 Skill 的 Agent 中，把整个文件夹放入其技能目录；不支持 Skill 发现时可直接读 `SKILL.md` 并运行脚本。工具不依赖 Codex 专用 API。

## 默认的轻微胶片调色

默认只对生活照副本做微暖、柔和对比、轻收饱和、轻抬暗部及极淡单色颗粒，保留人物、构图、原尺寸和原有色彩关系。真实手抄不跟着调色。配方示例：

```json
"photo": {
  "image": "photos/photo.jpg",
  "look": {"preset": "japanese-film", "strength": 0.45, "grain": 0.35, "seed": 1729}
}
```

需要完全不改原像素时，将 `look` 改为 `{"preset": "none"}`。调色必然改变颜色像素，因此同时提供未调色原照、调色底图与合成验证记录。细则见 [调色说明](references/photo-look.md)。

## 先跑一个无需私人素材的示例

以下路径相对当前 Skill 文件夹；`demo-work` 和 `demo-results` 必须是尚不存在的新目录：

```bash
python scripts/make_demo.py --out demo-work
python scripts/compose.py demo-work/recipes/overlay.json --assets demo-work/assets --out demo-results
python scripts/verify.py demo-results --assets demo-work/assets
python scripts/self_test.py
```

生成器还提供 `vertical.json`、`horizontal.json`、`triptych.json`。替换配方名并使用新的结果目录即可运行。查看 `demo-results/final.png`，同时对照 `demo-work/assets/handcopies/landscape.png`；目视核对后填写 `review.json`，再执行：

```bash
python scripts/verify.py demo-results --assets demo-work/assets --require-review
```

生成后自动校验即会执行，但目视检查默认全为 `false`。没有完成逐项复核时，`delivery_ready` 为 `false`。测试样本的版权项只表示原创合成测试素材，不代表任何真实文学作品已获授权。

包内已附可直接运行的 `examples/demo/` 素材和四份配方，以及 [四种布局测试预览](examples/layout-preview.png)。可跳过生成器，直接将合成命令的配方路径改为 `examples/demo/recipes/overlay.json`、素材路径改为 `examples/demo/assets`。版本验证记录见 [VALIDATION.md](VALIDATION.md)。

## 使用自己的素材

自行创建素材目录，示意如下（文件名可自由更改）：

```text
my-materials/
  photos/photo.jpg
  handcopies/page.png
  catalog.json              可选的选文索引
recipe.json
```

复制 [examples/recipe.template.json](examples/recipe.template.json) 到自己的工作区，按真实图片改路径、布局、尺寸、完整转录、正文/署名框、最小字高及权限证据。模板的坐标仅演示字段，不可不核对就用于真实素材。索引格式见 [examples/catalog.template.json](examples/catalog.template.json)。索引只帮助选择素材，不会自动证明作者或授权。

对 Agent 的示例请求：

> 使用 $life-photo-literary-collage。素材目录是我提供的目录，生活照在 photos/photo.jpg，手抄在 handcopies/。先按照片情绪选一张完整真实手抄，保留所有字、标点、署名和纸纹。请自主选择克制布局，不加印章票根，默认做轻微日系胶片调色，保留未调色原照，核对调色底图与合成像素及文字完整性，最终只展示一张 PNG。

```bash
python /path/to/life-photo-literary-collage/scripts/compose.py recipe.json --assets /path/to/my-materials --out result-v1
python /path/to/life-photo-literary-collage/scripts/verify.py result-v1 --assets /path/to/my-materials --require-review
```

第二条须在对照原素材完成 `result-v1/review.json` 后运行。输出目录存在时会拒绝覆盖；修订用 `result-v2` 等新目录。

## 输出内容与可信范围

| 文件 | 用途 |
| --- | --- |
| `final.png` | 无损 RGBA PNG 合成图 |
| `photo-native.png` | EXIF 显示方向、原尺寸、完整未改像素的照片底层 |
| `photo-graded.png` | 原尺寸完整调色照片；关闭调色时与原照像素一致 |
| `photo-base.png` | 画布中的调色照片底层，穿页布局可完整重组 |
| `paper-layer.png` | 整张纸的 RGBA 合成层，可还原覆盖范围 |
| `coverage-mask.png` | 从真实纸层 alpha 导出的二值覆盖遮罩，不是随意指定的免责区域 |
| `manifest.json` | 配方、调色参数/种子/实际差异、相对路径、源哈希、像素哈希、布局和版本 |
| `review.json` | 必须由执行者对照原素材填写的目视/出处版权检查 |
| `verification.json` | 自动检查和目视记录状态 |

验证器用调用者原素材重新生成预期图片，逐像素比较所有输出，并重组照片检查完整覆盖。即使篡改遮罩再更新文件哈希，也不能通过重算像素检查。它不能证明人为填写的配方、转录或复核内容真实，也不提供数字签名防伪。

“原像素”指原文件解码并依 EXIF 方向排列的 8 位 RGBA 采样值。源文件字节不变，`photo-native.png` 保留完整未调色采样。默认的轻微胶片调色会改变 RGB，结果另存 `photo-graded.png`，不重绘、不改构图或尺寸。合成与穿页重组以调色图为基准，叠纸覆盖区外必须零差异；不能将这个零差异说成与未调色原照零差异。显式关闭调色后，调色图也与原照逐像素一致。

输出只显式保留照片的 ICC 色彩配置，不复制源文件的 EXIF/GPS 元数据；这不改变像素值，也不修改源文件。

支持单帧 8 位 RGB、RGBA、灰度和调色板输入；生活照须不透明。CMYK、16 位、动画/多页输入会拒绝，不会静默降位深。HEIC/RAW 需调用者自行提供经确认的兼容导出；不要声称兼容导出与其原始 RAW/HEIC 采样逐像素相同。不同嵌入 ICC 的素材会拒绝；不会对生活照做 ICC 转换。只有一张有 ICC 时，另一张必须由执行者确认数值色彩空间相容。图片和画布各限 4000 万像素，内存占用可能较高。

跨 Pillow 版本的纸张重采样结果可能有差异，严格重算若失败请使用 `manifest.json` 中的生成版本。本包验证环境：Python 3.13.12、Pillow 12.2.0。自动检查不能证明文字没有在上传前就截断，也不能代替逐行目视核对。

## 打包与分享

分享安装包时只包含 Skill 指令、脚本、模板和非私人测试素材。不要把自己的 `my-materials`、成品、`.venv`、缓存、API Key 或真实文学扫描件一起打包。包内代码和文档按 [LICENSE](LICENSE) 授权；不授予任何调用者输入素材、文学文本、译文或手抄图像的权利。

详细规则：[轻微胶片调色](references/photo-look.md) · [选文与出处](references/editorial.md) · [布局与字段](references/layouts-and-config.md) · [质量检查](references/quality.md)。
