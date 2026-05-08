# Business Overview Deck

本目录保存权签票据一致性 AI 预审方案的业务汇报材料。

## 输出文件

- `output/bill_verification_business_overview.pptx`：图片版 PPT，每页由 PNG 预览图铺底，适合快速浏览和转发。
- `output/bill_verification_business_overview_editable.pptx`：原生可编辑 PPT，文本、灰线表格、流程框、结论区均为 PowerPoint 可编辑对象。
- `output/bill_verification_business_overview_editable_summary.json`：可编辑 PPT 的对象统计和生成说明。
- `previews/*.png`：图片版逐页预览和 montage 总览图。

## 生成脚本

- `src/build_business_deck.py`：生成图片版 PPT 和 PNG 预览。
- `src/build_business_deck_editable.py`：生成原生可编辑 PPT。

## 风格原则

当前材料遵循跨项目风格规范：

`C:\Users\61588\.openclaw\shared\steering\PPT_STYLE_HUAWEI.md`

默认口径：

- 华为内部汇报 / 麦肯锡式结构化业务汇报风格。
- 白底，蓝灰主色，橙色只用于关键结论。
- 每页包含观点化标题、核心判断、主体结构、关键结论。
- 优先使用可编辑文本框、形状、线条和表格单元，不使用整页图片作为正式可编辑版。
