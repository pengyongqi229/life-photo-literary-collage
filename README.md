# 生活照＋文学手抄 Skill

可移植的本地合成流程。包含 Skill 指令、轻微日系胶片调色、上下/左右/穿页/叠纸及整纸嵌图的 Pillow 引擎、独立重算校验、使用示例和自测。无需 API Key、图像生成模型或网络服务；**查证外部文学出处/版权**时由执行者使用可用的检索渠道。

**安装后只需上传生活照。** Skill 完整接入维护者提供的 **69 张参考素材**，先按照片情绪寻找真实手抄，保留原笔迹、文字、纸纹和落款；没有合适且完整可用的手抄，再查证外部文学片段与作者，制作同审美的手写风排印页。随后轻微胶片调色、合成并复核。使用者无需上传或配置手抄库、寻找字体或指定布局。

**原来的《参考图.zip》完整放在安装包内**，没有改动或删减，包含全部 69 张原参考图。首次使用由 Agent 自动解压到本地，按之前的方式选图、裁取真实手抄并合成。无需使用者另下素材或重新上传。调用者后来上传的生活照不加入安装包。图上署名按原样保留，出处与适用使用依据仍由执行 Agent 核对，详见 [共享素材说明](assets/HANDCOPY-NOTICE.md)。合成引擎的 `examples/demo/` 仍是明确标注的程序测试图，与真实手抄库分开。

[下载完整安装包 ZIP](https://github.com/pengyongqi229/life-photo-literary-collage/archive/refs/heads/main.zip) · [查看最新版代码](https://github.com/pengyongqi229/life-photo-literary-collage) · [四种布局测试预览](examples/layout-preview.png)

**审美仍由执行 Agent 看图复核。** 1.2.1 起，单照片入口会自动生成整张画布的阅读尺寸预览，提示文字过小、纸幅过窄等问题，并明确第一次输出为待审草稿。规则见 [构图与审美复核](references/aesthetic-review.md)。自动测试验证合成、素材完整性与像素保护，不代表已经验证所有宿主中的审美表现。

**这些中间步骤都在内部完成。用户只上传生活照，收到一张完成品。** Agent 负责选文、试排、查看预览、核对与返工，不让用户挑模板或处理检查提示。`finalize.py` 在当前预览和严格内部复核通过后，仅导出一张交付 PNG；`prepare.py` 的 `draft_image` 供内部制作使用。

**1.3.0 新增整页手抄纸面嵌图。** 左文右图、左图右文、上图下文、上文下图均参与自主构图，纸面包围照片、留白连贯。优先使用原纸真实空白；确需延展时，仅从同一原纸无字区域采样并拼接，纹理尺度跟随整纸比例，完整原手抄页与照片原尺寸保留。实现和配方见 [整纸嵌图](references/paper-frame.md)。原有 69 张素材完整保留，私人照片与用户手绘草图不加入分发包。

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

**旧版用户请更新一次完整 Skill。** 1.2.0 起包含完整 69 条参考索引、原始素材压缩包与外部文学补充分支；历史 1.1.0 安装包没有这些素材。

## 日常使用：只上传生活照

在支持 Skill 的 AI 工具里上传照片，说：

> 用这个 Skill，把这张生活照拼成一页文学。

Agent 会观察照片，先从完整 69 张库内素材中选文；没有合适的，再联网查证文学片段与作者并制作手写风排印页。文字与图片的出处核对由 Agent 执行。无需用户填写路径、编号、素材目录或布局；缺文件则由 Agent 修复安装。Python/Pillow 准备属于安装步骤。

Agent 的单照片执行入口（在任意工作目录运行）：

```bash
python /path/to/life-photo-literary-collage/scripts/prepare.py --photo /path/to/photo.jpg --mood 安静,松弛 --out result-work-v1
python /path/to/life-photo-literary-collage/scripts/verify.py result-work-v1/result --assets result-work-v1/assets
```

Agent 先运行 `scripts/library.py --out <工作区素材缓存>` 自动解压，随后用 `scripts/search_library.py --mood 情绪` 检索全部 69 条记录，并查看本地原参考图，按需裁取真实手抄；可用 `--paper-id` 明确选定，或由情绪标签排序。脚本不做视觉情绪识别，也不会把待查证的作者/出处自动标成已核实。像素检查通过后，仍需逐行目视与出处/使用依据复核，填写 `result/review.json`，再加 `--require-review` 运行严格校验。

`prepare.py` 返回的 `preview_image` 是完整、不截边的阅读尺寸预览；原尺寸成图不变。`--layout auto` 只按照片横竖给草稿起点。Agent 须检查预览里的文字、纸幅、留白与情绪，再决定结构。多个工作区草稿可运行 `python scripts/preview.py result-v1 result-v2 --out comparison-v1` 对比；自定义或修改配方后也须重新生成预览。用户不需要自己挑模板。

`--layout auto|vertical|horizontal|overlay|triptych|paper-frame`、`--box 左 上 右 下`、`--axis x|y`、`--split-at`、`--protected-json` 供 Agent 根据构图选择；不需要用户指定。整纸嵌图用 `--frame-file` 读取 Agent 写好的布局；`--resources-file` 配置宿主资源，`--allow-paper-upscale` 仅允许整纸等比放大。`auto` 不会凭空猜测纸张无字区域，Agent 须看实图自主决定。`--no-grade` 关闭调色。完整自定义仍可沿用下方 `compose.py` 配方流程。库内没有合适手抄时，按 [选文规则](references/editorial.md) 查证外部片段，再用 `render_excerpt.py` 及随包字体制作手写风排印页；来源记录模板见 [examples/excerpt-source.template.json](examples/excerpt-source.template.json)。新效果页不能称真实手抄或作者亲笔。

## 默认的轻微胶片调色

默认只对生活照副本做微暖、柔和对比、轻收饱和、轻抬暗部及极淡单色颗粒，保留人物、构图、原尺寸和原有色彩关系。真实手抄不跟着调色。配方示例：

```json
"photo": {
  "image": "photos/photo.jpg",
  "look": {"preset": "japanese-film", "strength": 0.45, "grain": 0.35, "seed": 1729}
}
```

需要完全不改原像素时，将 `look` 改为 `{"preset": "none"}`。调色必然改变颜色像素，因此在工作区保留未调色原照、调色底图与合成验证记录供内部复核，默认用户只收到完成品。细则见 [调色说明](references/photo-look.md)。

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

## 可选：使用自己的手抄素材

此节仅供用户另有自己的手抄时使用；默认只上传生活照并调用共享库即可。自定义目录示意如下：

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
| `paper-surface.png` | 完整纸底；整纸嵌图版保留照片遮盖前的无字纸区与完整原手抄页，用于复核和独立重算 |
| `coverage-mask.png` | 从真实纸层 alpha 导出的二值覆盖遮罩，不是随意指定的免责区域 |
| `manifest.json` | 配方、调色参数/种子/实际差异、相对路径、源哈希、像素哈希、布局和版本 |
| `review.json` | 必须由执行者对照原素材填写的目视/出处版权检查 |
| `verification.json` | 自动检查和目视记录状态 |

验证器用调用者原素材重新生成预期图片，逐像素比较所有输出，并重组照片检查完整覆盖。即使篡改遮罩再更新文件哈希，也不能通过重算像素检查。它不能证明人为填写的配方、转录或复核内容真实，也不提供数字签名防伪。

“原像素”指原文件解码并依 EXIF 方向排列的 8 位 RGBA 采样值。源文件字节不变，`photo-native.png` 保留完整未调色采样。默认的轻微胶片调色会改变 RGB，结果另存 `photo-graded.png`，不重绘、不改构图或尺寸。合成与穿页重组以调色图为基准，叠纸覆盖区外必须零差异；不能将这个零差异说成与未调色原照零差异。显式关闭调色后，调色图也与原照逐像素一致。

输出只显式保留照片的 ICC 色彩配置，不复制源文件的 EXIF/GPS 元数据；这不改变像素值，也不修改源文件。

支持单帧 8 位 RGB、RGBA、灰度和调色板输入；生活照须不透明。CMYK、16 位、动画/多页输入会拒绝，不会静默降位深。HEIC/RAW 需调用者自行提供经确认的兼容导出；不要声称兼容导出与其原始 RAW/HEIC 采样逐像素相同。不同嵌入 ICC 的素材会拒绝；不会对生活照做 ICC 转换。只有一张有 ICC 时，另一张必须由执行者确认数值色彩空间相容。图片和画布默认各限 4000 万像素；1.3.0 可按可用资源明确提高，源图上限 8000 万、画布上限 1.2 亿，并有工作内存预算检查，详见 [资源字段](references/layouts-and-config.md)。不会缩小原照迁就限制。

跨 Pillow 版本的纸张重采样结果可能有差异，严格重算若失败请使用 `manifest.json` 中的生成版本。本包验证环境：Python 3.13.12、Pillow 12.2.0。自动检查不能证明文字没有在上传前就截断，也不能代替逐行目视核对。

## 打包与分享

分享安装包包含 Skill 指令、脚本、模板、测试夹具及维护者提供的原始《参考图.zip》和辅助索引。不要加入调用者的 `my-materials`、生活照、成品、`.venv`、缓存或 API Key，完整保留原参考素材包，不作预先删减。包内代码和文档按 [LICENSE](LICENSE) 授权；共享素材中的文学文本、译文和书写图像不自动适用 MIT，提供记录与核对要求见 [共享素材说明](assets/HANDCOPY-NOTICE.md)。

详细规则：[轻微胶片调色](references/photo-look.md) · [选文与出处](references/editorial.md) · [布局与字段](references/layouts-and-config.md) · [质量检查](references/quality.md)。
