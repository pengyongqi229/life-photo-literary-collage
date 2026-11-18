# 1.0.1 验证记录

验证日期：2026-11-18。环境：Python 3.13.12、Pillow 12.2.0。所有测试只使用程序绘制的非私人测试场景和印刷测试页，不包含调用者的生活照、手抄或参考图库。测试页不是文学原作，也不是真实手写素材。1.0.1 补充 GitHub 安装和下载说明，合成引擎保持 1.0.0。

- Skill 结构和 frontmatter 校验通过。
- `scripts/self_test.py` 的 **30 项测试全部通过**，含四种布局、上下/左右变体、纵向穿页、EXIF 无损方向映射、中文素材路径、源文件不变、透明打孔和原边缘保留。
- 拒绝或检出：漏署名、正文框越界、纸张容器越界、最小字高不足、主体受挡、分割线穿过主体、目录越界/符号链接越界、覆盖已有目录、版权证据缺失、CMYK/透明生活照、ICC 冲突。
- 篡改测试通过：成品像素或遮罩被修改，即使重写文件哈希仍会在重新合成比较时失败；RGB 改动不会因 alpha 不变而漏检。源文件变化、输出 ICC 变化、旧成功报告遗留也有测试。
- 目视复核门槛已测试：自动通过而未完成逐字/出处复核时，`delivery_ready` 为 `false`，严格命令失败；不会把“框在图内”当作文字识别证明。
- 四份配方经命令行实际生成并独立验证，三个拼接结构的 1,152,000 个生活照测试像素全部不变；叠纸结构的完整照片底层可重组为 0 差异，覆盖区以外 0 差异。
- 已对照两张完整测试纸页及四种输出目视检查：测试文本、标点、署名、打孔、纸张纹理和边缘保留，叠纸能透景且纸张仍可辨。记录只适用于这些合成夹具，不表示任何真实文学作品的出处和版权已获核实。
- 已执行 ZIP 解压后的独立目录运行检查，使用随包示例、相对路径和中文结果目录验证，不依赖原工作区路径。

机器可读结果：[examples/validation-results.json](examples/validation-results.json)。测试日志：[examples/self-test.log](examples/self-test.log)。布局预览：[examples/layout-preview.png](examples/layout-preview.png)。

## 自行复现

在已安装依赖的 Skill 目录运行：

```bash
python scripts/self_test.py
python scripts/compose.py examples/demo/recipes/overlay.json --assets examples/demo/assets --out my-test-result
python scripts/verify.py my-test-result --assets examples/demo/assets
```

第二条应返回 `automatic_pass: true` 与 `delivery_ready: false`；这是正确状态。真实任务仍须执行者对照自己的原素材完成 `review.json`，再用 `--require-review` 检查。不能将包内测试的已复核结果套用到新素材。
