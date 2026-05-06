let selectedSample = null;
let fieldSchema = {};
let fieldAliases = {};
let mappingRules = {};
let currentLang = "zh";
let uploadedDocument = null;

const qs = (id) => document.getElementById(id);

const fieldOrder = [
  "payer_name",
  "payer_account",
  "payer_bank",
  "beneficiary_name",
  "beneficiary_account",
  "beneficiary_bank",
  "swift_code",
  "iban",
  "intermediary_bank",
  "currency",
  "amount",
  "amount_in_words",
  "payment_date",
  "purpose",
  "charge_bearer",
  "non_transferable",
];

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
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function init() {
  const health = await api("/api/health");
  qs("health").textContent = health.status;
  fieldSchema = await api("/api/config/field_schema.json");
  fieldAliases = await api("/api/config/field_aliases.json");
  mappingRules = await api("/api/config/mapping_rules.json");
  await loadModelSettings();
  renderPaymentForm({});
  renderBusinessConfig();
  renderAiTuningConfig();
  await loadSamples();
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
  qs("documentFrame").src = selectedSample.image_path;
  fillPayment(selectedSample.payment_instruction);
  qs("customExtraction").value = JSON.stringify(selectedSample.expected_result, null, 2);
  qs("summary").innerHTML = "";
  qs("results").innerHTML = "";
}

function renderPaymentForm(values) {
  const box = qs("paymentForm");
  box.innerHTML = "";
  const keys = [...new Set([...fieldOrder, ...Object.keys(values)])].filter((key) => key !== "non_transferable");
  keys.forEach((key) => {
    const row = document.createElement("label");
    row.className = "field-row";
    row.innerHTML = `<span>${fieldLabel(key)}</span><input data-field="${key}" value="${escapeHtml(values[key] ?? "")}" />`;
    box.appendChild(row);
  });
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

async function runVerify() {
  if (!selectedSample) return;
  const result = await api(`/api/verify/${selectedSample.id}`, { method: "POST" });
  renderResult(result);
}

async function runCustomVerify() {
  const payment = readPaymentForm();
  const extraction = JSON.parse(qs("customExtraction").value);
  const result = await api("/api/verify-custom", {
    method: "POST",
    body: JSON.stringify({ sample_id: "custom_input", payment_instruction: payment, extraction }),
  });
  renderResult(result);
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
  if (showMessage) {
    qs("modelTestResult").textContent = result.api_key_set ? "模型配置已保存，API Key 已保存到本地。" : "模型配置已保存，但 API Key 为空，暂时不能调用模型。";
  }
}

async function testTextModel() {
  qs("modelTestResult").textContent = "测试中...";
  await saveModelSettings(false);
  const result = await api("/api/model/test", {
    method: "POST",
    body: JSON.stringify({ prompt: qs("modelPrompt").value }),
  });
  qs("modelTestResult").textContent = JSON.stringify(simplifyModelResult(result), null, 2);
}

async function testImageModel() {
  qs("modelTestResult").textContent = "图片测试中...";
  await saveModelSettings(false);
  const image = await currentImagePayload();
  const result = await api("/api/model/test", {
    method: "POST",
    body: JSON.stringify({
      prompt: "请识别这张付款文件中的收款人、金额、币种、账号等关键信息，用简短中文回答。",
      image_base64: image.base64,
      mime_type: image.mimeType,
    }),
  });
  qs("modelTestResult").textContent = JSON.stringify(simplifyModelResult(result), null, 2);
}

async function extractWithModel() {
  qs("modelTestResult").textContent = "正在调用 AI 提取票面字段...";
  await saveModelSettings(false);
  const image = await currentImagePayload();
  const result = await api("/api/extract-with-model", {
    method: "POST",
    body: JSON.stringify({
      prompt: "请从票据中提取结构化字段。",
      image_base64: image.base64,
      mime_type: image.mimeType,
    }),
  });
  qs("customExtraction").value = JSON.stringify(result, null, 2);
  qs("modelTestResult").textContent = "AI 提取完成，结果已写入票面结构化结果 JSON。";
}

function renderResult(result) {
  qs("summary").innerHTML = `
    <span class="badge">总体：${result.overall_status === "pass" ? "通过" : "需关注"}</span>
    <span class="badge danger">高风险：${result.summary.high}</span>
    <span class="badge warn">中风险：${result.summary.medium}</span>
    <span class="badge">低风险：${result.summary.low}</span>
    <span class="badge ok">一致：${result.summary.match}</span>
  `;
  const box = qs("results");
  box.innerHTML = "";
  [...result.items].sort((a, b) => riskRank(a) - riskRank(b)).forEach((item) => box.appendChild(renderItem(result.sample_id, item)));
}

function renderItem(sampleId, item) {
  const div = document.createElement("div");
  const css = item.status === "match" ? "match" : item.risk_level;
  div.className = `result-card ${css}`;
  div.innerHTML = `
    <div class="result-head">
      <strong>${item.display_name}</strong>
      <span>${statusText(item.status)}</span>
    </div>
    <div class="compare-values">
      <div><b>系统值</b><p>${empty(item.system_value)}</p></div>
      <div><b>票面值</b><p>${empty(item.document_value)}</p></div>
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
    button.onclick = async () => {
      await api("/api/feedback", {
        method: "POST",
        body: JSON.stringify({ sample_id: sampleId, field: item.field, action: button.dataset.action }),
      });
      button.textContent = "已保存";
    };
  });
  return div;
}

function renderBusinessConfig() {
  const box = qs("businessConfig");
  box.innerHTML = "";
  const table = document.createElement("table");
  table.innerHTML = `
    <thead><tr><th>字段</th><th>风险等级</th><th>比对方式</th><th>票面未出现时</th></tr></thead>
    <tbody></tbody>
  `;
  const body = table.querySelector("tbody");
  Object.entries(fieldSchema).forEach(([field, meta]) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${fieldLabel(field)}<div class="tech-key">${field}</div></td>
      <td>
        <select data-field="${field}" data-prop="risk_level">
          ${option("high", "高风险", meta.risk_level)}
          ${option("medium", "中风险", meta.risk_level)}
          ${option("low", "低风险", meta.risk_level)}
        </select>
      </td>
      <td>
        <select data-field="${field}" data-prop="compare_type">
          ${Object.entries(compareLabels).map(([value, label]) => option(value, label, meta.compare_type)).join("")}
        </select>
      </td>
      <td>
        <select data-field="${field}" data-prop="document_presence">
          ${option("optional", "不提示，仅核对已出现字段", meta.document_presence)}
          ${option("required", "必须出现在票面", meta.document_presence)}
          ${option("special_risk", "作为特殊票面提示", meta.document_presence)}
        </select>
      </td>
    `;
    body.appendChild(row);
  });
  box.appendChild(table);
}

function renderAiTuningConfig() {
  const box = qs("aiTuningConfig");
  box.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "tuning-grid";
  Object.entries(fieldSchema).forEach(([field]) => {
    const card = document.createElement("div");
    card.className = "tuning-card";
    card.innerHTML = `
      <strong>${fieldLabel(field)}</strong>
      <div class="tech-key">${field}</div>
      <label>票面常见叫法<input data-field="${field}" data-kind="aliases" value="${escapeHtml((fieldAliases[field] || []).join('、'))}" /></label>
      <label>位置/模板提示<input data-field="${field}" data-kind="hint" value="${escapeHtml(templateHintFor(field))}" placeholder="例如：右上角金额框、Beneficiary 信息区域" /></label>
      <label>业务说明<input data-field="${field}" data-kind="note" value="${escapeHtml(mappingRules.business_notes?.[field] || '')}" placeholder="给配置人员看的说明" /></label>
    `;
    wrap.appendChild(card);
  });
  box.appendChild(wrap);
}

function templateHintFor(field) {
  const rules = mappingRules.template_rules || [];
  for (const rule of rules) {
    if (rule.hints?.[field]) return rule.hints[field];
  }
  return "";
}

async function saveAiTuning() {
  const aliases = {};
  const notes = {};
  const hints = {};
  document.querySelectorAll("#aiTuningConfig input").forEach((input) => {
    const field = input.dataset.field;
    if (input.dataset.kind === "aliases") {
      aliases[field] = input.value.split(/[、,，]/).map((x) => x.trim()).filter(Boolean);
    }
    if (input.dataset.kind === "hint") {
      hints[field] = input.value.trim();
    }
    if (input.dataset.kind === "note") {
      notes[field] = input.value.trim();
    }
  });
  fieldAliases = aliases;
  mappingRules.business_notes = notes;
  mappingRules.template_rules = mappingRules.template_rules || [];
  const demoRule = mappingRules.template_rules[0] || { template_id: "business_demo", document_type: "demo", country: "GLOBAL", hints: {} };
  demoRule.hints = { ...(demoRule.hints || {}), ...hints };
  mappingRules.template_rules[0] = demoRule;
  await api("/api/config/field_aliases.json", { method: "PUT", body: JSON.stringify(fieldAliases) });
  await api("/api/config/mapping_rules.json", { method: "PUT", body: JSON.stringify(mappingRules) });
  qs("saveAiTuning").textContent = "已保存";
  setTimeout(() => (qs("saveAiTuning").textContent = "保存调优配置"), 1200);
}

async function saveBusinessConfig() {
  document.querySelectorAll("#businessConfig select").forEach((select) => {
    fieldSchema[select.dataset.field][select.dataset.prop] = select.value;
  });
  await api("/api/config/field_schema.json", { method: "PUT", body: JSON.stringify(fieldSchema) });
  qs("saveBusinessConfig").textContent = "已保存";
  setTimeout(() => (qs("saveBusinessConfig").textContent = "保存字段配置"), 1200);
}

function previewUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  const url = URL.createObjectURL(file);
  qs("documentFrame").src = url;
  fileToBase64(file).then((payload) => {
    uploadedDocument = payload;
  });
  qs("uploadHint").textContent = `已选择：${file.name}。可以点击“调用 AI 提取票面字段”测试真实多模态模型。`;
}

function toggleLang() {
  currentLang = currentLang === "zh" ? "en" : "zh";
  qs("langToggle").textContent = currentLang === "zh" ? "English" : "中文";
  renderPaymentForm(readPaymentForm());
  renderBusinessConfig();
  renderAiTuningConfig();
}

function fillFromSample() {
  if (selectedSample) fillPayment(selectedSample.payment_instruction);
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
    reader.onload = () => {
      const dataUrl = String(reader.result);
      resolve({ base64: dataUrl.split(",")[1], mimeType });
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function mimeFromPath(path) {
  const lower = path.toLowerCase();
  if (lower.endsWith(".svg")) return "image/svg+xml";
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  if (lower.endsWith(".pdf")) return "application/pdf";
  return "image/png";
}

function simplifyModelResult(result) {
  const message = result?.choices?.[0]?.message?.content;
  return message ? { content: message } : result;
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

function feedbackButton(action, label) {
  return `<button data-action="${action}">${label}</button>`;
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

function friendlyError(err) {
  const message = String(err?.message || err);
  if (message.includes("LLM_BASE_URL") || message.includes("LLM_API_KEY")) {
    return "模型调用失败：接口地址或 API Key 没有保存成功。请填写 API Key 后点击“保存模型配置”，或直接点击测试按钮自动保存后重试。";
  }
  if (message.includes("401") || message.includes("Unauthorized")) {
    return "模型调用失败：API Key 鉴权失败，请确认 Key 是否正确或是否有该模型权限。";
  }
  if (message.includes("404")) {
    return "模型调用失败：接口地址或模型名称可能不正确。请确认 OpenAI-compatible 地址是否应以 /v3 结尾，以及模型名称是否可用。";
  }
  return `模型调用失败：${message}`;
}

qs("runVerify").onclick = runVerify;
qs("runCustomVerify").onclick = runCustomVerify;
qs("extractWithModel").onclick = () => extractWithModel().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("saveBusinessConfig").onclick = saveBusinessConfig;
qs("saveAiTuning").onclick = saveAiTuning;
qs("saveModelSettings").onclick = () => saveModelSettings().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("testTextModel").onclick = () => testTextModel().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("testImageModel").onclick = () => testImageModel().catch((err) => (qs("modelTestResult").textContent = friendlyError(err)));
qs("documentUpload").onchange = previewUpload;
qs("langToggle").onclick = toggleLang;
qs("fillFromSample").onclick = fillFromSample;

init().catch((err) => {
  qs("health").textContent = "error";
  console.error(err);
});
