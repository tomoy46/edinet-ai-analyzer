const CATEGORIES = ["優待新設", "優待拡充", "優待変更", "優待廃止", "増配", "減配", "配当予想修正", "自社株買い", "決算", "業績予想修正", "TOB・M&A", "その他"];
const state = { disclosures: [], status: {}, sample: false, saved: new Set(JSON.parse(localStorage.getItem("savedSecurities") || "[]")) };
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
const stars = (count) => "★".repeat(count) + "☆".repeat(5 - count);

function saveCodes() {
  localStorage.setItem("savedSecurities", JSON.stringify([...state.saved]));
  $("#savedCount").textContent = state.saved.size;
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

function render() {
  const query = $("#searchInput").value.trim().toLowerCase();
  const category = $("#categoryFilter").value;
  const importance = Number($("#importanceFilter").value);
  const savedOnly = $("#savedOnly").checked;
  const filtered = state.disclosures.filter((item) => {
    const text = `${item.security_code} ${item.company_name} ${item.title}`.toLowerCase();
    return (!query || text.includes(query)) && (!category || item.category === category)
      && item.importance >= importance && (!savedOnly || state.saved.has(item.security_code));
  }).sort((a, b) => Number(state.saved.has(b.security_code)) - Number(state.saved.has(a.security_code))
    || b.published_at.localeCompare(a.published_at));
  $("#visibleCount").textContent = filtered.length;
  $("#importantCount").textContent = filtered.filter((item) => item.importance >= 4).length;
  $("#emptyMessage").hidden = filtered.length !== 0;
  $("#disclosureList").innerHTML = filtered.map((item) => {
    const saved = state.saved.has(item.security_code);
    return `<article class="disclosure${saved ? " saved" : ""}">
      <div class="meta"><time>${formatDate(item.published_at)}</time><div class="company">${escapeHtml(item.security_code)} · ${escapeHtml(item.company_name)}</div></div>
      <div><span class="badge">${escapeHtml(item.category)}</span><h3>${escapeHtml(item.title)}</h3><span class="stars" aria-label="重要度${item.importance}">${stars(item.importance)}</span></div>
      <div class="actions"><a href="${encodeURI(item.pdf_url)}" target="_blank" rel="noopener noreferrer">公式PDF ↗</a><button class="star-button${saved ? " active" : ""}" data-code="${escapeHtml(item.security_code)}" aria-label="保存銘柄を切替">${saved ? "★" : "☆"}</button></div>
    </article>`;
  }).join("");
  document.querySelectorAll(".star-button").forEach((button) => button.onclick = () => toggleSaved(button.dataset.code));
}

function toggleSaved(code) {
  if (state.saved.has(code)) state.saved.delete(code); else state.saved.add(code);
  saveCodes(); render(); renderSavedCodes();
}

function renderSavedCodes() {
  $("#savedCodes").innerHTML = [...state.saved].sort().map((code) => `<button type="button" data-code="${code}" title="押すと削除">${code} ×</button>`).join("") || "まだ登録されていません。";
  document.querySelectorAll("#savedCodes button").forEach((button) => button.onclick = () => toggleSaved(button.dataset.code));
}

async function loadData() {
  try {
    const [dataResponse, statusResponse] = await Promise.all([
      fetch("data/disclosures.json", { cache: "no-store" }),
      fetch("data/status.json", { cache: "no-store" }),
    ]);
    if (!dataResponse.ok || !statusResponse.ok) throw new Error("JSONを読み込めません");
    const data = await dataResponse.json();
    state.status = await statusResponse.json(); state.disclosures = data.disclosures || []; state.sample = Boolean(data.sample);
    $("#lastUpdated").textContent = formatDate(data.last_success_at || state.status.checked_at);
    $("#fetchedCount").textContent = state.status.fetched_count ?? 0;
    $("#statusDot").style.background = state.status.ok ? "var(--accent)" : "var(--danger)";
    if (state.sample) showNotice("画面確認用のサンプルデータです。実際の適時開示ではありません。Actionsを実行すると実データへ置き換わります。", true);
    else if (!state.status.ok) showNotice(state.status.message || "取得に失敗したため、前回のデータを表示しています。", true);
    render();
  } catch (error) {
    showNotice("データを読み込めませんでした。ページを再読み込みしてください。", true);
  }
}

CATEGORIES.forEach((category) => $("#categoryFilter").insertAdjacentHTML("beforeend", `<option>${category}</option>`));
["#searchInput", "#categoryFilter", "#importanceFilter", "#savedOnly"].forEach((selector) => $(selector).addEventListener("input", render));
$("#manageButton").onclick = () => { renderSavedCodes(); $("#savedDialog").showModal(); };
$("#savedForm").onsubmit = (event) => { event.preventDefault(); toggleSaved($("#savedCode").value); $("#savedCode").value = ""; };
$("#themeButton").onclick = () => { document.body.classList.toggle("light"); localStorage.setItem("theme", document.body.classList.contains("light") ? "light" : "dark"); };
if (localStorage.getItem("theme") === "light") document.body.classList.add("light");
saveCodes(); loadData();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
