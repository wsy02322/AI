const state = {
  models: [],
  works: [],
  work: null,
  painting: false,
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
    throw new Error("未登录");
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

function renderModels() {
  $("model").innerHTML = state.models
    .map((m) => {
      const tag = m.available ? "" : "（钥匙未注入）";
      return `<option value="${m.id}">${m.label}${tag}</option>`;
    })
    .join("");
  onModelChange();
}

function onModelChange() {
  const model = currentModel();
  if (!model) return;
  const aspect = $("aspect");
  aspect.innerHTML = `<option value="">默认 ${model.default_aspect || ""}</option>` +
    (model.aspects || []).map((a) => `<option value="${a}">${a}</option>`).join("");
  const size = $("size");
  const resolutions = model.resolutions || [];
  size.innerHTML = `<option value="">默认 ${model.default_resolution || ""}</option>` +
    resolutions.map((r) => `<option value="${r}">${r}</option>`).join("");
  size.disabled = resolutions.length === 0;
  const quality = $("quality");
  const qualities = model.qualities || [];
  quality.innerHTML = `<option value="">默认</option>` +
    qualities.map((q) => `<option value="${q}">${q}</option>`).join("");
  quality.disabled = qualities.length === 0;
  const editHint = model.edit === "mask" ? "可用笔刷选区（OpenAI 透明=编辑区）" : "语义编辑：按提示改当前图，没有像素蒙版";
  const keyHint = model.available ? "直连已就绪" : "这台机器还没注入对应钥匙，生成会返回 503";
  $("model-hint").textContent = `${editHint}。${keyHint}。参考上限 ${model.refs_max}。`;
  $("edit-mask").disabled = model.edit !== "mask";
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
    .map((v) => `<li data-id="${v.id}" class="${state.work.current === v.id ? "active" : ""}">${v.kind} · ${v.prompt.slice(0, 36)}</li>`)
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
    return;
  }
  const img = await loadImage(fileUrl(file));
  imageCanvas.width = img.naturalWidth;
  imageCanvas.height = img.naturalHeight;
  maskCanvas.width = img.naturalWidth;
  maskCanvas.height = img.naturalHeight;
  imageCtx.drawImage(img, 0, 0);
  clearMask();
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
  if (!state.painting) return;
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
  renderWorks();
  renderVersions();
  await drawWork();
}

async function createWork() {
  const data = await api("/api/works", { method: "POST", body: new FormData() });
  await refreshWorks(data.work.id);
}

async function generate() {
  const prompt = $("prompt").value.trim();
  if (!prompt) return setStatus("先写提示词", true);
  const form = new FormData();
  form.set("model_id", $("model").value);
  form.set("prompt", prompt);
  form.set("aspect", $("aspect").value);
  form.set("resolution", $("size").value);
  form.set("quality", $("quality").value);
  if (state.work) form.set("work_id", state.work.id);
  setStatus("生成中…");
  try {
    const data = await api("/api/generate", { method: "POST", body: form });
    await refreshWorks(data.work_id);
    setStatus("已生成");
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
}

async function edit(useMask) {
  const prompt = $("prompt").value.trim();
  if (!prompt) return setStatus("先写要改什么", true);
  if (!state.work || !state.work.current) return setStatus("先生成或上传一张底图", true);
  const form = new FormData();
  form.set("model_id", $("model").value);
  form.set("prompt", prompt);
  form.set("work_id", state.work.id);
  form.set("aspect", $("aspect").value);
  form.set("resolution", $("size").value);
  form.set("quality", $("quality").value);
  if (useMask) {
    if (!maskHasPaint()) return setStatus("先在图上涂要改的区域", true);
    form.set("mask", await exportMask(), "mask.png");
  }
  setStatus(useMask ? "按选区编辑中…" : "语义编辑中…");
  try {
    const data = await api("/api/edit", { method: "POST", body: form });
    await refreshWorks(data.work_id);
    setStatus("已编辑");
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
}

async function boot() {
  const data = await api("/api/models");
  state.models = data.models || [];
  renderModels();
  await refreshWorks();
  $("model").addEventListener("change", onModelChange);
  $("new-work").addEventListener("click", () => createWork().catch((e) => setStatus(e.message, true)));
  $("generate").addEventListener("click", generate);
  $("edit").addEventListener("click", () => edit(false));
  $("edit-mask").addEventListener("click", () => edit(true));
  $("clear-mask").addEventListener("click", clearMask);
  $("upload").addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!file) return;
    try {
      if (!state.work) await createWork();
      const form = new FormData();
      form.set("image", file, file.name);
      form.set("prompt", file.name);
      const data = await api(`/api/works/${state.work.id}/upload`, { method: "POST", body: form });
      state.work = data.work;
      await refreshWorks(state.work.id);
      setStatus("已打开图片");
    } catch (err) {
      setStatus(String(err.message || err), true);
    }
  });
  $("works").addEventListener("click", async (event) => {
    const id = event.target.getAttribute("data-id");
    if (!id) return;
    await refreshWorks(id);
  });
  $("version-list").addEventListener("click", async (event) => {
    const id = event.target.getAttribute("data-id");
    if (!id || !state.work) return;
    state.work.current = id;
    renderVersions();
    await drawWork();
  });
  maskCanvas.addEventListener("pointerdown", (event) => {
    state.painting = true;
    paint(event);
  });
  maskCanvas.addEventListener("pointermove", paint);
  window.addEventListener("pointerup", () => { state.painting = false; });
}

boot().catch((err) => setStatus(err.message, true));
