const app = document.querySelector("#app");
let pollTimer;
let adminView = "processes";
let selectedFiles = [];
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const html = escapeHTML;
const bytes = (value) =>
  value > 1048576
    ? `${(value / 1048576).toFixed(1)} MiB`
    : `${Math.ceil(value / 1024)} KiB`;
const badge = (state) =>
  `<span class="badge ${html(state)}">${html(state)}</span>`;
const date = (value) =>
  new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let body;
  try {
    body = await response.json();
  } catch {
    body = {};
  }
  if (!response.ok) {
    if (response.status === 401 && location.pathname !== "/") {
      sessionStorage.setItem("vnizer-return", location.pathname);
      location.href = "/";
    }
    const detail = body.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((x) => x.msg).join(" ")
          : `Request failed (${response.status}).`,
    );
  }
  return body;
}
const post = (path, body = {}) =>
  api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
function notice(text) {
  const box = document.querySelector("#notice");
  box.textContent = text;
  box.hidden = false;
  clearTimeout(box.timer);
  box.timer = setTimeout(() => (box.hidden = true), 6000);
}
function errorAt(id, error) {
  document.querySelector(id).textContent = error.message;
}
async function action(button, work) {
  button.disabled = true;
  try {
    await work();
  } catch (error) {
    notice(error.message);
  } finally {
    button.disabled = false;
  }
}
function recentRows(processes) {
  if (!processes.length)
    return '<p class="empty">Your recent processes will appear here.</p>';
  return processes
    .slice(0, 8)
    .map(
      (p) =>
        `<a class="recent-row" href="/${p.id}"><div class="file-info"><div class="file-name">${html(p.documents[0]?.name || "Process")}${p.documents.length > 1 ? ` +${p.documents.length - 1}` : ""}</div><div class="file-size">${html(date(p.created))}</div></div>${badge(p.state)}</a>`,
    )
    .join("");
}
async function loginPage(session) {
  app.innerHTML = `<div class="login-layout"><section><div class="eyebrow">Your reading, reimagined</div><h1>A new way to<br>listen and learn.</h1><p class="lead">Turn research papers into narrated visual novel videos. Keep the details. Take the reading with you.</p><div class="hint">One PDF. One transcript. Audio and video, ready to download.</div></section><div class="stack"><section class="card"><h2>Welcome to VNizer</h2><p class="muted">${session.auth_required ? "Sign in to open your document studio." : "Your document studio is ready."}</p><form id="login-form">${session.auth_required ? '<div class="field"><label for="username">Username</label><input id="username" autocomplete="username" required></div><div class="field"><label for="password">Password</label><input id="password" type="password" autocomplete="current-password" required></div>' : ""}<p id="login-error" class="error" role="alert"></p><button>${session.auth_required ? "Sign in" : "Enter the studio"} <span aria-hidden="true">→</span></button></form></section><section class="card"><h3>Recent processes</h3><div id="login-recent">${session.auth_required && !session.authenticated ? '<p class="muted">Sign in to view your recent processes.</p>' : ""}</div></section></div></div>`;
  document.querySelector("#login-form").onsubmit = async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      await post("/api/login", {
        username: document.querySelector("#username")?.value || "",
        password: document.querySelector("#password")?.value || "",
      });
      const target = sessionStorage.getItem("vnizer-return");
      sessionStorage.removeItem("vnizer-return");
      location.href =
        target?.startsWith("/") && !target.startsWith("//")
          ? target
          : "/upload";
    } catch (error) {
      errorAt("#login-error", error);
      button.disabled = false;
    }
  };
  if (session.authenticated)
    document.querySelector("#login-recent").innerHTML = recentRows(
      await api("/api/processes"),
    );
}
function updateFiles() {
  document.querySelector("#file-list").innerHTML = selectedFiles
    .map(
      (file, index) =>
        `<div class="file-row"><div class="file-info"><div class="file-name">${html(file.name)}</div><div class="file-size">${bytes(file.size)}</div></div><button class="quiet small" data-remove="${index}" aria-label="Remove ${html(file.name)}">Remove</button></div>`,
    )
    .join("");
  document.querySelector("#convert").disabled = !selectedFiles.length;
  document.querySelector("#file-count").textContent =
    `${selectedFiles.length} / 20 files`;
  document.querySelectorAll("[data-remove]").forEach(
    (button) =>
      (button.onclick = () => {
        selectedFiles.splice(Number(button.dataset.remove), 1);
        updateFiles();
      }),
  );
}
function addFiles(files) {
  for (const file of files) {
    if (
      !file.name.toLowerCase().endsWith(".pdf") ||
      file.size > 100 * 1048576
    ) {
      notice("Use PDF files of at most 100 MiB each.");
      continue;
    }
    if (selectedFiles.length >= 20) {
      notice("Select at most 20 PDF files.");
      break;
    }
    if (
      !selectedFiles.some(
        (f) =>
          f.name === file.name &&
          f.size === file.size &&
          f.lastModified === file.lastModified,
      )
    )
      selectedFiles.push(file);
  }
  updateFiles();
}
async function uploadPage() {
  app.innerHTML = `<section class="hero"><div><div class="eyebrow">Document studio</div><h1>Let your papers<br>tell the story.</h1><p class="lead">Upload your PDFs. Get clear narration, a visual novel video, and a transcript you can keep.</p></div><div class="hero-art" aria-hidden="true"><div class="paper">A different<br>point of view.<div class="paper-lines"></div><div class="paper-lines"></div><div class="paper-lines short"></div></div><div class="wave">${"<i></i>".repeat(15)}</div></div></section><div class="grid"><section class="card"><div class="section-head"><h2>Add your documents</h2><span class="muted" id="file-count">0 / 20 files</span></div><div id="dropzone" class="dropzone" tabindex="0" role="button" aria-label="Browse or drop PDF files"><span class="upload-icon" aria-hidden="true">↑</span><strong>Drop your PDFs here</strong><p class="muted">or click to browse your computer</p><span class="file-size">PDF files · Up to 100 MiB each</span></div><input class="sr-only" id="pdf-files" type="file" accept="application/pdf,.pdf" multiple aria-label="PDF files"><div id="file-list"></div><p id="upload-error" class="error" role="alert"></p><div class="actions"><button id="convert" disabled>Convert documents <span aria-hidden="true">→</span></button><span class="muted" id="upload-status">Services are checked before conversion.</span></div></section><div class="stack"><section class="card"><h2>Made for your next read</h2><ul class="outputs"><li><span class="output-icon">TXT</span><div><strong>Full transcript</strong><div class="file-size">Document text, ready to keep.</div></div></li><li><span class="output-icon">AUDIO</span><div><strong>Listen anywhere</strong><div class="file-size">An audio-only MP4 for your commute.</div></div></li><li><span class="output-icon">VIDEO</span><div><strong>A visual companion</strong><div class="file-size">Narration with a character and text.</div></div></li></ul><div class="hint">You can leave while conversion runs. Return to the process page whenever you are ready.</div></section><section class="card"><h3>Recent processes</h3><div id="recent"></div></section></div></div>`;
  const input = document.querySelector("#pdf-files"),
    drop = document.querySelector("#dropzone");
  input.onchange = () => {
    addFiles(input.files);
    input.value = "";
  };
  drop.onclick = () => input.click();
  drop.onkeydown = (event) => {
    if (["Enter", " "].includes(event.key)) {
      event.preventDefault();
      input.click();
    }
  };
  drop.ondragover = (event) => {
    event.preventDefault();
    drop.classList.add("drag");
  };
  drop.ondragleave = () => drop.classList.remove("drag");
  drop.ondrop = (event) => {
    event.preventDefault();
    drop.classList.remove("drag");
    addFiles(event.dataTransfer.files);
  };
  document.querySelector("#convert").onclick = async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    document.querySelector("#upload-error").textContent = "";
    document.querySelector("#upload-status").textContent =
      "Checking services and uploading…";
    try {
      const health = await post("/api/health-check");
      if (!health.ready) throw new Error(health.errors.join(" "));
      const data = new FormData();
      selectedFiles.forEach((file) => data.append("files", file));
      const process = await api("/api/processes", {
        method: "POST",
        body: data,
      });
      location.href = `/${process.id}`;
    } catch (error) {
      errorAt("#upload-error", error);
      button.disabled = false;
      document.querySelector("#upload-status").textContent =
        "Conversion has not started.";
    }
  };
  updateFiles();
  document.querySelector("#recent").innerHTML = recentRows(
    await api("/api/processes"),
  );
}
const outputNames = {
  transcript: "Transcript · TXT",
  audio: "Audio · MP4",
  video: "Video · MP4",
};
function documentCard(doc, admin = false) {
  const downloads = doc.artifacts.filter((a) => outputNames[a.kind]);
  const stage =
    doc.stage === "transcription" ? "PDF to transcript" : "Speech and video";
  const progress =
    doc.state === "completed"
      ? 100
      : doc.total
        ? Math.round((doc.progress / doc.total) * 100)
        : 0;
  return `<article class="card document"><div class="section-head"><div><h3>${html(doc.name)}</h3><span class="file-size">${doc.pages} page${doc.pages === 1 ? "" : "s"} · Attempt ${doc.attempt}</span></div>${badge(doc.state)}</div><div class="progress-label"><span>${stage}</span><span>${doc.state === "completed" ? "Complete" : `${doc.progress} / ${doc.total || "—"}`}</span></div><progress value="${progress}" max="100" aria-label="${html(doc.name)} progress"></progress>${doc.error ? `<p class="error">${html(doc.error)}</p>` : ""}<div class="actions">${["failed", "canceled"].includes(doc.state) ? `<button class="secondary small" data-retry="${doc.id}" data-stage="${doc.stage}">Retry ${doc.stage === "media" ? "speech and video" : "transcription"}</button>` : ""}${downloads.map((a) => `<a class="button secondary small" href="/api/artifacts/${a.id}" download>${outputNames[a.kind]}</a>`).join("")}</div>${admin ? `<details><summary>All artifacts (${doc.artifacts.length})</summary>${doc.artifacts.map((a) => `<div class="artifact-row"><span>${html(a.name || a.kind)} · ${bytes(a.size)}</span><div class="artifact-actions"><a href="/api/artifacts/${a.id}" download>Download</a><button class="danger small" data-delete-artifact="${a.id}" ${["queued", "parsing", "rendering"].includes(doc.state) ? "disabled" : ""}>Delete file</button></div></div>`).join("")}</details>` : ""}</article>`;
}
function bindRetries(refresh) {
  document.querySelectorAll("[data-retry]").forEach(
    (button) =>
      (button.onclick = () =>
        action(button, async () => {
          await post(`/api/documents/${button.dataset.retry}/retry`, {
            stage: button.dataset.stage,
          });
          notice("Retry queued.");
          await refresh();
        })),
  );
}
async function processPage(id) {
  const process = await api(`/api/processes/${id}`);
  const available = process.documents.some((d) =>
    d.artifacts.some((a) => outputNames[a.kind]),
  );
  app.innerHTML = `<div class="eyebrow">Your conversion</div><div class="section-head"><div><h1>${process.state === "completed" ? "Ready when you are." : process.state === "failed" ? "A step needs attention." : process.state === "canceled" ? "Conversion stopped." : "Your reading is on its way."}</h1><p class="muted">You can close this page and return later. Progress is saved.</p><div class="process-id">Process ${html(id)}</div></div>${badge(process.state)}</div><div class="actions"><a class="button secondary" href="/upload">New conversion</a>${available ? `<a class="button" href="/api/processes/${id}/download" download>Download all outputs</a>` : ""}${["queued", "running"].includes(process.state) ? '<button id="stop" class="danger">Stop conversion</button>' : ""}</div><div id="documents">${process.documents.map((d) => documentCard(d)).join("")}</div>`;
  bindRetries(() => processPage(id));
  if (document.querySelector("#stop"))
    document.querySelector("#stop").onclick = (event) =>
      action(event.currentTarget, async () => {
        await post(`/api/processes/${id}/cancel`);
        notice("Stop requested.");
        await processPage(id);
      });
  clearTimeout(pollTimer);
  if (["queued", "running"].includes(process.state)) scheduleProcessPoll(id);
}
function scheduleProcessPoll(id, delay = 2500) {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(async () => {
    try {
      await processPage(id);
    } catch (error) {
      notice(error.message);
      scheduleProcessPoll(id, 5000);
    }
  }, delay);
}
async function adminPage() {
  adminView = "processes";
  app.innerHTML =
    '<div class="eyebrow">Studio controls</div><h1>Keep everything in order.</h1><p class="lead">Manage conversions, service connections, and the characters that bring your documents to life.</p><div class="tabs" role="tablist"><button data-tab="processes" role="tab" class="active" aria-selected="true">Processes & files</button><button data-tab="settings" role="tab" aria-selected="false">Services</button><button data-tab="avatars" role="tab" aria-selected="false">Avatars</button></div><section id="admin-content"></section>';
  document.querySelectorAll("[data-tab]").forEach(
    (button) =>
      (button.onclick = () =>
        action(button, async () => {
          clearTimeout(pollTimer);
          adminView = button.dataset.tab;
          document.querySelector("#admin-content").innerHTML =
            '<p class="muted">Loading…</p>';
          document.querySelectorAll("[data-tab]").forEach((b) => {
            b.classList.toggle("active", b === button);
            b.setAttribute("aria-selected", String(b === button));
          });
          await {
            processes: adminProcesses,
            settings: adminSettings,
            avatars: adminAvatars,
          }[button.dataset.tab]();
        })),
  );
  await adminProcesses();
}
async function adminProcesses() {
  const processes = await api("/api/processes?include_work=true");
  if (adminView !== "processes") return;
  document.querySelector("#admin-content").innerHTML =
    `<div class="section-head"><h2>All processes <span class="muted">(${processes.length})</span></h2><button id="refresh" class="secondary small">Refresh</button></div>${processes.length ? processes.map((p) => `<section class="process-list"><div class="section-head"><div><a href="/${p.id}" class="file-name">${html(date(p.created))}</a><div class="process-id">${p.id}</div></div><div class="actions">${badge(p.state)}${["queued", "running"].includes(p.state) ? `<button class="secondary small" data-stop="${p.id}">Stop</button>` : ""}<button class="danger small" data-delete-process="${p.id}">Delete process</button></div></div>${p.documents.map((d) => documentCard(d, true)).join("")}</section>`).join("") : '<div class="card empty">No processes yet. Start a conversion in the studio.</div>'}`;
  document.querySelector("#refresh").onclick = (event) =>
    action(event.currentTarget, adminProcesses);
  bindRetries(adminProcesses);
  document.querySelectorAll("[data-stop]").forEach(
    (button) =>
      (button.onclick = () =>
        action(button, async () => {
          await post(`/api/processes/${button.dataset.stop}/cancel`);
          notice("Stop requested.");
          await adminProcesses();
        })),
  );
  for (const kind of ["process", "artifact"])
    document.querySelectorAll(`[data-delete-${kind}]`).forEach(
      (button) =>
        (button.onclick = () =>
          action(button, async () => {
            if (
              !confirm(
                kind === "process"
                  ? "Delete this process and all its files?"
                  : "Delete this file? This action cannot be undone.",
              )
            )
              return;
            await api(
              `/api/${kind === "process" ? "processes" : "artifacts"}/${button.dataset[kind === "process" ? "deleteProcess" : "deleteArtifact"]}`,
              { method: "DELETE" },
            );
            notice("Deleted.");
            await adminProcesses();
          })),
    );
}
async function adminSettings() {
  const settings = await api("/api/settings");
  if (adminView !== "settings") return;
  const fields = (prefix) =>
    `<div class="field"><label for="${prefix}_url">Service URL</label><input id="${prefix}_url" name="${prefix}_url" type="url" value="${html(settings[prefix + "_url"])}" required></div><div class="field"><label for="${prefix}_api_key">API key ${settings[prefix + "_api_key_configured"] ? "(saved)" : "(optional)"}</label><input id="${prefix}_api_key" name="${prefix}_api_key" type="password" autocomplete="new-password" placeholder="Leave empty to keep the saved key"><button type="button" class="quiet small" data-clear-key="${prefix}">Clear saved key</button></div>`;
  document.querySelector("#admin-content").innerHTML =
    `<form id="settings-form" class="card"><div class="form-grid"><section><h2>PDF to text</h2><p class="muted">An image-capable Qwen service.</p>${fields("ftt")}<div class="field"><label for="ftt_model">Model name</label><input id="ftt_model" name="ftt_model" value="${html(settings.ftt_model)}" placeholder="Detect from the service"></div></section><section><h2>Text to speech</h2><p class="muted">The VNizer Qwen TTS service.</p>${fields("tts")}<div class="field"><label for="speaker">Speaker</label><input id="speaker" name="speaker" value="${html(settings.speaker)}" required></div><div class="field"><label for="language">Language</label><input id="language" name="language" value="${html(settings.language)}" required></div></section></div><div class="hint">Changes apply to new processes and retries. Running attempts keep their current settings.</div><p id="settings-error" class="error" role="alert"></p><div class="actions"><button>Save settings</button><button type="button" id="check-services" class="secondary">Check saved connections</button></div><p id="health-result" class="muted" aria-live="polite"></p></form>`;
  const clearKeys = new Set();
  document.querySelectorAll("[data-clear-key]").forEach(
    (button) =>
      (button.onclick = () => {
        clearKeys.add(button.dataset.clearKey + "_api_key");
        button.textContent = "Key will be cleared on save";
      }),
  );
  document.querySelector("#settings-form").onsubmit = async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      const values = Object.fromEntries(new FormData(event.currentTarget));
      for (const key of ["ftt_api_key", "tts_api_key"])
        if (!values[key] && !clearKeys.has(key)) delete values[key];
      await post("/api/settings", values);
      notice("Settings saved.");
      await adminSettings();
    } catch (error) {
      errorAt("#settings-error", error);
    } finally {
      button.disabled = false;
    }
  };
  document.querySelector("#check-services").onclick = (event) =>
    action(event.currentTarget, async () => {
      document.querySelector("#health-result").textContent = "Checking…";
      const result = await post("/api/health-check");
      document.querySelector("#health-result").textContent = result.ready
        ? "Both services are ready."
        : result.errors.join(" ");
    });
}
async function adminAvatars() {
  const avatars = await api("/api/avatars");
  if (adminView !== "avatars") return;
  document.querySelector("#admin-content").innerHTML =
    `<div class="grid"><section class="card"><h2>Character library</h2><p class="muted">Select one character for each mood. Running attempts keep their current assets.</p><div class="avatar-grid">${avatars.map((a) => `<article class="avatar-card">${a.media_type === "video" ? `<video src="/api/avatars/${a.id}/preview" muted loop autoplay playsinline aria-label="${html(a.name)}"></video>` : `<img src="/api/avatars/${a.id}/preview" alt="${html(a.name)}" loading="lazy">`}<h3>${html(a.name)}</h3><div class="file-size">${html(a.mood)}</div><div class="actions">${a.selected ? '<span class="badge completed">Selected</span>' : `<button class="secondary small" data-select-avatar="${a.id}">Select</button>`}<button class="danger small" data-delete-avatar="${a.id}">Delete</button></div></article>`).join("")}</div></section><form id="avatar-form" class="card"><h2>Add an avatar</h2><p class="muted">Use an image or a clip of up to 30 seconds. Maximum file size: 50 MiB.</p><div class="field"><label for="avatar-name">Name</label><input id="avatar-name" name="name" maxlength="120" required></div><div class="field"><label for="avatar-mood">Mood</label><select id="avatar-mood" name="mood">${["neutral", "explaining", "curious", "positive", "serious"].map((m) => `<option>${m}</option>`).join("")}</select></div><div class="field"><label for="avatar-file">Avatar file</label><input id="avatar-file" name="file" type="file" accept=".png,.jpg,.jpeg,.gif,.webp,.mp4,.webm" required></div><p id="avatar-error" class="error" role="alert"></p><button>Upload avatar</button></form></div>`;
  document.querySelector("#avatar-form").onsubmit = async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const button = event.submitter;
    button.disabled = true;
    try {
      await api("/api/avatars", { method: "POST", body: data });
      notice("Avatar uploaded. Select it to use it.");
      await adminAvatars();
    } catch (error) {
      errorAt("#avatar-error", error);
    } finally {
      button.disabled = false;
    }
  };
  document.querySelectorAll("[data-select-avatar]").forEach(
    (button) =>
      (button.onclick = () =>
        action(button, async () => {
          await post(`/api/avatars/${button.dataset.selectAvatar}/select`);
          await adminAvatars();
        })),
  );
  document.querySelectorAll("[data-delete-avatar]").forEach(
    (button) =>
      (button.onclick = () =>
        action(button, async () => {
          if (!confirm("Delete this avatar?")) return;
          await api(`/api/avatars/${button.dataset.deleteAvatar}`, {
            method: "DELETE",
          });
          await adminAvatars();
        })),
  );
}
async function start() {
  const session = await api("/api/session");
  document.querySelector("#logout").hidden =
    !session.auth_required || !session.authenticated;
  document.querySelector("#logout").onclick = async () => {
    await post("/api/logout");
    location.href = "/";
  };
  if (location.pathname === "/") return loginPage(session);
  if (!session.authenticated) {
    sessionStorage.setItem("vnizer-return", location.pathname);
    location.href = "/";
    return;
  }
  if (location.pathname === "/upload") return uploadPage();
  if (location.pathname === "/admin") return adminPage();
  return processPage(location.pathname.slice(1));
}
start().catch((error) => {
  app.innerHTML = `<section class="card"><h1>Unable to open this page.</h1><p class="error">${html(error.message)}</p><a class="button secondary" href="/upload">Return to the studio</a></section>`;
});
