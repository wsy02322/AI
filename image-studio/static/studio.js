const state = {
  models: [],
  works: [],
  work: null,
  painting: false,
  selecting: false,
};

const $ = (id) => document.getElementById(id);
const imageCanvas = $("image-canvas");
const maskCanvas = $("mask-canvas");
const imageCtx = imageCanvas.getContext("2d");
const maskCtx = maskCanvas.getContext("2d");

async function api(url, options = {}) {
  const res = await fetch(url, { credentials: "same-origin", ...options });
  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) {
    const data = await res.json();
    if (!res.ok || data.ok === false) throw new Error(data.error || res.statusText);
    return data;
  }
  if (res.redirected && /\/login/.test(res.url)) {
    window.location.href = "/login";
    throw new Error("Not signed in");
  }
  if (!res.ok) throw new Error(await res.text());
  return res;
}

function setStatus(msg, isError) {
  const el = $("status");
  el.textContent = msg || "";
  el.className = isError ? "status error" : "status";
}

function currentModel() {
  return state.models.find((m) => m.id === $("model").value) || state.models[0];
}

function hasCanvas() {
  return !!(state.work && state.work.current);
}

function syncActions() {
  const has = hasCanvas();
  const selecting = has && state.selecting;
  $("generate-new").hidden = !has;
  $("select-area").hidden = !has;
  $("brush-wrap").hidden = !selecting;
  $("clear-mask").hidden = !selecting;
  $("select-area").classList.toggle("active", selecting);
  $("primary").textContent = !has ? "Generate" : (selecting ? "Edit selection" : "Edit");
  $("download").hidden = !has;
  $("canvas-wrap").classList.toggle("has-image", has);
  maskCanvas.classList.toggle("painting", selecting);
}

function renderModels() {
  $("model").innerHTML = state.models
    .map((m) => {
      const tag = m.available ? "" : " (key missing)";
      return `<option value="${m.id}">${m.label}${tag}</option>`;
    })
    .join("");
  onModelChange();
}

function onModelChange() {
  const model = currentModel();
  if (!model) return;
  const aspect = $("aspect");
  aspect.innerHTML = `<option value="">Default ${model.default_aspect || ""}</option>` +
    (model.aspects || []).map((a) => `<option value="${a}">${a}</option>`).join("");
  const size = $("size");
  const resolutions = model.resolutions || [];
  size.innerHTML = `<option value="">Default ${model.default_resolution || ""}</option>` +
    resolutions.map((r) => `<option value="${r}">${r}</option>`).join("");
  size.disabled = resolutions.length === 0;
  const quality = $("quality");
  const qualities = model.qualities || [];
  quality.innerHTML = `<option value="">Default</option>` +
    qualities.map((q) => `<option value="${q}">${q}</option>`).join("");
  quality.disabled = qualities.length === 0;
  const keyHint = model.available ? "Direct key ready." : "No key for this provider; requests return 503.";
  let editHint;
  if (model.edit === "mask") {
    editHint = "GPT Image 2 supports pixel selection. Turn on Select area, paint, then Edit selection.";
  } else {
    editHint = "This model edits from the prompt only (no pixel mask). For a brush mask, switch to GPT Image 2.";
  }
  $("model-hint").textContent = `${editHint} ${keyHint} Up to ${model.refs_max} references.`;
  syncActions();
}

function renderWorks() {
  $("works").innerHTML = state.works
    .map((w) => `<li data-id="${w.id}" class="${state.work && state.work.id === w.id ? "active" : ""}">${w.title}</li>`)
    .join("");
}

function renderVersions() {
  const versions = (state.work && state.work.versions) || [];
  $("version-list").innerHTML = versions
    .slice()
    .reverse()
    .map((v) => `<li data-id="${v.id}" class="${state.work.current === v.id ? "active" : ""}">
        <span class="ver-label">${v.kind} · ${v.prompt.slice(0, 36)}</span>
        <button type="button" class="ghost tiny" data-download="${v.file}">Download</button>
      </li>`)
    .join("");
}

function fileUrl(filename) {
  return `/api/works/${state.work.id}/files/${filename}`;
}

function currentFile() {
  if (!state.work || !state.work.current) return null;
  const row = (state.work.versions || []).find((v) => v.id === state.work.current);
  return row ? row.file : null;
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

async function drawWork() {
  const file = currentFile();
  if (!file) {
    imageCtx.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
    clearMask();
    syncActions();
    return;
  }
  const img = await loadImage(fileUrl(file));
  imageCanvas.width = img.naturalWidth;
  imageCanvas.height = img.naturalHeight;
  maskCanvas.width = img.naturalWidth;
  maskCanvas.height = img.naturalHeight;
  imageCtx.drawImage(img, 0, 0);
  clearMask();
  syncActions();
}

function clearMask() {
  maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
}

function canvasPoint(event) {
  const rect = maskCanvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * maskCanvas.width;
  const y = ((event.clientY - rect.top) / rect.height) * maskCanvas.height;
  return { x, y };
}

function paint(event) {
  if (!state.painting || !state.selecting) return;
  const { x, y } = canvasPoint(event);
  const size = Number($("brush").value);
  maskCtx.fillStyle = "rgba(255,255,255,0.72)";
  maskCtx.beginPath();
  maskCtx.arc(x, y, size, 0, Math.PI * 2);
  maskCtx.fill();
}

function maskHasPaint() {
  const data = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height).data;
  for (let i = 3; i < data.length; i += 4) {
    if (data[i] > 10) return true;
  }
  return false;
}

async function exportMask() {
  return await new Promise((resolve) => maskCanvas.toBlob(resolve, "image/png"));
}

function downloadName(filename) {
  const title = ((state.work && state.work.title) || "image")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/^[-._]+|[-._]+$/g, "") || "image";
  const stem = String(filename || "v").replace(/\.png$/i, "").slice(0, 24) || "v";
  return `${title.slice(0, 48)}-${stem}.png`;
}

async function downloadPng(filename) {
  if (!state.work || !filename) return setStatus("Nothing to download.", true);
  try {
    const res = await fetch(`${fileUrl(filename)}?download=1`, { credentials: "same-origin" });
    if (!res.ok) throw new Error("Download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadName(filename);
    a.click();
    URL.revokeObjectURL(url);
    setStatus("Downloaded");
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
}

function isImageFile(file) {
  if (!file) return false;
  if ((file.type || "").startsWith("image/")) return true;
  return /\.(png|jpe?g|webp)$/i.test(file.name || "");
}

async function ingestFile(file) {
  if (!isImageFile(file)) return setStatus("Choose a PNG, JPEG, or WebP image.", true);
  setStatus("Opening…");
  try {
    if (!state.work) await createWork();
    const form = new FormData();
    form.set("image", file, file.name || "paste.png");
    form.set("prompt", file.name || "paste");
    const data = await api(`/api/works/${state.work.id}/upload`, { method: "POST", body: form });
    state.work = data.work;
    state.selecting = false;
    await refreshWorks(state.work.id);
    setStatus("Opened");
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
}

async function refreshWorks(selectId) {
  const data = await api("/api/works");
  state.works = data.works || [];
  if (selectId) {
    const detail = await api(`/api/works/${selectId}`);
    state.work = detail.work;
  } else if (state.work) {
    const still = state.works.find((w) => w.id === state.work.id);
    if (!still) state.work = null;
  }
  if (!hasCanvas()) state.selecting = false;
  renderWorks();
  renderVersions();
  await drawWork();
}

async function createWork() {
  const data = await api("/api/works", { method: "POST", body: new FormData() });
  state.selecting = false;
  await refreshWorks(data.work.id);
}

function promptForm() {
  const form = new FormData();
  form.set("model_id", $("model").value);
  form.set("prompt", $("prompt").value.trim());
  form.set("aspect", $("aspect").value);
  form.set("resolution", $("size").value);
  form.set("quality", $("quality").value);
  if (state.work) form.set("work_id", state.work.id);
  return form;
}

async function generate({ confirmIfCanvas } = {}) {
  const prompt = $("prompt").value.trim();
  if (!prompt) return setStatus("Enter a prompt first.", true);
  if (confirmIfCanvas && hasCanvas()) {
    const ok = window.confirm("This creates a new image. The current one stays in Versions.");
    if (!ok) return;
  }
  const form = promptForm();
  setStatus("Generating…");
  try {
    const data = await api("/api/generate", { method: "POST", body: form });
    state.selecting = false;
    await refreshWorks(data.work_id);
    setStatus("Generated");
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
}

async function edit(useMask) {
  const prompt = $("prompt").value.trim();
  if (!prompt) return setStatus("Describe what to change.", true);
  if (!hasCanvas()) return setStatus("Generate or open an image first.", true);
  if (useMask) {
    const model = currentModel();
    if (!model || model.edit !== "mask") {
      return setStatus("This model has no pixel mask. Switch to GPT Image 2 for selection edit.", true);
    }
    if (!maskHasPaint()) return setStatus("Paint the area to change first.", true);
  }
  const form = promptForm();
  if (useMask) form.set("mask", await exportMask(), "mask.png");
  setStatus(useMask ? "Editing selection…" : "Editing…");
  try {
    const data = await api("/api/edit", { method: "POST", body: form });
    await refreshWorks(data.work_id);
    setStatus("Edited");
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
}

function onPrimary() {
  if (!hasCanvas()) return generate({ confirmIfCanvas: false });
  if (state.selecting) return edit(true);
  return edit(false);
}

function toggleSelect() {
  if (!hasCanvas()) return;
  state.selecting = !state.selecting;
  if (!state.selecting) clearMask();
  syncActions();
}

async function boot() {
  const data = await api("/api/models");
  state.models = data.models || [];
  renderModels();
  await refreshWorks();
  $("model").addEventListener("change", onModelChange);
  $("new-work").addEventListener("click", () => createWork().catch((e) => setStatus(e.message, true)));
  $("primary").addEventListener("click", onPrimary);
  $("generate-new").addEventListener("click", () => generate({ confirmIfCanvas: true }));
  $("select-area").addEventListener("click", toggleSelect);
  $("clear-mask").addEventListener("click", clearMask);
  $("open-file").addEventListener("click", () => $("upload").click());
  $("download").addEventListener("click", () => downloadPng(currentFile()));
  $("upload").addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (file) await ingestFile(file);
  });
  const wrap = $("canvas-wrap");
  wrap.addEventListener("dragover", (event) => {
    event.preventDefault();
    wrap.classList.add("drop-target");
  });
  wrap.addEventListener("dragleave", () => wrap.classList.remove("drop-target"));
  wrap.addEventListener("drop", async (event) => {
    event.preventDefault();
    wrap.classList.remove("drop-target");
    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
    if (file) await ingestFile(file);
  });
  window.addEventListener("paste", async (event) => {
    const items = event.clipboardData && event.clipboardData.items;
    if (!items) return;
    for (const item of items) {
      if (item.kind === "file" && (item.type || "").startsWith("image/")) {
        event.preventDefault();
        const file = item.getAsFile();
        if (file) await ingestFile(file);
        return;
      }
    }
  });
  $("works").addEventListener("click", async (event) => {
    const id = event.target.getAttribute("data-id");
    if (!id) return;
    state.selecting = false;
    await refreshWorks(id);
  });
  $("version-list").addEventListener("click", async (event) => {
    const dl = event.target.closest("[data-download]");
    if (dl) {
      event.preventDefault();
      event.stopPropagation();
      await downloadPng(dl.getAttribute("data-download"));
      return;
    }
    const row = event.target.closest("li[data-id]");
    const id = row && row.getAttribute("data-id");
    if (!id || !state.work) return;
    state.work.current = id;
    renderVersions();
    await drawWork();
  });
  maskCanvas.addEventListener("pointerdown", (event) => {
    if (!state.selecting) return;
    state.painting = true;
    paint(event);
  });
  maskCanvas.addEventListener("pointermove", paint);
  window.addEventListener("pointerup", () => { state.painting = false; });
}

boot().catch((err) => setStatus(err.message, true));
