# 布局与配方字段

所有路径相对 `--assets`，解析后不可越出该目录，符号链接也受此限制。配置为 UTF-8 JSON，不含注释。像素坐标按 EXIF 显示方向；矩形为 `[左, 上, 右, 下]`，右、下不包含端点。照片原尺寸不可调整，输出比例通过扩展画布解决；默认先进行轻微胶片调色，见 [photo-look.md](photo-look.md)。

## 构图结构

| `layout.type` | 适用场景 | 字段 |
| --- | --- | --- |
| `vertical` | 横向场景需要完整呈现，整纸适合横向阅读 | `panel_size` 新增栏高；`paper_side` 为 `before`（纸在上）/`after`（纸在下）；`gap` |
| `horizontal` | 竖照、视线指向侧边，或纸与照片适合并列 | `panel_size` 新增栏宽；`paper_side` 为 `before`（纸在左）/`after`（纸在右）；`gap` |
| `triptych` | 中间插入完整纸张，照片场景从两侧/上下穿过 | `axis` 为 `x`（左/纸/右）或 `y`（上/纸/下）；`split_at` 为原照分割坐标；`panel_size` 插页宽/高；`gap` 在两条接缝各占一次 |
| `overlay` | 天空、墙面等留白足以容纳一整张可辨的纸 | `box` 为照片内纸张容器；`gap` 必须为 0；原画布尺寸不变 |
| `paper-frame` | 照片嵌入整页真实手抄纸面，纸边包围照片，留白连贯 | `mode: embed/extend`、`canvas_size`、`photo_xy`、`paper_xy`、`photo_side: left/right/top/bottom`、`border`；详见 [整纸嵌图配方](paper-frame.md) |

`margin` 是容器内部留白；非文字边框。纸整页 contain 适配并居中，不拉伸、不铺满裁切。请避免狭窄容器硬塞横向长文，或宽栏只放几个大字。构图不协调时换素材/结构，不拆行、剪掉署名或新增装饰。穿页分割线不得切过脸、手、花束等主体，`protected_regions` 可阻止切线穿过已标出的主体框。

`paper-frame` 使用明确的整纸与照片坐标，不采用分栏 contain 容器。它支持左文右图、左图右文、上图下文、上文下图；必须看得出纸面包围照片。真实留白足够时直接嵌图，不足时仅允许从同一原纸的无字纹理区域做传统像素采样/拼接延展，整张原手抄页保留。不能覆盖文字、复制文字区、从旧场景边缘拉长色带或新增草图描边。

## 必需字段

| 字段 | 内容 |
| --- | --- |
| `schema_version` | 整数 `1` |
| `photo.image` | 生活照的相对路径 |
| `photo.look` | 可选；默认 `japanese-film`、强度 0.45、颗粒 0.35、种子 1729；原像素零变化要求使用 `{"preset":"none"}` |
| `photo.protected_regions` | 可选的主体矩形数组，建议标出所有不可遮挡/分割的主体；叠纸相交或穿页切线穿过会报错 |
| `paper.image` | 已完整保留纸张轮廓的手抄图；无自动抠纸或透视处理 |
| `paper.asset_kind` | 实际作品填 `real-handcopy`；非私人夹具只能填 `synthetic-test` |
| `paper.expected_transcript` | 完整正文、标点、换行和署名，不得仅填标题或节选 |
| `paper.regions` | 至少一个 `text` 和一个 `signature`，各包含 `box`；可标多块正文 |
| `paper.smallest_character_px` | 在原纸图上量取的最小字高，含署名；不是整段文字框高度 |
| `paper.rights.basis` | `user-original` / `permission` / `public-domain` / `licensed`；测试专用 `synthetic-test` |
| `paper.rights.evidence` | 非空证据摘要；可另加 `record_file` 指向详细来源记录，但工具不会自动读取或裁定它 |
| `layout` | 上表对应结构；`panel_size`/`box` 等适用字段为必需 |

## 可调字段与限制

- `background`：画布留白 RGB，默认 `[240,235,221]`；不会用此颜色替换原手抄纸纹。
- `paper.opacity`：叠纸默认 `0.55`，表示 55% 不透明；脚本允许 `0.01–1`，数值有效不等于审美合格，纸色/边缘是否可辨必须目视检查。可先在约 0.45–0.65 试起，根据实图决定，不固化为所有照片的标准。
- `paper.ink_opacity`：叠纸默认 `0.96`，须不小于纸张不透明度。引擎依据亮度连续提高深色区域 alpha，保留原 RGB、纹理和源 alpha，不二值抠字、不移除浅字。旧纸污痕也可能因此加深，需目视检查。分栏/穿页两项必须均为 `1`，默认即 `1`。
- 透明度曲线为 `paper_alpha × [opacity + (ink_opacity-opacity) × (1-luminance/255)^2]`，没有边缘渐隐。原图中的透明打孔仍为透明。
- `paper.minimum_character_px`：默认合成后最小字高 `12`，允许 `8–200`，只作机械下限。按真实观看尺寸提高标准；不能为绕过报错随意降低。最小字高由执行者测量，脚本不会 OCR 测字。
- `paper.allow_upscale`：默认 `false`；需要放大整页时显式设为 `true` 并复查清晰度，放大不能修复低清笔画。生活照不提供放大选项。
- 分栏/穿页画布可变大，照片必须按整数位置原尺寸粘贴。三段结构的左右/上下是同一张照片互补的两个区块，不复制整张照片。
- `resources` 可按宿主资源明确配置：`max_source_pixels` 默认 4000 万、上限 8000 万；`max_canvas_pixels` 默认 4000 万、上限 1.2 亿；`max_working_memory_mb` 默认 4096、上限 32768。合成前做保守内存估算并拒绝超过预算的画布，不会自动缩小原照。大照片示例：`{"resources":{"max_source_pixels":60000000,"max_canvas_pixels":80000000,"max_working_memory_mb":8192}}`，须确认宿主有相应可用内存，数值预算不保证操作系统一定分配成功。验证采用逐文件比较，避免同时保留两套大画布。
- 目前不提供纸张旋转、透视变换、文字提取、分层重排、自动语义选文或自动版权判定。需要这些处理时先准备完整可用素材，不能以生成式补全代替。
