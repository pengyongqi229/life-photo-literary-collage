# 1.2.0 验证记录

验证日期：2026-11-18。环境：Python 3.13.12、Pillow 12.2.0。

1.2.0 增加随包共享手抄库与 `prepare.py` 单照片入口。用户不需上传或配置手抄素材库。原《参考图.zip》完整随包分发，69 张原图自动解压后全部进入本地检索，选中后再裁取真实手抄，不预先删减。

- 原合成/调色引擎 39 项自测通过，验证原照保留、四种结构、关闭调色、固定颗粒种子、整页/打孔保留及像素篡改检测。
- 新增 5 项单照片流程测试通过：69 条索引和文件哈希检查、9 页手工转录样本合成与独立重算；其余 OCR/问题页未经复核时拒绝直接合成；四种结构与关闭调色；情绪选择与明确选页；素材损坏时拒绝；目录存在时不覆盖。未经目视/出处复核时严格交付检查仍拒绝。
- 原素材 ZIP 与维护者提供文件字节完全相同；全部 69 张解压图片与 ZIP 内成员 SHA-256 一致。按需裁取纸区为无损像素搬移，没有重绘、JPEG 重压缩、补字、抠墨或擦除。
- ZIP 解压后在独立目录仅传一张照片，使用随包手抄生成配方、合成并校验，不依赖原参考 ZIP 或维护者本机目录。
- 外部片段补充分支新增 3 项测试通过：无出处证据时拒绝、换行不丢字、手写风效果明确标注后可完整合成并保留照片。
- Skill frontmatter 与相对文档链接检查通过。安装包排除缓存、虚拟环境、私有运行结果、维护者路径和原始参考成品。

自动测试证明文件、几何和像素行为，不证明文学归属、原作版权、转录或审美已全部核实。共享索引明确记录出处待核实；真实交付仍须查证、逐字与目视复核，不可自动勾选 `review.json`。

```bash
python scripts/self_test.py
python scripts/library_test.py
python scripts/fallback_test.py
python scripts/prepare.py --photo /path/to/photo.jpg --mood 日常,松弛 --out my-work-v1
python scripts/verify.py my-work-v1/result --assets my-work-v1/assets
```

目视/出处复核完成后才加 `--require-review`。旧版用户须更新一次完整 Skill，才能取得共享素材与单照片入口。

## 历史记录：1.1.0

以下仅记录 1.1.0 的测试范围；其中“不含真实手抄图库”不描述当前安装包。

验证日期：2026-11-18。环境：Python 3.13.12、Pillow 12.2.0。测试素材为程序绘制的非私人场景和印刷测试页，不含真实手抄图库或私人照片。1.1.0 增加默认的轻微日系胶片调色，并保留显式关闭选项。

- Skill 结构和 frontmatter 校验通过，39 项自测全部通过。
- 验证四种布局、上下/左右变体、纵向穿页、EXIF 方向、中文路径、源文件不变、完整纸页、透明打孔、主体保护和覆盖范围。
- 未调色原照保持源图解码像素；调色副本保持原尺寸与构图。关闭调色或强度为 0 时，副本与原照逐像素一致。
- 默认调色经过离散 RGB 色块检查：通道变化不超过 16 个 8 位等级；黄/蓝色块保留色彩次序和至少 85% 的原色差，白色不低于 250，黑位仅轻抬。该检查不代替真实照片的肤色、氛围和亮部目视复核。
- 颗粒固定种子可复现，为极轻微单色噪点；在整幅照片上生成后再分割，重组与合成校验均以 `photo-graded.png` 为基准。调色原本就会改变 RGB，报告明确记录相对原照的真实差异。
- 同一配方开关照片调色时，手抄合成层逐像素相同，不会误调纸张、笔迹或署名。
- 篡改成品、调色底图、遮罩、源文件、ICC 或调色记录可被重算检查检出；改写文件哈希不能绕过预期像素比较。
- 目视复核新增 `photo_look_natural`。未逐项确认时，严格验证不通过，不会把自动像素检查冒充文字/版权/审美认证。
- 四份示例配方均已命令行生成并严格复核；ZIP 解压后合成与验证运行通过，结果仍正确保持“自动通过、待目视复核”。

机器结果：[examples/validation-results.json](examples/validation-results.json)。测试日志：[examples/self-test.log](examples/self-test.log)。预览：[examples/layout-preview.png](examples/layout-preview.png)。

```bash
python scripts/self_test.py
python scripts/compose.py examples/demo/recipes/overlay.json --assets examples/demo/assets --out my-test-result
python scripts/verify.py my-test-result --assets examples/demo/assets
```

真实任务需对照自己的原素材完成 `review.json`，再运行 `--require-review`。新引擎不会验证旧引擎生成的包；历史结果请使用相应 GitHub 版本的验证器。
