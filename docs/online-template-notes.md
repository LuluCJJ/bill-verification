# 票据模板参考要点

本 Demo 使用公开常见票据形态作为参考，样例数据全部为合成数据，不包含公司真实业务信息。

参考来源包括公开支票填写说明和公开电汇申请表样例，例如 UC Davis 的支票字段说明、DBS Telegraphic Transfer Application Form、ANZ Telegraphic Transfer Application Form、Bank of Baroda Fiji SWIFT Application Form 等。

## 1. 支票常见字段

公开样例中的支票通常包含：

- 银行名称。
- 支票号码。
- 日期。
- 收款人或 Payee。
- 数字金额。
- 大写金额或 amount in words。
- 付款人签名。
- Memo、用途或备注。
- MICR 或底部机读码。
- Not Negotiable、A/C Payee Only、不可转让等限制性标识。

Demo 中的国内支票样例参考了这些字段，但不复刻任何真实银行版式。

## 2. 转账信/电汇申请常见字段

公开样例中的 Telegraphic Transfer、Remittance Application、Payment Instruction 通常包含：

- Applicant、Remitter、付款人。
- Debit Account、付款账号。
- Beneficiary、收款人。
- Beneficiary Account、收款账号或 IBAN。
- Beneficiary Bank、Account With Bank、收款银行。
- SWIFT/BIC。
- Currency and Amount。
- Value Date。
- Details of Payment、用途或附言。
- Charge Bearer，例如 OUR、SHA、BEN。
- Applicant signature。

Demo 中的跨境电汇样例参考了这些字段，但所有公司名、账号、银行和金额均为合成数据。

## 4. 参考链接

- [UC Davis - How to Write a Check](https://financeandbusiness.ucdavis.edu/student-resources/cashier/checks/write)
- [DBS - Telegraphic Transfer Application Form](https://www.dbs.com/iwov-resources/images/au/form-manual-telegraphic-transfer-application-australia-sep2023.pdf)
- [ANZ - Telegraphic Transfer Application Form](https://www.anz.com/content/dam/vanuatu/pdf/telegraphic-transfer-application-form-vanuatu.pdf)
- [Bank of Baroda Fiji - Application Form for Telegraphic Transfers](https://www.bankofbaroda-fiji.com/-/media/project/bob/countrywebsites/Fiji/uploader/Remittances/Application-Form-for-Telegraphic-Transfers-SWIFT-02-02.pdf)

## 3. 对 Demo 设计的影响

- 系统字段应设计得比票面字段更全。
- 票面字段通常是系统字段的子集。
- 第一版按“整体一致性预审”展示，不把配置逻辑做成最终业务口径。
- 配置管理页用于演示 MAP 后续配置字段、别名和映射规则后，AI 提取结果如何与配置规则组合。
