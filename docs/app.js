const CATEGORIES = ["優待新設", "優待拡充", "優待変更", "優待廃止", "増配", "減配", "自社株買い", "決算", "業績予想修正", "TOB", "M&A", "その他"];
const appUrl = new URL(document.currentScript.src, document.baseURI);
const basePath = new URL("./", appUrl);
const updateApiUrl = document.querySelector('meta[name="update-api-url"]')?.content.replace(/\/$/, "");
const UPDATE_POLL_INTERVAL = 3000;
const UPDATE_POLL_RETRY_LIMIT = 5;
const RETRYABLE_POLL_STATUSES = new Set([403, 404, 500]);
function loadFavorites() {
  try {
    const stored = localStorage.getItem("favoriteSecurities") || localStorage.getItem("savedSecurities") || "[]";
    const codes = JSON.parse(stored);
    return new Set(Array.isArray(codes) ? codes : []);
  } catch (error) { return new Set(); }
}
function loadReadItems() {
  try {
    const ids = JSON.parse(localStorage.getItem("readDisclosures") || "[]");
    return new Set(Array.isArray(ids) ? ids : []);
  } catch (error) { return new Set(); }
}
const state = { disclosures: [], status: {}, sample: false, saved: loadFavorites(), read: loadReadItems() };
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
const stars = (count) => "★".repeat(count) + "☆".repeat(5 - count);
const impactClass = (impact) => ({ "プラス": "positive", "マイナス": "negative" })[impact] || "neutral";

function renderAiSummary(ai) {
  if (!ai || !Array.isArray(ai.summary)) return "";
  const points = Array.isArray(ai.key_points) ? ai.key_points.slice(0, 3) : [];
  return `<section class="ai-summary"><div class="ai-heading"><strong>AI要約</strong><span class="impact impact-${impactClass(ai.impact)}">株価への影響：${escapeHtml(ai.impact)}</span></div>
    <ul>${ai.summary.slice(0, 3).map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>
    ${points.length ? `<div class="key-points"><b>重要ポイント</b><ul>${points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul></div>` : ""}
    <p class="caution"><b>注意点：</b>${escapeHtml(ai.caution || "公式PDFをご確認ください。")}</p></section>`;
}

function saveCodes() {
  localStorage.setItem("favoriteSecurities", JSON.stringify([...state.saved]));
}

function saveReadItems() { localStorage.setItem("readDisclosures", JSON.stringify([...state.read])); }
function dateKey(value) { return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(new Date(value)); }
function todayKey() { return dateKey(new Date()); }
function isBenefit(item) { return item.category.startsWith("優待"); }
function categoryClass(category) {
  if (category.startsWith("優待")) return "benefit";
  if (["増配", "減配"].includes(category)) return "dividend";
  if (["決算", "業績予想修正"].includes(category)) return "earnings";
  if (["TOB", "M&A"].includes(category)) return "ma";
  if (category === "自社株買い") return "buyback";
  return "other";
}

function formatDate(value, withDate = true) {
  if (!value) return "未取得";
  return new Intl.DateTimeFormat("ja-JP", withDate
    ? { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }
    : { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function showNotice(message, error = false) {
  const notice = $("#notice");
  notice.textContent = message;
  notice.className = `notice show${error ? " error" : ""}`;
}

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function readApiResponse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.error || "更新APIとの通信に失敗しました。");
    error.status = response.status;
    error.code = body.code || body.error_code;
    throw error;
  }
  return body;
}

function updateErrorMessage(error) {
  if (error.code === "method_not_allowed" || error.status === 405) {
    return "更新APIで許可されていない操作です。管理者へお問い合わせください。";
  }
  return error.message || "データ更新に失敗しました。しばらくしてから再度お試しください。";
}

async function pollUpdate(runId) {
  let consecutiveFailures = 0;
  while (true) {
    await wait(UPDATE_POLL_INTERVAL);
    try {
      const response = await fetch(`${updateApiUrl}?run_id=${encodeURIComponent(runId)}`, { cache: "no-store" });
      const run = await readApiResponse(response);
      consecutiveFailures = 0;
      if (run.status !== "completed") continue;
      if (run.conclusion !== "success") {
        const error = new Error(run.error || "データ更新に失敗しました。しばらくしてから再度お試しください。");
        error.code = run.code || run.error_code;
        throw error;
      }
      return;
    } catch (error) {
      if (!RETRYABLE_POLL_STATUSES.has(error.status)) throw error;
      consecutiveFailures += 1;
      if (consecutiveFailures >= UPDATE_POLL_RETRY_LIMIT) {
        throw new Error("更新状況を確認できませんでした。時間をおいて、もう一度更新してください。");
      }
      showNotice(`更新状況を再確認しています（${consecutiveFailures}/${UPDATE_POLL_RETRY_LIMIT}）…`);
    }
  }
}

async function requestUpdate() {
  const button = $("#updateButton");
  if (!updateApiUrl || updateApiUrl.includes("YOUR-WORKER")) {
    showNotice("更新APIが未設定です。管理者へお問い合わせください。", true);
    return;
  }

  button.disabled = true;
  showNotice("更新処理を開始しています。この画面のままお待ちください。");
  try {
    const started = await readApiResponse(await fetch(updateApiUrl, { method: "POST" }));
    if (!started.run_id) throw new Error("更新状況を確認するための情報を取得できませんでした。");
    button.classList.add("updating");
    button.querySelector(".update-label").textContent = "更新中…";
    showNotice("更新開始。GitHub Actionsの完了までこの画面のままお待ちください。");
    await pollUpdate(started.run_id);
    showNotice("更新が完了しました。画面を再読み込みします。");
    window.location.reload();
  } catch (error) {
    showNotice(updateErrorMessage(error), true);
    button.disabled = false;
    button.classList.remove("updating");
    button.querySelector(".update-label").textContent = "更新";
  }
}

function render() {
  const query = $("#searchInput").value.trim().toLowerCase();
  const category = $("#categoryFilter").value;
  const importance = Number($("#importanceFilter").value);
  const savedOnly = $("#savedOnly").checked;
  const sortOrder = $("#sortOrder").value;
  const currentDate = todayKey();
  const filtered = state.disclosures.filter((item) => {
    const text = `${item.security_code} ${item.company_name} ${item.title}`.toLowerCase();
    return (!query || text.includes(query)) && (!category || item.category === category) && item.importance >= importance
      && (!savedOnly || state.saved.has(item.security_code)) && (!$("#todayOnly").checked || dateKey(item.published_at) === currentDate)
      && (!$("#unreadOnly").checked || !state.read.has(item.id)) && (!$("#importantOnly").checked || item.importance >= 4)
      && (!$("#benefitOnly").checked || isBenefit(item)) && (!$("#dividendOnly").checked || ["増配", "減配"].includes(item.category))
      && (!$("#earningsOnly").checked || ["決算", "業績予想修正"].includes(item.category))
      && (!$("#maOnly").checked || ["TOB", "M&A"].includes(item.category));
  }).sort((a, b) => {
    if (sortOrder === "oldest") return a.published_at.localeCompare(b.published_at);
    if (sortOrder === "importance") return b.importance - a.importance || b.published_at.localeCompare(a.published_at);
    if (sortOrder === "company") return a.company_name.localeCompare(b.company_name, "ja") || b.published_at.localeCompare(a.published_at);
    if (sortOrder === "code") return a.security_code.localeCompare(b.security_code) || b.published_at.localeCompare(a.published_at);
    return b.published_at.localeCompare(a.published_at);
  });
  $("#visibleCount").textContent = `${filtered.length}件`;
  $("#todayCount").textContent = state.disclosures.filter((item) => dateKey(item.published_at) === currentDate).length;
  $("#unreadCount").textContent = state.disclosures.filter((item) => !state.read.has(item.id)).length;
  $("#importantCount").textContent = state.disclosures.filter((item) => item.importance >= 4).length;
  $("#benefitCount").textContent = state.disclosures.filter(isBenefit).length;
  $("#emptyMessage").hidden = filtered.length !== 0;
  $("#disclosureList").innerHTML = filtered.map((item) => {
    const saved = state.saved.has(item.security_code);
    const read = state.read.has(item.id);
    return `<article class="disclosure${saved ? " saved" : ""}${read ? " read" : " unread"}">
      <div class="meta"><span class="read-state">${read ? "既読" : "未読"}</span><br><time>${formatDate(item.published_at)}</time><div class="company">${escapeHtml(item.security_code)} · ${escapeHtml(item.company_name)}</div></div>
      <div><span class="badge category-${categoryClass(item.category)}">${escapeHtml(item.category)}</span><h3>${escapeHtml(item.title)}</h3><span class="stars importance-${item.importance}" aria-label="重要度${item.importance}">${stars(item.importance)}</span>${renderAiSummary(item.ai_summary)}</div>
      <div class="actions"><a class="pdf-link" data-id="${escapeHtml(item.id)}" href="${encodeURI(item.pdf_url)}" target="_blank" rel="noopener noreferrer">TDnet PDF ↗</a><button class="star-button${saved ? " active" : ""}" data-code="${escapeHtml(item.security_code)}" aria-label="お気に入りを切替">${saved ? "★" : "☆"}</button></div>
    </article>`;
  }).join("");
  document.querySelectorAll(".star-button").forEach((button) => button.onclick = () => toggleSaved(button.dataset.code));
  document.querySelectorAll(".pdf-link").forEach((link) => link.onclick = () => markRead(link.dataset.id));
}

function markRead(id) { state.read.add(id); saveReadItems(); setTimeout(render, 0); }

function toggleSaved(code) {
  if (state.saved.has(code)) state.saved.delete(code); else state.saved.add(code);
  saveCodes(); render(); renderSavedCodes();
}

function renderSavedCodes() {
  $("#savedCodes").innerHTML = [...state.saved].sort().map((code) => `<button type="button" data-code="${code}" title="押すと削除">${code} ×</button>`).join("") || "お気に入りはまだありません。";
  document.querySelectorAll("#savedCodes button").forEach((button) => button.onclick = () => toggleSaved(button.dataset.code));
}

async function loadData() {
  try {
    const [dataResponse, statusResponse] = await Promise.all([
      fetch(new URL("data/disclosures.json", basePath), { cache: "no-store" }),
      fetch(new URL("data/status.json", basePath), { cache: "no-store" }),
    ]);
    if (!dataResponse.ok || !statusResponse.ok) throw new Error("JSONを読み込めません");
    const data = await dataResponse.json();
    state.status = await statusResponse.json(); state.disclosures = data.disclosures || []; state.sample = Boolean(data.sample);
    $("#lastUpdated").textContent = formatDate(data.last_success_at || state.status.checked_at);
    $("#statusDot").style.background = state.status.ok ? "var(--accent)" : "var(--danger)";
    if (state.sample) showNotice("画面確認用のサンプルデータです。実際の適時開示ではありません。Actionsを実行すると実データへ置き換わります。", true);
    else if (!state.status.ok) showNotice(state.status.message || "取得に失敗したため、前回のデータを表示しています。", true);
    render();
  } catch (error) {
    showNotice("データを読み込めませんでした。ページを再読み込みしてください。", true);
  }
}

CATEGORIES.forEach((category) => $("#categoryFilter").insertAdjacentHTML("beforeend", `<option>${category}</option>`));
const FILTERS = ["#searchInput", "#categoryFilter", "#importanceFilter", "#sortOrder", "#todayOnly", "#unreadOnly", "#savedOnly", "#importantOnly", "#benefitOnly", "#dividendOnly", "#earningsOnly", "#maOnly"];
FILTERS.forEach((selector) => $(selector).addEventListener("input", render));
$("#markAllRead").onclick = () => { state.disclosures.forEach((item) => state.read.add(item.id)); saveReadItems(); render(); };
$("#resetRead").onclick = () => { state.read.clear(); saveReadItems(); render(); };
$("#manageButton").onclick = () => { renderSavedCodes(); $("#savedDialog").showModal(); };
$("#savedForm").onsubmit = (event) => { event.preventDefault(); toggleSaved($("#savedCode").value); $("#savedCode").value = ""; };
$("#themeButton").onclick = () => { document.body.classList.toggle("light"); localStorage.setItem("theme", document.body.classList.contains("light") ? "light" : "dark"); };
$("#updateButton").onclick = requestUpdate;
if (localStorage.getItem("theme") === "light") document.body.classList.add("light");
saveCodes(); loadData();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
