let selectedSample = null;
let activeConfig = "field_schema.json";

const qs = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function init() {
  const health = await api("/api/health");
  qs("health").textContent = health.status;
  await loadSamples();
  await loadConfig(activeConfig);
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
  if (samples[0]) {
    box.querySelector("button").click();
  }
}

async function selectSample(sampleId, button) {
  document.querySelectorAll(".sample-list button").forEach((x) => x.classList.remove("active"));
  button.classList.add("active");
  selectedSample = await api(`/api/samples/${sampleId}`);
  qs("sampleTitle").textContent = selectedSample.name;
  qs("documentFrame").src = selectedSample.image_path;
  qs("paymentJson").textContent = JSON.stringify(selectedSample.payment_instruction, null, 2);
  qs("summary").innerHTML = "";
  qs("results").innerHTML = "";
}

async function runVerify() {
  if (!selectedSample) return;
  const result = await api(`/api/verify/${selectedSample.id}`, { method: "POST" });
  renderResult(result);
}

function renderResult(result) {
  qs("summary").innerHTML = `
    <span class="badge">总体：${result.overall_status === "pass" ? "通过" : "需关注"}</span>
    <span class="badge">高风险：${result.summary.high}</span>
    <span class="badge">中风险：${result.summary.medium}</span>
    <span class="badge">低风险：${result.summary.low}</span>
    <span class="badge">一致：${result.summary.match}</span>
  `;
  const box = qs("results");
  box.innerHTML = "";
  const sorted = [...result.items].sort((a, b) => riskRank(a) - riskRank(b));
  sorted.forEach((item) => box.appendChild(renderItem(result.sample_id, item)));
}

function riskRank(item) {
  if (item.status === "match") return 4;
  return { high: 1, medium: 2, low: 3 }[item.risk_level] || 5;
}

function renderItem(sampleId, item) {
  const div = document.createElement("div");
  const css = item.status === "match" ? "match" : item.risk_level;
  div.className = `result-card ${css}`;
  div.innerHTML = `
    <strong>${item.display_name}</strong> · ${statusText(item.status)}
    <div class="meta">系统值：${empty(item.system_value)}</div>
    <div class="meta">票面值：${empty(item.document_value)}</div>
    <div class="meta">${item.message}</div>
    <div class="meta">证据：${item.evidence.text || "-"} (${item.evidence.region_hint || "-"}) · 置信度 ${Math.round((item.confidence || 0) * 100)}%</div>
    <div class="feedback">
      ${feedbackButton(sampleId, item.field, "confirm_match", "确认一致")}
      ${feedbackButton(sampleId, item.field, "confirm_mismatch", "确认不一致")}
      ${feedbackButton(sampleId, item.field, "ai_error", "AI 识别错误")}
      ${feedbackButton(sampleId, item.field, "ignore", "忽略")}
      ${feedbackButton(sampleId, item.field, "submit_optimization", "提交优化")}
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

function feedbackButton(sampleId, field, action, label) {
  return `<button data-sample="${sampleId}" data-field="${field}" data-action="${action}">${label}</button>`;
}

function statusText(status) {
  return {
    match: "一致",
    mismatch: "不一致",
    missing_in_document: "票面缺失",
    document_only: "票面提示",
    unchecked: "未检查",
  }[status] || status;
}

function empty(value) {
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

async function loadConfig(name) {
  activeConfig = name;
  document.querySelectorAll(".config-tabs button").forEach((x) => x.classList.toggle("active", x.dataset.config === name));
  const config = await api(`/api/config/${name}`);
  qs("configEditor").value = JSON.stringify(config, null, 2);
}

async function saveConfig() {
  const payload = JSON.parse(qs("configEditor").value);
  await api(`/api/config/${activeConfig}`, { method: "PUT", body: JSON.stringify(payload) });
  qs("saveConfig").textContent = "已保存";
  setTimeout(() => (qs("saveConfig").textContent = "保存配置"), 1200);
}

qs("runVerify").onclick = runVerify;
qs("saveConfig").onclick = saveConfig;
document.querySelectorAll(".config-tabs button").forEach((button) => {
  button.onclick = () => loadConfig(button.dataset.config);
});
init().catch((err) => {
  qs("health").textContent = "error";
  console.error(err);
});
