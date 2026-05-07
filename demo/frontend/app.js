let selectedSample = null;
let fieldSchema = {};
let fieldAliases = {};
let mappingRules = {};
let currentLang = "zh";
let uploadedDocument = null;
let lastExtraction = null;
let lastVerification = null;
let resultFilter = "risks";

const qs = (id) => document.getElementById(id);

const groups = {
  payer: { title: "付款方信息", fields: ["payer_name", "payer_account", "payer_bank", "payer_bank_code"] },
  beneficiary: { title: "收款方信息", fields: ["beneficiary_name", "beneficiary_account", "beneficiary_bank", "beneficiary_bank_address", "swift_code", "iban", "intermediary_bank"] },
  amount: { title: "金额信息", fields: ["currency", "amount", "amount_in_words"] },
  transaction: { title: "交易信息", fields: ["payment_date", "purpose", "charge_bearer"] },
  risk: { title: "特殊风险", fields: ["non_transferable"] },
};

const fieldOrder = Object.values(groups).flatMap((group) => group.fields);

const labels = {
  zh: {
    payer_name: "付款方名称",
    payer_account: "付款方账号",
    payer_bank: "付款方银行",
    payer_bank_code: "付款方银行代码",
    beneficiary_name: "收款方名称",
    beneficiary_account: "收款方账号",
    beneficiary_bank: "收款方银行",
    beneficiary_bank_address: "收款方银行地址",
    swift_code: "SWIFT/BIC",
    iban: "IBAN",
    intermediary_bank: "中间行",
    currency: "币种",
    amount: "金额",
    amount_in_words: "大写金额",
    payment_date: "付款日期",
    purpose: "付款用途",
    charge_bearer: "费用承担",
    non_transferable: "不可转让/限定入账",
  },
  en: {
    payer_name: "Payer Name",
    payer_account: "Payer Account",
    payer_bank: "Payer Bank",
    payer_bank_code: "Payer Bank Code",
    beneficiary_name: "Beneficiary Name",
    beneficiary_account: "Beneficiary Account",
    beneficiary_bank: "Beneficiary Bank",
    beneficiary_bank_address: "Beneficiary Bank Address",
    swift_code: "SWIFT/BIC",
    iban: "IBAN",
    intermediary_bank: "Intermediary Bank",
    currency: "Currency",
    amount: "Amount",
    amount_in_words: "Amount in Words",
    payment_date: "Payment Date",
    purpose: "Purpose",
    charge_bearer: "Charge Bearer",
    non_transferable: "Non-transferable",
  },
};

const compareLabels = {
  amount: "金额精确一致",
  account: "账号去空格后精确一致",
  currency: "币种归一后比较",
  date: "日期归一后比较",
  normalized_text: "名称/文本归一后比较",
  bank_name: "银行名称归一后比较",
  contains_text: "用途包含或语义近似",
  special_presence: "票面特殊提示",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const payload = JSON.parse(text);
      message = payload.detail || text;
    } catch {
      message = text;
    }
    throw new Error(message);
  }
  return response.json();
}

async function init() {
  qs("health").textContent = (await api("/api/health")).status;
  fieldSchema = await api("/api/config/field_schema.json");
  fieldAliases = await api("/api/config/field_aliases.json");
  mappingRules = await api("/api/config/mapping_rules.json");
  await loadModelSettings();
  renderPaymentForm({});
  renderTemplateList();
  renderBusinessConfig();
  renderAiTuningConfig();
  await loadSamples();
  await renderFeedbackList();
}

async function loadSamples() {
  const samples = await api("/api/samples");
  const box = qs("sampleList");
  box.innerHTML = "";
  samples.forEach((sample) => {
    const btn = document.createElement("button");
    btn.textContent = sample.name;
    btn.onclick = () => selectSample(sample.id, btn);
    box.appendChild(btn);
  });
  if (samples[0]) box.querySelector("button").click();
}

async function selectSample(sampleId, button) {
  document.querySelectorAll(".sample-list button").forEach((x) => x.classList.remove("active"));
  button.classList.add("active");
  selectedSample = await api(`/api/samples/${sampleId}`);
  uploadedDocument = null;
  lastExtraction = selectedSample.expected_result;
  qs("documentFrame").src = selectedSample.image_path;
  qs("currentTemplate").textContent = selectedSample.template_id || "-";
  qs("aiStatus").textContent = "等待预审";
  qs("uploadHint").textContent = "当前使用样例票据。点击“开始 AI 预审”会调用真实模型提取票面字段。";
  fillPayment(selectedSample.payment_instruction);
  renderExtraction(selectedSample.expected_result, "预置样例结果，仅作对照");
  clearResults();
  renderVerifyDemoGuide();
}

function renderPaymentForm(values) {
  const box = qs("paymentForm");
  box.innerHTML = "";
  for (const group of Object.values(groups)) {
    const groupBox = document.createElement("div");
    groupBox.className = "payment-group";
    groupBox.innerHTML = `<h3>${group.title}</h3>`;
    group.fields.filter((key) => key !== "non_transferable").forEach((key) => {
      const row = document.createElement("label");
      row.className = "field-row";
      row.innerHTML = `<span>${fieldLabel(key)}</span><input data-field="${key}" value="${escapeHtml(values[key] ?? "")}" />`;
      groupBox.appendChild(row);
    });
    box.appendChild(groupBox);
  }
}

function fillPayment(values) {
  renderPaymentForm(values || {});
}

function readPaymentForm() {
  const data = {};
  document.querySelectorAll("#paymentForm input").forEach((input) => {
    if (input.value.trim()) data[input.dataset.field] = input.value.trim();
  });
  return data;
}

async function startPreAudit() {
  if (!selectedSample && !uploadedDocument) throw new Error("请先选择任务或上传票据。");
  qs("aiStatus").textContent = "AI 提取中";
  clearResults();
  await saveModelSettings(false);
  let extraction = null;
  if (selectedSample?.demo_flow === "alias_feedback") {
    extraction = selectedSample.expected_result;
    qs("aiStatus").textContent = "演示：首次提取漏识别";
  } else {
    const image = await currentImagePayload();
    ensureModelImageType(image.mimeType);
    extraction = await api("/api/extract-with-model", {
      method: "POST",
      body: JSON.stringify({ prompt: "请从票据中提取结构化字段。", image_base64: image.base64, mime_type: image.mimeType }),
    });
  }
  lastExtraction = extraction;
  renderExtraction(extraction, selectedSample?.demo_flow === "alias_feedback" ? "演示首次 AI 提取结果" : "真实模型提取结果");
  qs("aiStatus").textContent = "规则核验中";
  await runCustomVerify();
  qs("aiStatus").textContent = "预审完成";
  renderVerifyDemoGuide();
}

async function runCustomVerify() {
  if (!lastExtraction) {
    lastExtraction = JSON.parse(qs("customExtraction").value);
  }
  const result = await api("/api/verify-custom", {
    method: "POST",
    body: JSON.stringify({ sample_id: selectedSample?.id || "custom_input", payment_instruction: readPaymentForm(), extraction: lastExtraction }),
  });
  renderResult(result);
}

function renderExtraction(extraction, sourceLabel) {
  lastExtraction = extraction;
  qs("customExtraction").value = JSON.stringify(extraction, null, 2);
  const fields = extraction.extracted_fields || [];
  const avgConfidence = fields.length ? Math.round((fields.reduce((sum, field) => sum + Number(field.confidence || 0), 0) / fields.length) * 100) : 0;
  const isLive = sourceLabel.includes("真实模型");
  qs("extractionStatus").innerHTML = `
    <div class="status-card ${isLive ? "live" : "sample"}">
      <span>${isLive ? "真实 AI 识别" : "样例预置结果"}</span>
      <strong>${fields.length}</strong>
      <em>提取字段</em>
    </div>
    <div class="status-card">
      <span>平均置信度</span>
      <strong>${avgConfidence}%</strong>
      <em>${isLive ? "来自模型输出" : "样例标注"}</em>
    </div>
    <div class="status-card ${(extraction.special_risks || []).length ? "warn" : ""}">
      <span>特殊提示</span>
      <strong>${(extraction.special_risks || []).length}</strong>
      <em>票面额外风险</em>
    </div>
  `;
  qs("extractionSummary").innerHTML = "";
  fields.forEach((field) => {
    const chip = document.createElement("div");
    chip.className = `field-chip ${confidenceClass(field.confidence)}`;
    chip.innerHTML = `
      <div class="field-chip-head">
        <strong>${fieldLabel(field.normalized_field)}</strong>
        <em>${Math.round((field.confidence || 0) * 100)}%</em>
      </div>
      <span>${escapeHtml(field.raw_value)}</span>
      <small>票面标签：${escapeHtml(field.raw_label || "-")}</small>
      <small>证据：${escapeHtml(field.evidence?.text || "-")}</small>
    `;
    qs("extractionSummary").appendChild(chip);
  });
}

function renderResult(result) {
  lastVerification = result;
  qs("summary").innerHTML = `
    <span class="badge">总体：${result.overall_status === "pass" ? "通过" : "需关注"}</span>
    <span class="badge danger">高风险：${result.summary.high}</span>
    <span class="badge warn">中风险：${result.summary.medium}</span>
    <span class="badge">低风险：${result.summary.low}</span>
    <span class="badge ok">一致：${result.summary.match}</span>
  `;
  renderResultItems();
}

function renderResultItems() {
  if (!lastVerification) return;
  const box = qs("results");
  box.innerHTML = "";
  const items = [...lastVerification.items].sort((a, b) => riskRank(a) - riskRank(b));
  const filtered = items.filter((item) => {
    if (resultFilter === "all") return true;
    if (resultFilter === "match") return item.status === "match";
    return item.status !== "match";
  });
  if (!filtered.length) {
    box.innerHTML = `<div class="empty-state">${resultFilter === "risks" ? "没有需要关注的风险项。" : "没有符合筛选条件的结果。"}</div>`;
    return;
  }
  filtered.forEach((item) => box.appendChild(renderItem(lastVerification.sample_id, item)));
}

function renderItem(sampleId, item) {
  const div = document.createElement("div");
  const css = item.status === "match" ? "match" : item.risk_level;
  div.className = `result-card ${css}`;
  div.innerHTML = `
    <div class="result-head">
      <strong>${item.display_name}</strong>
      <span class="result-status ${css}">${statusText(item.status)}</span>
    </div>
    <div class="compare-values">
      <div><b>系统值</b><p>${empty(item.system_value)}</p></div>
      <div class="${item.status === "mismatch" ? "attention-value" : ""}"><b>票面值</b><p>${empty(item.document_value)}</p></div>
    </div>
    <div class="meta">${item.message}</div>
    <div class="meta">证据：${item.evidence.text || "-"} (${item.evidence.region_hint || "-"}) · 置信度 ${Math.round((item.confidence || 0) * 100)}%</div>
    <div class="feedback">
      ${feedbackButton("confirm_match", "确认一致")}
      ${feedbackButton("confirm_mismatch", "确认不一致")}
      ${feedbackButton("ai_error", "AI识别错误")}
      ${feedbackButton("ignore", "忽略")}
      ${feedbackButton("submit_optimization", "提交优化")}
    </div>
  `;
  div.querySelectorAll("button").forEach((button) => {
    button.onclick = () => handleFeedbackAction(sampleId, item, button).catch((err) => alert(friendlyError(err)));
  });
  return div;
}

async function handleFeedbackAction(sampleId, item, button) {
  const action = button.dataset.action;
  if (sampleId === "alias_feedback_case" && item.field === "beneficiary_bank" && action === "submit_optimization") {
    button.textContent = "应用中...";
    const data = await api("/api/demo/alias-case/apply", { method: "POST", body: "{}" });
    fieldAliases = await api("/api/config/field_aliases.json");
    mappingRules = await api("/api/config/mapping_rules.json");
    lastExtraction = data.extraction;
    renderExtraction(data.extraction, "反馈优化后提取结果");
    renderResult(data.verification);
    renderTemplateList();
    await renderFeedbackList();
    renderVerifyDemoGuide("已将“入账行”加入收款方银行别名，重新核验后该风险项已变为一致。");
    qs("aiStatus").textContent = "反馈优化完成";
    return;
  }
  await api("/api/feedback", { method: "POST", body: JSON.stringify({ sample_id: sampleId, field: item.field, action }) });
  button.textContent = "已保存";
  await renderFeedbackList();
}

function clearResults() {
  qs("summary").innerHTML = "";
  qs("results").innerHTML = "";
  lastVerification = null;
}

function renderVerifyDemoGuide(message = "") {
  const box = qs("verifyDemoGuide");
  if (!selectedSample || selectedSample.demo_flow !== "alias_feedback") {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  const riskItem = lastVerification?.items?.find((item) => item.field === "beneficiary_bank");
  const done = riskItem?.status === "match";
  box.classList.remove("hidden");
  box.innerHTML = `
    <div>
      <h2>当前用例：别名漏识别到反馈优化</h2>
      <p class="hint">票面写的是“入账行”，业务含义是收款方银行。初始别名清单没有这个叫法，所以第一次核验会提示收款方银行未识别。</p>
      ${message ? `<p class="demo-message">${escapeHtml(message)}</p>` : ""}
    </div>
    <div class="demo-steps">
      <span class="${lastVerification ? "done" : "active"}">1. 开始 AI 预审</span>
      <span class="${riskItem && !done ? "active" : done ? "done" : ""}">2. 发现漏识别风险</span>
      <span class="${done ? "done" : ""}">3. 点击“提交优化”应用别名</span>
    </div>
    <div class="panel-actions">
      <button id="resetVerifyAliasCase">重置用例</button>
      <button id="applyVerifyAliasCase" class="primary">直接应用反馈别名</button>
    </div>
  `;
  qs("resetVerifyAliasCase").onclick = () => resetAliasCaseFromVerify().catch((err) => alert(friendlyError(err)));
  qs("applyVerifyAliasCase").onclick = () => applyAliasCaseFromVerify().catch((err) => alert(friendlyError(err)));
}

async function resetAliasCaseFromVerify() {
  await api("/api/demo/alias-case/reset", { method: "POST", body: "{}" });
  fieldAliases = await api("/api/config/field_aliases.json");
  mappingRules = await api("/api/config/mapping_rules.json");
  if (selectedSample?.id === "alias_feedback_case") {
    selectedSample = await api("/api/samples/alias_feedback_case");
    lastExtraction = selectedSample.expected_result;
    renderExtraction(selectedSample.expected_result, "预置样例结果，仅作对照");
    clearResults();
    qs("aiStatus").textContent = "等待预审";
  }
  renderTemplateList();
  await renderFeedbackList();
  renderVerifyDemoGuide("已重置别名配置。现在点击“开始 AI 预审”会再次出现漏识别风险。");
}

async function applyAliasCaseFromVerify() {
  const data = await api("/api/demo/alias-case/apply", { method: "POST", body: "{}" });
  fieldAliases = await api("/api/config/field_aliases.json");
  mappingRules = await api("/api/config/mapping_rules.json");
  lastExtraction = data.extraction;
  renderExtraction(data.extraction, "反馈优化后提取结果");
  renderResult(data.verification);
  renderTemplateList();
  await renderFeedbackList();
  qs("aiStatus").textContent = "反馈优化完成";
  renderVerifyDemoGuide("已应用别名并重新核验。");
}

function renderTemplateList() {
  const box = qs("templateList");
  box.innerHTML = "";
  (mappingRules.template_rules || []).forEach((template, index) => {
    const btn = document.createElement("button");
    btn.textContent = `${template.country || "GLOBAL"} / ${template.document_type || "document"} / ${template.template_id}`;
    btn.onclick = () => selectTemplate(index, btn);
    box.appendChild(btn);
  });
  if (box.querySelector("button")) box.querySelector("button").click();
}

function selectTemplate(index, button) {
  document.querySelectorAll("#templateList button").forEach((x) => x.classList.remove("active"));
  button.classList.add("active");
  const template = mappingRules.template_rules[index];
  qs("templateTitle").textContent = `模板调优：${template.template_id}`;
  renderAiTuningConfig(template);
}

function renderAiTuningConfig(template = (mappingRules.template_rules || [])[0]) {
  const box = qs("aiTuningConfig");
  box.innerHTML = "";
  for (const group of Object.values(groups)) {
    const groupBox = document.createElement("section");
    groupBox.className = "tuning-group";
    groupBox.innerHTML = `<h3>${group.title}</h3>`;
    group.fields.forEach((field) => {
      if (!fieldSchema[field]) return;
      const card = document.createElement("details");
      card.className = "tuning-card";
      card.innerHTML = `
        <summary>${fieldLabel(field)} <span>${field}</span></summary>
        <label>票面常见叫法<input data-field="${field}" data-kind="aliases" value="${escapeHtml((fieldAliases[field] || []).join("、"))}" /></label>
        <label>位置/模板提示<input data-field="${field}" data-kind="hint" value="${escapeHtml(template?.hints?.[field] || "")}" placeholder="例如：右上角金额框、Beneficiary 信息区域" /></label>
        <label>AI 识别要求<input data-field="${field}" data-kind="note" value="${escapeHtml(mappingRules.business_notes?.[field] || "")}" placeholder="例如：不要把 Intermediary Bank 识别为收款银行" /></label>
      `;
      groupBox.appendChild(card);
    });
    box.appendChild(groupBox);
  }
}

async function saveAiTuning() {
  const aliases = {};
  const notes = {};
  const hints = {};
  document.querySelectorAll("#aiTuningConfig input").forEach((input) => {
    const field = input.dataset.field;
    if (input.dataset.kind === "aliases") aliases[field] = input.value.split(/[、,，]/).map((x) => x.trim()).filter(Boolean);
    if (input.dataset.kind === "hint") hints[field] = input.value.trim();
    if (input.dataset.kind === "note") notes[field] = input.value.trim();
  });
  fieldAliases = aliases;
  mappingRules.business_notes = notes;
  mappingRules.template_rules = mappingRules.template_rules || [];
  const active = document.querySelector("#templateList button.active");
  const index = [...document.querySelectorAll("#templateList button")].indexOf(active);
  const targetIndex = index >= 0 ? index : 0;
  mappingRules.template_rules[targetIndex].hints = { ...(mappingRules.template_rules[targetIndex].hints || {}), ...hints };
  await api("/api/config/field_aliases.json", { method: "PUT", body: JSON.stringify(fieldAliases) });
  await api("/api/config/mapping_rules.json", { method: "PUT", body: JSON.stringify(mappingRules) });
  qs("saveAiTuning").textContent = "已保存";
  setTimeout(() => (qs("saveAiTuning").textContent = "保存调优配置"), 1200);
}

function renderBusinessConfig() {
  const box = qs("businessConfig");
  box.innerHTML = "";
  const table = document.createElement("table");
  table.innerHTML = `<thead><tr><th>字段</th><th>风险等级</th><th>比对方式</th><th>票面未出现时</th></tr></thead><tbody></tbody>`;
  const body = table.querySelector("tbody");
  Object.entries(fieldSchema).forEach(([field, meta]) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${fieldLabel(field)}<div class="tech-key">${field}</div></td>
      <td><select data-field="${field}" data-prop="risk_level">${option("high", "高风险", meta.risk_level)}${option("medium", "中风险", meta.risk_level)}${option("low", "低风险", meta.risk_level)}</select></td>
      <td><select data-field="${field}" data-prop="compare_type">${Object.entries(compareLabels).map(([value, label]) => option(value, label, meta.compare_type)).join("")}</select></td>
      <td><select data-field="${field}" data-prop="document_presence">${option("optional", "不提示，仅核对已出现字段", meta.document_presence)}${option("required", "必须出现在票面", meta.document_presence)}${option("special_risk", "作为特殊票面提示", meta.document_presence)}</select></td>
    `;
    body.appendChild(row);
  });
  box.appendChild(table);
}

async function saveBusinessConfig() {
  document.querySelectorAll("#businessConfig select").forEach((select) => {
    fieldSchema[select.dataset.field][select.dataset.prop] = select.value;
  });
  await api("/api/config/field_schema.json", { method: "PUT", body: JSON.stringify(fieldSchema) });
  qs("saveBusinessConfig").textContent = "已保存";
  setTimeout(() => (qs("saveBusinessConfig").textContent = "保存字段配置"), 1200);
}

async function renderFeedbackList() {
  const box = qs("feedbackList");
  box.innerHTML = "";
  const payload = await api("/api/feedback");
  const entries = payload.entries || [];
  if (!entries.length) {
    box.innerHTML = `<div class="empty-state">暂无反馈。可先在“付款核验”结果里点击“AI识别错误/提交优化”，或运行上方别名闭环演示。</div>`;
    return;
  }
  entries.slice().reverse().forEach((entry) => {
    const card = document.createElement("div");
    card.className = "feedback-card";
    card.innerHTML = `
      <div class="feedback-head">
        <strong>${escapeHtml(entry.field || "-")}</strong>
        <span>${feedbackActionText(entry.action)}</span>
      </div>
      <div class="meta">样例：${escapeHtml(entry.sample_id || "-")} · 来源：${escapeHtml(entry.source_file || "runtime")}</div>
      ${entry.corrected_value ? `<div class="meta">修正值：${escapeHtml(entry.corrected_value)}</div>` : ""}
      ${entry.note ? `<div class="meta">说明：${escapeHtml(entry.note)}</div>` : ""}
    `;
    box.appendChild(card);
  });
}

async function loadModelSettings() {
  const settings = await api("/api/model/settings");
  qs("modelBaseUrl").value = settings.base_url || "https://ark.cn-beijing.volces.com/api/coding/v3";
  qs("modelName").value = settings.model || "Doubao-Seed-2.0-pro";
  qs("modelTimeout").value = settings.timeout || 60;
  qs("modelApiKey").placeholder = settings.api_key_set ? "已保存，留空不修改" : "请输入 API Key";
}

async function saveModelSettings(showMessage = true) {
  const payload = {
    base_url: qs("modelBaseUrl").value.trim(),
    model: qs("modelName").value.trim(),
    api_key: qs("modelApiKey").value,
    timeout: Number(qs("modelTimeout").value || 60),
  };
  const result = await api("/api/model/settings", { method: "PUT", body: JSON.stringify(payload) });
  qs("modelApiKey").value = "";
  qs("modelApiKey").placeholder = result.api_key_set ? "已保存，留空不修改" : "请输入 API Key";
  if (showMessage) qs("modelTestResult").textContent = result.api_key_set ? "模型配置已保存，API Key 已保存到本地。" : "模型配置已保存，但 API Key 为空，暂时不能调用模型。";
}

async function testTextModel() {
  qs("modelTestResult").textContent = "测试中...";
  await saveModelSettings(false);
  const result = await api("/api/model/test", { method: "POST", body: JSON.stringify({ prompt: qs("modelPrompt").value }) });
  qs("modelTestResult").textContent = JSON.stringify(simplifyModelResult(result), null, 2);
}

async function testImageModel() {
  qs("modelTestResult").textContent = "图片测试中...";
  await saveModelSettings(false);
  const image = await currentImagePayload();
  ensureModelImageType(image.mimeType);
  const result = await api("/api/model/test", {
    method: "POST",
    body: JSON.stringify({ prompt: "请识别这张付款文件中的收款人、金额、币种、账号等关键信息，用简短中文回答。", image_base64: image.base64, mime_type: image.mimeType }),
  });
  qs("modelTestResult").textContent = JSON.stringify(simplifyModelResult(result), null, 2);
}

async function diagnoseModel() {
  qs("modelTestResult").textContent = "诊断中：正在保存配置并检查文本/图片链路...";
  await saveModelSettings(false);
  let image = null;
  try {
    image = await currentImagePayload();
    ensureModelImageType(image.mimeType);
  } catch (err) {
    const result = await api("/api/model/diagnose", {
      method: "POST",
      body: JSON.stringify({ include_image: false }),
    });
    qs("modelTestResult").textContent = formatDiagnosis(result, `图片诊断未执行：${err.message}`);
    return;
  }
  const result = await api("/api/model/diagnose", {
    method: "POST",
    body: JSON.stringify({ include_image: true, image_base64: image.base64, mime_type: image.mimeType }),
  });
  qs("modelTestResult").textContent = formatDiagnosis(result);
}

function previewUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  const url = URL.createObjectURL(file);
  qs("documentFrame").src = url;
  fileToBase64(file).then((payload) => {
    uploadedDocument = payload;
  });
  qs("uploadHint").textContent = `已选择：${file.name}。点击“开始 AI 预审”会把该文件发送给模型。`;
}

async function currentImagePayload() {
  if (uploadedDocument) return uploadedDocument;
  if (!selectedSample) throw new Error("请先选择样例或上传文档。");
  const response = await fetch(selectedSample.image_path);
  const blob = await response.blob();
  return blobToBase64(blob, blob.type || mimeFromPath(selectedSample.image_path));
}

function fileToBase64(file) {
  return blobToBase64(file, file.type || mimeFromPath(file.name));
}

function blobToBase64(blob, mimeType) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ base64: String(reader.result).split(",")[1], mimeType });
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function showTab(tabId) {
  document.querySelectorAll(".tabs button").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabId));
  document.querySelectorAll(".tab-page").forEach((page) => page.classList.toggle("active", page.id === tabId));
}

function toggleExtractionJson() {
  qs("customExtraction").classList.toggle("collapsed-json");
  qs("showExtractionJson").textContent = qs("customExtraction").classList.contains("collapsed-json") ? "查看结构化 JSON" : "收起结构化 JSON";
}

function toggleLang() {
  currentLang = currentLang === "zh" ? "en" : "zh";
  qs("langToggle").textContent = currentLang === "zh" ? "English" : "中文";
  fillPayment(readPaymentForm());
  renderBusinessConfig();
  renderAiTuningConfig();
}

function fillFromSample() {
  if (selectedSample) fillPayment(selectedSample.payment_instruction);
}

function ensureModelImageType(mimeType) {
  if (!["image/png", "image/jpeg", "image/jpg", "image/webp"].includes(mimeType)) throw new Error(`当前模型测试仅支持 PNG/JPG/WebP 图片。当前文件类型是 ${mimeType}，请先转换为图片后再测试。`);
}

function mimeFromPath(path) {
  const lower = path.toLowerCase();
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  if (lower.endsWith(".webp")) return "image/webp";
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".svg")) return "image/svg+xml";
  return "image/png";
}

function simplifyModelResult(result) {
  const message = result?.choices?.[0]?.message?.content;
  return message ? { content: message } : result;
}

function formatDiagnosis(result, note = "") {
  const lines = [`诊断结论：${result.summary || "-"}`];
  if (note) lines.push(`补充说明：${note}`);
  (result.steps || []).forEach((step, index) => {
    lines.push("");
    lines.push(`${index + 1}. ${step.ok ? "通过" : "失败"} - ${step.name}`);
    lines.push(`   ${step.message}`);
    if (step.endpoint) lines.push(`   endpoint: ${step.endpoint}`);
    if (step.model) lines.push(`   model: ${step.model}`);
    if (step.attempts) lines.push(`   attempts: ${step.attempts}`);
    if (step.api_key_set !== undefined) lines.push(`   api_key_set: ${step.api_key_set}`);
    if (step.image_bytes !== undefined) lines.push(`   image_bytes: ${step.image_bytes}`);
    if (step.image_style) lines.push(`   image_style: ${step.image_style}`);
    if (step.mime_type) lines.push(`   mime_type: ${step.mime_type}`);
    if (step.response_preview) lines.push(`   response: ${step.response_preview}`);
  });
  return lines.join("\n");
}

function friendlyError(err) {
  const message = String(err?.message || err);
  if (message.includes("LLM_BASE_URL") || message.includes("LLM_API_KEY")) return "模型调用失败：接口地址或 API Key 没有保存成功。请填写 API Key 后点击“保存模型配置”。";
  if (message.includes("401") || message.includes("Unauthorized")) return "模型调用失败：API Key 鉴权失败，请确认 Key 是否正确或是否有该模型权限。";
  if (message.includes("404")) return "模型调用失败：接口地址或模型名称可能不正确。";
  return `模型调用失败：${message}`;
}

function option(value, label, selected) {
  return `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`;
}

function fieldLabel(key) {
  return labels[currentLang][key] || fieldSchema[key]?.display_name || key;
}

function riskRank(item) {
  if (item.status === "match") return 4;
  return { high: 1, medium: 2, low: 3 }[item.risk_level] || 5;
}

function confidenceClass(confidence) {
  const value = Number(confidence || 0);
  if (value >= 0.85) return "conf-high";
  if (value >= 0.6) return "conf-mid";
  return "conf-low";
}

function feedbackButton(action, label) {
  return `<button data-action="${action}">${label}</button>`;
}

function feedbackActionText(action) {
  return {
    confirm_match: "确认一致",
    confirm_mismatch: "确认不一致",
    ai_error: "AI识别错误",
    ignore: "忽略",
    submit_optimization: "提交优化",
  }[action] || action || "-";
}

function statusText(status) {
  return { match: "一致", mismatch: "不一致", missing_in_document: "票面缺失", document_only: "票面提示", unchecked: "未检查" }[status] || status;
}

function empty(value) {
  return value === null || value === undefined || value === "" ? "-" : escapeHtml(String(value));
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]);
}

document.querySelectorAll(".tabs button").forEach((btn) => (btn.onclick = () => showTab(btn.dataset.tab)));
document.querySelectorAll(".result-filters button").forEach((btn) => {
  btn.onclick = () => {
    resultFilter = btn.dataset.resultFilter;
    document.querySelectorAll(".result-filters button").forEach((x) => x.classList.toggle("active", x === btn));
    renderResultItems();
  };
});
qs("startPreAudit").onclick = () => startPreAudit().catch((err) => {
  qs("aiStatus").textContent = "预审失败";
  qs("modelTestResult").textContent = friendlyError(err);
  showTab("settingsTab");
});
qs("runCustomVerify").onclick = () => runCustomVerify().catch((err) => alert(friendlyError(err)));
qs("showExtractionJson").onclick = toggleExtractionJson;
qs("saveBusinessConfig").onclick = saveBusinessConfig;
qs("saveAiTuning").onclick = saveAiTuning;
qs("refreshFeedback").onclick = renderFeedbackList;
qs("saveModelSettings").onclick = () => saveModelSettings().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("diagnoseModel").onclick = () => diagnoseModel().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("testTextModel").onclick = () => testTextModel().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("testImageModel").onclick = () => testImageModel().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("documentUpload").onchange = previewUpload;
qs("langToggle").onclick = toggleLang;
qs("fillFromSample").onclick = fillFromSample;

init().catch((err) => {
  qs("health").textContent = "error";
  console.error(err);
});
