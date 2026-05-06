# 权签票据一致性 AI 预审 Demo 技术方案

## 1. Demo 目标

Demo 的目标不是一次性建设完整生产系统，而是围绕公司内部可访问的多模态大模型接口，快速验证以下问题：

- 大模型能否从真实或模拟票据中提取关键字段。
- 大模型能否给出票面字段到 MAP/AP 标准字段的归一结果。
- 系统值与票面值的差异能否被清晰展示。
- 权签人是否能基于 AI 结果更快定位风险。
- 人工反馈能否被沉淀为下一次优化的配置或样本。

当前假设公司内已有可访问的多模态大模型接口，模型暂按“Qwen3.5 35B A3B”类接口处理。实际名称、上下文长度、图片输入格式、并发限制和输出稳定性需要在接入前确认。

## 2. Demo 范围

### 2.1 输入

- 一张或多张票据图片。
- 可选 PDF，Demo 阶段可以先转图片后处理。
- 一份模拟 MAP/AP 系统支付指令 JSON。

示例系统指令：

```json
{
  "payment_id": "PAY-2026-0001",
  "payer_name": "Example Trading Co., Ltd.",
  "payer_account": "123456789012",
  "payer_bank": "Industrial and Commercial Bank of China",
  "beneficiary_name": "Global Supplier Limited",
  "beneficiary_account": "987654321000",
  "beneficiary_bank": "ABC Bank Hong Kong",
  "currency": "USD",
  "amount": "12500.00",
  "payment_date": "2026-05-06",
  "purpose": "Invoice payment"
}
```

### 2.2 输出

- 票面结构化字段。
- 字段归一结果。
- 系统值与票面值对比表。
- 风险等级。
- 差异说明。
- 票面证据位置，如页码、区域、原文片段。
- 人工反馈入口。

## 3. Demo 架构

```mermaid
flowchart LR
    A["上传票据图片/PDF"] --> B["文件预处理"]
    C["MAP/AP 模拟 JSON"] --> D["核验编排服务"]
    B --> D
    D --> E["多模态大模型接口"]
    E --> F["结构化结果校验"]
    F --> G["字段归一与比对"]
    G --> H["Demo 前端展示"]
    H --> I["人工反馈记录"]
```

## 4. 推荐技术组件

### 4.1 前端

建议使用轻量 Web Demo：

- React + Vite。
- TypeScript。
- Tailwind CSS 或普通 CSS。
- PDF/图片预览组件。
- 表格展示核验结果。

页面建议包括：

- 左侧：票据图片预览。
- 右侧上方：系统支付指令。
- 右侧中部：AI 提取字段。
- 右侧下方：一致性风险列表。
- 支持点击风险项后在票据图片上高亮证据区域。

### 4.2 后端

建议使用 Python FastAPI，原因是：

- 适合快速封装 AI 接口。
- 方便处理图片、PDF、JSON Schema 校验。
- 方便后续接入 OCR、向量检索、规则引擎。

后端模块：

- 文件上传接口。
- PDF 转图片接口。
- 多模态模型调用封装。
- Prompt 模板管理。
- JSON 结果解析和校验。
- 字段归一服务。
- 比对服务。
- 反馈记录服务。

后端环境建议参考同类项目 `contract_handle` 的做法，使用项目内 `.venv` 管理依赖：

- `.venv/` 只保存在本地，不提交到 Git。
- 后端依赖写入仓库根目录 `requirements.txt`。
- Windows 环境使用 `start_demo.bat` 创建虚拟环境、安装依赖并启动服务。
- 安装依赖时显式使用 `.venv\Scripts\python.exe -m pip install -r requirements.txt`，避免依赖进入全局 Python 环境。

### 4.3 数据存储

Demo 阶段可以先用本地文件或 SQLite：

- `samples/`：样例票据图片。
- `data/payment_instructions/`：模拟系统支付指令。
- `data/results/`：AI 提取结果。
- `data/feedback/`：人工反馈。
- `config/field_schema.json`：标准字段 Schema。
- `config/field_aliases.json`：字段别名。
- `config/rules.json`：比对规则。

如果后续接近生产，可替换为数据库和配置中心。

## 5. 多模态大模型调用策略

### 5.1 两阶段调用

建议不要一次性让模型完成所有事情。Demo 可以采用两阶段：

1. 票面结构化提取  
   输入票据图片，让模型输出原始字段、候选值、原文片段、位置描述和置信度。

2. 字段归一与风险判断  
   输入第一步结果 + MAP/AP 系统 JSON + 字段 Schema，让模型辅助归一和解释差异。

其中最终一致性判断建议由规则代码完成，模型主要负责提取、归一和解释。这样结果更可控。

### 5.2 模型输出格式

要求模型严格输出 JSON，后端使用 JSON Schema 校验。

示例输出：

```json
{
  "document_type": "remittance_application",
  "language": ["en", "zh"],
  "extracted_fields": [
    {
      "raw_label": "Beneficiary",
      "raw_value": "Global Supplier Limited",
      "normalized_field": "beneficiary_name",
      "confidence": 0.93,
      "evidence": {
        "page": 1,
        "text": "Beneficiary: Global Supplier Limited",
        "region_hint": "middle-left"
      }
    }
  ],
  "special_risks": [
    {
      "type": "non_transferable",
      "text": "A/C Payee Only",
      "confidence": 0.88,
      "evidence": {
        "page": 1,
        "region_hint": "top-right"
      }
    }
  ]
}
```

### 5.3 Prompt 设计要点

Prompt 应强调：

- 只提取票面能看到的信息，不要补全或猜测。
- 不确定时输出候选值和低置信度。
- 保留原文片段。
- 输出标准 JSON。
- 字段归一必须说明依据。
- 区分“票面未出现”和“模型无法识别”。

## 6. 字段归一与比对设计

### 6.1 标准字段 Schema

Demo 阶段可以定义一个简单 Schema：

```json
{
  "beneficiary_name": {
    "display_name": "收款方名称",
    "risk_level": "high",
    "compare_type": "normalized_text",
    "required": true
  },
  "beneficiary_account": {
    "display_name": "收款方账号",
    "risk_level": "high",
    "compare_type": "exact_account",
    "required": true
  },
  "amount": {
    "display_name": "金额",
    "risk_level": "high",
    "compare_type": "decimal_amount",
    "required": true
  },
  "currency": {
    "display_name": "币种",
    "risk_level": "high",
    "compare_type": "currency_code",
    "required": true
  }
}
```

### 6.2 比对规则

Demo 阶段先实现几类规则：

- 金额：去掉千分位、统一小数位后比较。
- 币种：USD、US Dollar、美元归一后比较。
- 账号：去掉空格、短横线后精确比较。
- 名称：大小写、空格、标点归一后比较，并可加入相似度。
- 日期：统一日期格式后比较。
- 缺失：系统有值但票面无对应字段时提示。
- 特殊字段：票面出现特殊条款时提示，不一定参与一致性比对。

### 6.3 风险结果结构

```json
{
  "field": "amount",
  "display_name": "金额",
  "risk_level": "high",
  "status": "mismatch",
  "system_value": "12500.00",
  "document_value": "15200.00",
  "message": "票面金额与系统支付金额不一致",
  "confidence": 0.95,
  "evidence": {
    "page": 1,
    "text": "Amount: USD 15,200.00",
    "region_hint": "middle-right"
  }
}
```

## 7. Demo 页面设计

### 7.1 页面布局

- 顶部：任务编号、文档类型、总体风险状态。
- 左侧：票据图片预览。
- 右侧：核验结果面板。
- 结果面板分为高风险、中风险、低风险、已一致。
- 每个字段展示系统值、票面值、状态、置信度和证据。

### 7.2 交互

- 点击风险项，高亮票面证据区域。
- 支持人工标记：AI 正确、AI 识别错误、业务确认不一致、忽略。
- 支持查看模型原始 JSON。
- 支持重新发起识别。
- 支持切换不同样例票据。

## 8. Demo 目录建议

```text
bill_verification/
  docs/
    bill-verification-product-solution.md
    demo-technical-solution.md
  demo/
    backend/
      app/
        main.py
        model_client.py
        extractor.py
        comparator.py
        schemas.py
      requirements.txt
    frontend/
      src/
      package.json
    config/
      field_schema.json
      field_aliases.json
      rules.json
    samples/
      documents/
      payment_instructions/
      expected_results/
```

## 9. Demo 实施步骤

### 第一步：静态样例闭环

- 准备 3-5 张票据样例。
- 准备对应 MAP/AP 系统 JSON。
- 人工准备一份 expected result。
- 前端先读取静态 JSON 展示完整核验页面。

目标：验证产品展示和权签交互是否清晰。

### 第二步：接入多模态模型

- 后端封装内部多模态模型接口。
- 将票据图片传给模型。
- 要求模型输出结构化 JSON。
- 对模型输出做 Schema 校验和容错。

目标：验证模型对真实票面的提取能力。

### 第三步：规则比对

- 实现金额、币种、账号、名称、日期等基础比对规则。
- 由代码生成风险结果。
- 模型只负责提取和归一，尽量不让模型直接决定最终一致性。

目标：提升结果稳定性和可解释性。

### 第四步：反馈闭环

- 前端支持人工修正和标记。
- 后端保存反馈样本。
- 基于反馈生成字段别名或模板规则建议。

目标：验证后续无发版优化的产品形态。

## 10. 需要确认的问题

接入内部多模态接口前，需要确认：

- 模型接口协议：OpenAI-compatible、HTTP JSON、自定义网关或 SDK。
- 图片输入方式：base64、文件 URL、multipart upload。
- 是否支持多图输入。
- 单次最大图片大小。
- 上下文长度。
- 是否支持 JSON mode 或结构化输出约束。
- 并发、限流、超时和费用口径。
- 是否允许票据数据进入该模型服务。
- 是否需要脱敏或内网隔离。

## 11. Demo 成功标准

Demo 可以认为成功，如果它能做到：

- 对 3-5 张样例票据完成关键字段提取。
- 能展示系统值与票面值的清晰对比。
- 能正确暴露至少几类典型风险，例如金额不一致、账号不一致、币种缺失。
- 权签人能看懂 AI 为什么提示风险。
- 人工反馈能被记录，并能说明未来如何变成配置或优化样本。

## 12. 配置和 AI 语义映射的组合方式

Demo 中需要体现两类映射能力的组合：

1. AI 天然语义映射  
   多模态模型根据票面文字、字段上下文和语言语义，直接给出 `normalized_field`。

2. MAP 配置映射  
   MAP 或配置页面维护字段 Schema、字段别名、模板区域提示和比对规则。

组合逻辑建议为：

- AI 输出候选字段和值。
- 后端读取字段 Schema，决定哪些字段参与比对、风险等级是什么、使用什么比对方式。
- 后端读取字段别名和模板规则，作为后续 prompt、候选重排和人工优化依据。
- 第一版 Demo 先展示配置如何影响比对和展示，不做复杂自动学习。
- 后续生产方案中，MAP 管理业务字段和比对口径，AI 产品管理票面提取和候选字段，双方通过统一 Schema 对接。

这可以回答业务最关心的问题：即使 AI 有天然语义理解，业务仍然可以通过配置来约束字段范围、风险等级、比对规则和特殊提示。

## 13. 当前 Demo 与真实模型的关系

当前 Demo 页面默认采用“预置识别结果 + 规则比对”的方式运行，不会在点击“运行样例核验”时自动调用多模态模型。

原因是内部 OpenAI-compatible 接口虽然大概率可用，但图片输入协议、模型名、鉴权方式和 JSON 输出稳定性尚未实际验证。为了避免主流程被模型接入细节卡住，第一版先把产品闭环跑通：

- 系统支付指令输入。
- 文档预览。
- 票面结构化结果输入。
- 字段 Schema 和业务配置。
- 一致性比对。
- 风险展示。
- 人工反馈。

真实模型接入路径：

1. 使用 `scripts/test_model_api.py` 验证纯文本调用。
2. 使用同一脚本验证图片输入调用。
3. 确认模型能稳定输出约定 JSON。
4. 将上传文档接口接入 `extract_with_model`。
5. 页面上增加“调用 AI 提取票面字段”按钮，替代手工粘贴票面结构化结果。

当前实现已补充页面级模型配置：

- 在 Demo 页面填写 OpenAI-compatible 接口地址、模型名称、API Key 和超时时间。
- 配置保存到本地 `config.local.json`，不提交到 Git。
- 页面支持文本连通测试和图片输入测试。
- 页面支持把当前预览文档发送给模型，提取结果会写入“票面结构化结果 JSON”区域，再进入自定义核验。
- 火山方舟地址 `https://ark.cn-beijing.volces.com/api/coding/v3` 和模型名 `Doubao-Seed-2.0-pro` 已作为默认示例配置。
