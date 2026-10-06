const state = {
  conversationId: localStorage.getItem("smartops_conversation_id"),
  messageCount: 0,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function showToast(message, error = false) {
  const toast = $("#toast");
  toast.textContent = typeof message === "string" && message.trim() ? message : (error ? "İşlem tamamlanamadı." : "İşlem tamamlandı.");
  toast.className = `toast show${error ? " error" : ""}`;
  window.setTimeout(() => { toast.className = "toast"; }, 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let detail = "İstek tamamlanamadı.";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string" && payload.detail.trim()) detail = payload.detail;
      else if (Array.isArray(payload.detail)) detail = payload.detail.map((item) => item.msg || "Geçersiz alan").join(", ");
    } catch (_) { /* response is not JSON */ }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function setView(name) {
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  $$(".view").forEach((view) => view.classList.remove("active"));
  $(`#${name}View`).classList.add("active");
  const titles = { analyze: "Sorun Analizi", chat: "Asistan", files: "Kurumsal Dosyalar", admin: "Yönetim Paneli" };
  $("#pageTitle").textContent = titles[name] || "SmartOps";
  $(".sidebar").classList.remove("open");
}

function renderAnalysis(data) {
  const categoryLabels = { access: "Erişim", network: "Ağ", hardware: "Donanım", software: "Yazılım", email: "E-posta", security: "Güvenlik", other: "Diğer" };
  const severityLabels = { low: "Düşük", medium: "Orta", high: "Yüksek", critical: "Kritik" };
  const causes = data.probable_causes.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const steps = data.troubleshooting_steps.map((item, index) => `<li class="step-item"><span class="step-index">${String(index + 1).padStart(2, "0")}</span><span>${escapeHtml(item)}</span></li>`).join("");
  $("#analysisResult").innerHTML = `
    <div class="result-top">
      <div><span class="result-label">Analiz özeti</span><h2>${escapeHtml(data.summary)}</h2></div>
      <div class="badges"><span class="badge">${escapeHtml(categoryLabels[data.category] || data.category)}</span><span class="badge severity-${escapeHtml(data.severity)}">${escapeHtml(severityLabels[data.severity] || data.severity)}</span></div>
    </div>
    <div class="result-grid">
      <article class="result-card"><h3>Olası nedenler</h3><ul>${causes}</ul></article>
      <article class="result-card"><h3>Çözüm adımları</h3><ol class="steps-list">${steps}</ol></article>
      <article class="result-card action-card"><h3>Önerilen aksiyon</h3><p>${escapeHtml(data.recommended_action)}</p><span class="tool-chip">Eskalasyon: ${data.escalation_required ? "Öneriliyor" : "Şimdilik gerekmiyor"}</span></article>
    </div>`;
  $("#analysisResult").classList.remove("hidden");
}

function updateConversationMeta(tools = []) {
  $("#conversationId").textContent = state.conversationId || "Henüz oluşturulmadı";
  $("#messageCount").textContent = state.messageCount;
  $("#lastTool").textContent = tools.length ? tools.join(", ") : "—";
  $("#loadHistoryButton").disabled = !state.conversationId;
}

function addMessage(role, content, tools = [], sources = []) {
  const welcome = $(".welcome-message");
  if (welcome) welcome.remove();
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  const sourceText = sources.length ? `<span class="tool-chip">Kaynak: ${sources.map((source) => `<a href="/api/v1/files/${encodeURIComponent(source.indexed_file_id)}/content" target="_blank" rel="noopener">${escapeHtml(source.file_name)}</a>${source.location ? ` · ${escapeHtml(source.location)}` : ""} — ${escapeHtml(source.directory_path)}`).join("<br>")}</span>` : "";
  wrapper.innerHTML = `${role === "assistant" ? '<span class="assistant-avatar">S</span>' : ""}<div class="message-bubble">${escapeHtml(content)}${sourceText}${tools.length ? `<span class="tool-chip">Araç: ${escapeHtml(tools.join(", "))}</span>` : ""}</div>`;
  $("#messages").appendChild(wrapper);
  $("#messages").scrollTop = $("#messages").scrollHeight;
}

async function loadHistory() {
  if (!state.conversationId) return;
  try {
    const data = await api(`/api/v1/conversations/${state.conversationId}`);
    $("#messages").innerHTML = "";
    data.messages.forEach((message) => addMessage(message.role, message.content));
    state.messageCount = data.messages.length;
    updateConversationMeta();
    showToast("Konuşma geçmişi yenilendi.");
  } catch (error) {
    localStorage.removeItem("smartops_conversation_id");
    state.conversationId = null;
    updateConversationMeta();
    showToast(error.message, true);
  }
}

async function initialize() {
  try {
    const [health, tools] = await Promise.all([api("/health"), api("/api/v1/tools")]);
    const label = health.llm_mode === "demo" ? "Demo" : "Canlı";
    $("#modeLabel").textContent = label;
    $("#headerMode").textContent = `${label} modu`;
    $("#toolCount").textContent = tools.length;
    $("#chatDisclaimer").textContent = health.llm_mode === "demo"
      ? "Yerel doğrulama modu etkin. Doğal dil yanıtları için model bağlantısı gerekir."
      : "Model yanıtları hata içerebilir. Kritik işlemleri ve kaynakları doğrulayın.";
  } catch (error) {
    showToast("API bağlantısı kurulamadı.", true);
  }
  updateConversationMeta();
  if (state.conversationId) await loadHistory();
}

$$('.nav-item').forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
$(".mobile-menu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
$$('[data-prompt]').forEach((button) => button.addEventListener("click", () => { $("#issueInput").value = button.dataset.prompt; $("#issueInput").focus(); }));

$("#analyzeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type=submit]");
  button.disabled = true;
  $("#analysisResult").classList.add("hidden");
  $("#analysisLoading").classList.remove("hidden");
  try {
    const data = await api("/api/v1/analyze", { method: "POST", body: JSON.stringify({ issue: $("#issueInput").value.trim() }) });
    renderAnalysis(data);
    $("#analysisResult").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
    $("#analysisLoading").classList.add("hidden");
  }
});

$("#chatInput").addEventListener("input", (event) => {
  event.target.style.height = "auto";
  event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`;
});
$("#chatInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#chatForm").requestSubmit(); }
});

$("#chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#chatInput");
  const message = input.value.trim();
  if (!message) return;
  const button = event.currentTarget.querySelector("button");
  addMessage("user", message);
  state.messageCount += 1;
  input.value = "";
  input.style.height = "auto";
  button.disabled = true;
  updateConversationMeta();
  try {
    const payload = { message };
    if (state.conversationId) payload.conversation_id = state.conversationId;
    const data = await api("/api/v1/chat", { method: "POST", body: JSON.stringify(payload) });
    state.conversationId = data.conversation_id;
    localStorage.setItem("smartops_conversation_id", state.conversationId);
    state.messageCount += 1;
    addMessage("assistant", data.response, data.tools_used, data.sources || []);
    updateConversationMeta(data.tools_used);
  } catch (error) {
    addMessage("assistant", `Bir hata oluştu: ${error.message}`);
    showToast(error.message, true);
  } finally { button.disabled = false; input.focus(); }
});

$("#newChatButton").addEventListener("click", () => {
  state.conversationId = null;
  state.messageCount = 0;
  localStorage.removeItem("smartops_conversation_id");
  $("#messages").innerHTML = '<div class="welcome-message"><span class="assistant-avatar large">S</span><h3>Yeni konuşma hazır</h3><p>Bir IT operasyon sorunu yazarak başlayın.</p></div>';
  updateConversationMeta();
});
$("#loadHistoryButton").addEventListener("click", loadHistory);

initialize();

let adminToken = "";

async function adminApi(path, options = {}) {
  return api(path, { ...options, headers: { ...(options.headers || {}), "X-Admin-Token": adminToken } });
}

function renderFileResults(results) {
  const container = $("#fileSearchResults");
  if (!results.length) { container.className = "file-results empty-state"; container.textContent = "Eşleşen dosya bulunamadı."; return; }
  container.className = "file-results";
  container.innerHTML = results.map((file) => `<article class="file-card"><div class="file-card-head"><div><h3><a href="/api/v1/files/${encodeURIComponent(file.indexed_file_id)}/content" target="_blank" rel="noopener">${escapeHtml(file.file_name)}</a></h3><code>${escapeHtml(file.absolute_path)}</code></div><span class="file-type">${escapeHtml(file.extension || "dosya")}</span></div><p>${escapeHtml(file.excerpt || "İçerik özeti bulunmuyor.")}</p></article>`).join("");
}

$("#fileSearchForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const results = await api("/api/v1/files/search", { method: "POST", body: JSON.stringify({ query: $("#fileSearchInput").value.trim() }) });
    renderFileResults(results);
  } catch (error) { showToast(error.message, true); }
});

$("#writeProposalForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/api/v1/files/write-requests", { method: "POST", body: JSON.stringify({ allowed_path_id: $("#writeAllowedPathId").value.trim(), relative_path: $("#writeRelativePath").value.trim(), requested_by: $("#writeRequestedBy").value.trim(), content: $("#writeContent").value }) });
    event.currentTarget.reset();
    showToast(`Yazma talebi oluşturuldu: ${result.id}`);
  } catch (error) { showToast(error.message, true); }
});

$("#saveAdminToken").addEventListener("click", () => {
  adminToken = $("#adminToken").value;
  $("#adminToken").value = "";
  showToast("Yönetici anahtarı yalnızca bu sekme için ayarlandı.");
  loadLlmStatus(); loadRagStatus(); loadAllowedPaths(); loadWriteRequests(); loadAuditLogs();
});

async function loadRagStatus() {
  try {
    const status = await adminApi("/api/v1/admin/rag/status");
    $("#ragStatus").textContent = status.enabled
      ? `Etkin · ${status.embedding_model} · ${status.indexed_documents} belge · ${status.chunks} parça`
      : "Devre dışı · Etkinleştirmek için .env içinde RAG_ENABLED=true ayarlayın.";
    $("#reindexRag").disabled = !status.enabled;
  } catch (error) { showToast(error.message, true); }
}

$("#reindexRag").addEventListener("click", async () => {
  const button = $("#reindexRag");
  button.disabled = true;
  try {
    const result = await adminApi("/api/v1/admin/rag/reindex", { method: "POST" });
    showToast(`${result.indexed_documents} belge denetlendi, ${result.new_or_updated_chunks} parça güncellendi.`);
    await loadRagStatus();
  } catch (error) { showToast(error.message, true); }
  finally { button.disabled = false; }
});

async function loadLlmStatus() {
  try {
    const status = await adminApi("/api/v1/admin/llm/status");
    $("#llmBaseUrl").value = status.base_url;
    $("#llmModel").value = status.model;
    $("#llmApiKey").value = "";
    $("#llmConnectionState").textContent = status.mode === "live" ? "Canlı model etkin" : "Ollama ayarları hazır; sunucu bekleniyor";
  } catch (error) { showToast(error.message, true); }
}

function llmPayload() {
  return {
    base_url: $("#llmBaseUrl").value.trim(),
    model: $("#llmModel").value.trim(),
    api_key: $("#llmApiKey").value || "ollama",
  };
}

$("#testLlmConnection").addEventListener("click", async () => {
  const button = $("#testLlmConnection");
  button.disabled = true;
  try {
    const result = await adminApi("/api/v1/admin/llm/test", { method: "POST", body: JSON.stringify(llmPayload()) });
    $("#llmConnectionState").textContent = "Bağlantı başarılı";
    showToast(`${result.model} modeli erişilebilir.`);
  } catch (error) {
    $("#llmConnectionState").textContent = "Bağlantı başarısız";
    showToast(error.message, true);
  } finally { button.disabled = false; }
});

$("#llmConfigForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const result = await adminApi("/api/v1/admin/llm/configure", { method: "POST", body: JSON.stringify(llmPayload()) });
    $("#llmApiKey").value = "";
    $("#llmConnectionState").textContent = "Canlı model etkin";
    $("#modeLabel").textContent = "Canlı";
    $("#headerMode").textContent = "Canlı model";
    $("#chatDisclaimer").textContent = "Model yanıtları hata içerebilir. Kritik işlemleri ve kaynakları doğrulayın.";
    showToast(result.message);
  } catch (error) { showToast(error.message, true); }
  finally { button.disabled = false; }
});

async function loadAllowedPaths() {
  try {
    const paths = await adminApi("/api/v1/admin/paths");
    const container = $("#allowedPathList");
    if (!paths.length) { container.className = "admin-list empty-state"; container.textContent = "Henüz izinli klasör eklenmedi."; return; }
    container.className = "admin-list";
    container.innerHTML = paths.map((item) => `<div class="admin-row"><div class="admin-row-main"><strong>${escapeHtml(item.label)} · ${item.permission === "read_write" ? "Oku + onaylı yaz" : "Sadece oku"}${item.enabled ? "" : " · Devre dışı"}</strong><code>${escapeHtml(item.root_path)}</code><small>ID: ${escapeHtml(item.id)}</small></div><div class="admin-actions">${item.enabled ? `<button class="action-button" data-index-path="${escapeHtml(item.id)}">İndeksle</button><button class="action-button reject" data-disable-path="${escapeHtml(item.id)}">Yetkiyi kaldır</button>` : ""}</div></div>`).join("");
    $$('[data-index-path]').forEach((button) => button.addEventListener("click", () => indexPath(button.dataset.indexPath)));
    $$('[data-disable-path]').forEach((button) => button.addEventListener("click", () => disablePath(button.dataset.disablePath)));
  } catch (error) { showToast(error.message, true); }
}

async function disablePath(id) {
  if (!window.confirm("Bu klasörün okuma ve yazma yetkisini kaldırmak istiyor musunuz?")) return;
  try {
    await adminApi(`/api/v1/admin/paths/${id}`, { method: "DELETE" });
    await loadAllowedPaths(); await loadRagStatus(); await loadAuditLogs();
    showToast("Klasör yetkisi kaldırıldı; belge parçaları artık arama sonuçlarına dönmez.");
  } catch (error) { showToast(error.message, true); }
}

$("#selectDirectory").addEventListener("click", async () => {
  try {
    const result = await adminApi("/api/v1/admin/select-directory", { method: "POST" });
    if (result.path) {
      $("#rootPath").value = result.path;
      if (!$("#pathLabel").value.trim()) $("#pathLabel").value = result.path.split(/[\\/]/).filter(Boolean).pop() || "Kurumsal klasör";
      showToast("Klasör seçildi. Yetkiyi kontrol edip Klasör ekle düğmesine basın.");
    }
  } catch (error) { showToast(error.message, true); }
});

async function indexPath(id) {
  const button = document.querySelector(`[data-index-path="${CSS.escape(id)}"]`);
  const row = button?.closest(".admin-row");
  const rowMain = row?.querySelector(".admin-row-main");
  const progress = document.createElement("div");
  progress.className = "index-progress";
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-label", "Belge indeksleme devam ediyor");
  progress.innerHTML = '<span></span><small>İndeksleniyor… İlk model yüklemesi birkaç dakika sürebilir.</small>';
  if (button) {
    button.disabled = true;
    button.textContent = "İndeksleniyor…";
  }
  rowMain?.appendChild(progress);
  try {
    const result = await adminApi(`/api/v1/admin/paths/${id}/index`, { method: "POST" });
    showToast(`${result.indexed_files} dosya indekslendi, ${result.skipped_files} dosya atlandı.`);
    await loadRagStatus();
  } catch (error) { showToast(error.message, true); }
  finally {
    progress.remove();
    if (button?.isConnected) {
      button.disabled = false;
      button.textContent = "İndeksle";
    }
  }
}

$("#allowedPathForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const saved = await adminApi("/api/v1/admin/paths", { method: "POST", body: JSON.stringify({ label: $("#pathLabel").value.trim(), root_path: $("#rootPath").value.trim(), permission: $("#pathPermission").value }) });
    event.currentTarget.reset();
    await loadAllowedPaths();
    showToast(`İzinli klasör hazır: ${saved.label || saved.root_path}`);
  } catch (error) { showToast(error.message, true); }
});

async function loadWriteRequests() {
  try {
    const requests = await adminApi("/api/v1/admin/write-requests");
    const container = $("#writeRequestList");
    if (!requests.length) { container.className = "admin-list empty-state"; container.textContent = "Yazma talebi bulunmuyor."; return; }
    container.className = "admin-list";
    container.innerHTML = requests.map((item) => `<div class="admin-row"><div class="admin-row-main"><strong>${escapeHtml(item.operation)} · ${escapeHtml(item.status)}</strong><code>${escapeHtml(item.relative_path)}</code><small>Talep eden: ${escapeHtml(item.requested_by)} · ${escapeHtml(item.created_at)}</small></div>${item.status === "pending" ? `<div class="admin-actions"><button class="action-button approve" data-approve="${item.id}">Onayla</button><button class="action-button reject" data-reject="${item.id}">Reddet</button></div>` : ""}</div>`).join("");
    $$('[data-approve]').forEach((button) => button.addEventListener("click", () => decideWrite(button.dataset.approve, "approve")));
    $$('[data-reject]').forEach((button) => button.addEventListener("click", () => decideWrite(button.dataset.reject, "reject")));
  } catch (error) { showToast(error.message, true); }
}

async function decideWrite(id, decision) {
  const actor = window.prompt("Onaylayan/reddeden kişinin adını girin:");
  if (!actor) return;
  try {
    await adminApi(`/api/v1/admin/write-requests/${id}/${decision}`, { method: "POST", body: JSON.stringify({ actor }) });
    await loadWriteRequests(); await loadAuditLogs();
    showToast(decision === "approve" ? "Yazma işlemi onaylandı ve uygulandı." : "Talep reddedildi.");
  } catch (error) { showToast(error.message, true); }
}

async function loadAuditLogs() {
  try {
    const logs = await adminApi("/api/v1/admin/audit-logs");
    const container = $("#auditList");
    if (!logs.length) { container.className = "admin-list empty-state"; container.textContent = "Henüz denetim kaydı yok."; return; }
    container.className = "admin-list";
    container.innerHTML = logs.map((item) => `<div class="admin-row"><div class="admin-row-main"><strong>${escapeHtml(item.action)} · ${escapeHtml(item.actor)}</strong><code>${escapeHtml(item.target_path)}</code><small>${escapeHtml(item.detail)} · ${escapeHtml(item.created_at)}</small></div></div>`).join("");
  } catch (error) { showToast(error.message, true); }
}

$("#refreshPaths").addEventListener("click", loadAllowedPaths);
$("#refreshWrites").addEventListener("click", loadWriteRequests);
$("#refreshAudit").addEventListener("click", loadAuditLogs);
