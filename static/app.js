const $ = (id) => document.getElementById(id);

const urlInput = $("urlInput");
const probeForm = $("probeForm");
const probeBtn = $("probeBtn");
const pasteBtn = $("pasteBtn");
const previewBody = $("previewBody");
const emptyState = $("emptyState");
const qualityEl = $("quality");
const downloadBtn = $("downloadBtn");
const cancelBtn = $("cancelBtn");
const progressBox = $("progressBox");
const barFill = $("barFill");
const progressLabel = $("progressLabel");
const progressPct = $("progressPct");
const errorBox = $("errorBox");
const successBox = $("successBox");
const historyList = $("historyList");

const proxyInput = $("proxyInput");
proxyInput.value = localStorage.getItem("pulse-proxy") || "";
proxyInput.addEventListener("change", () => {
  localStorage.setItem("pulse-proxy", proxyInput.value.trim());
});

function payload(extra = {}) {
  const proxy = proxyInput.value.trim();
  return { ...extra, proxy: proxy || null };
}

function show(el, on) {
  el.classList.toggle("hidden", !on);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join(" ") : detail;
    throw new Error(message || data.error || res.statusText);
  }
  return data;
}

function setBusy(busy) {
  probeBtn.disabled = busy;
  probeBtn.textContent = busy ? "Working…" : "Fetch";
}

function fillStatus(status) {
  $("statusPills").innerHTML = [
    ["yt-dlp " + status.yt_dlp, true],
    [status.ffmpeg ? "FFmpeg ready" : "No system FFmpeg", status.ffmpeg],
    [status.cookies ? "cookies.txt loaded" : "No cookies.txt", status.cookies],
  ]
    .map(([text, ok]) => `<span class="pill ${ok ? "ok" : ""}">${text}</span>`)
    .join("");
}

function thumbSrc(url) {
  if (!url) return "";
  return "/api/thumb?url=" + encodeURIComponent(url);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fillPreview(info) {
  current = info;
  emptyState.classList.add("hidden");
  previewBody.classList.remove("hidden");
  $("title").textContent = info.title;
  $("uploader").textContent = info.uploader || info.extractor || "";
  $("platformBadge").textContent = info.platform;
  $("duration").textContent = info.duration_text || "";
  $("thumb").src = thumbSrc(info.thumbnail);
  $("playlistNote").textContent = info.playlist_note || "";
  show(errorBox, false);
  show(successBox, false);
  show(progressBox, false);
  show(cancelBtn, false);

  const heights = new Set((info.formats || []).map((f) => String(f.height)));
  const options = [["best", "Best available"]];
  ["2160", "1440", "1080", "720", "480", "360"].forEach((h) => {
    if (heights.has(h) || h === "1080" || h === "720") {
      options.push([h, h + "p"]);
    }
  });
  options.push(["audio", info.ffmpeg ? "Audio only (MP3)" : "Audio only"]);
  qualityEl.innerHTML = options
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
    .join("");
}

async function loadHistory() {
  const items = await api("/api/history");
  if (!items.length) {
    historyList.innerHTML = '<li class="filename">Downloads will show up here.</li>';
    return;
  }
  historyList.innerHTML = items
    .map(
      (item) => `
      <li>
        <button data-path="${encodeURIComponent(item.path || "")}" ${item.exists ? "" : "disabled"}>
          ${escapeHtml(item.title || item.filename)}
          <span class="filename">${escapeHtml(item.platform || "")} · ${escapeHtml(item.size_text || "")} · ${escapeHtml(item.quality || "")}</span>
        </button>
      </li>`
    )
    .join("");
}

async function pollJob() {
  if (!jobId) return;
  try {
    const job = await api("/api/jobs/" + jobId);
    show(progressBox, true);
    const pct = job.percent || 0;
    barFill.style.width = pct + "%";
    progressPct.textContent = Math.round(pct) + "%";
    const bits = [job.message || job.status, job.speed, job.eta].filter(Boolean);
    progressLabel.textContent = bits.join(" · ");

    if (job.status === "done") {
      jobId = null;
      show(cancelBtn, false);
      downloadBtn.disabled = false;
      show(successBox, true);
      successBox.textContent = "Saved to downloads: " + (job.result?.filename || "");
      loadHistory();
      return;
    }
    if (job.status === "error") {
      jobId = null;
      show(cancelBtn, false);
      downloadBtn.disabled = false;
      show(errorBox, true);
      errorBox.textContent = job.error || "Download failed.";
      return;
    }
    pollTimer = setTimeout(pollJob, 500);
  } catch (err) {
    pollTimer = setTimeout(pollJob, 1200);
  }
}

probeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;
  setBusy(true);
  show(errorBox, false);
  try {
    const info = await api("/api/probe", {
      method: "POST",
      body: JSON.stringify(payload({ url })),
    });
    fillPreview(info);
  } catch (err) {
    emptyState.classList.add("hidden");
    previewBody.classList.remove("hidden");
    show(errorBox, true);
    errorBox.textContent = err.message;
  } finally {
    setBusy(false);
  }
});

pasteBtn.addEventListener("click", async () => {
  try {
    urlInput.value = await navigator.clipboard.readText();
    urlInput.focus();
  } catch {
    urlInput.focus();
  }
});

downloadBtn.addEventListener("click", async () => {
  if (!current) return;
  downloadBtn.disabled = true;
  show(errorBox, false);
  show(successBox, false);
  show(progressBox, true);
  show(cancelBtn, true);
  barFill.style.width = "2%";
  progressLabel.textContent = "starting";
  progressPct.textContent = "0%";
  try {
    const job = await api("/api/download", {
      method: "POST",
      body: JSON.stringify(
        payload({
          url: current.webpage_url || urlInput.value.trim(),
          quality: qualityEl.value,
        })
      ),
    });
    jobId = job.id;
    pollJob();
  } catch (err) {
    downloadBtn.disabled = false;
    show(cancelBtn, false);
    show(errorBox, true);
    errorBox.textContent = err.message;
  }
});

cancelBtn.addEventListener("click", async () => {
  if (!jobId) return;
  await api("/api/jobs/" + jobId + "/cancel", { method: "POST" });
});

$("openFolderBtn").addEventListener("click", () => {
  api("/api/open-folder", { method: "POST" });
});

historyList.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-path]");
  if (!btn || btn.disabled) return;
  api("/api/open-file?path=" + btn.dataset.path, { method: "POST" });
});

api("/api/status").then(fillStatus).catch(() => {});
loadHistory().catch(() => {});
