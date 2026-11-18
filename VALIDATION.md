# 1.1.0 验证记录

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
