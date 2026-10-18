// Uploads files from the browser straight to Vercel Blob, so large videos don't pass through the server
// (serverless functions accept at most 4.5 MB per request). Used only when cloud storage is configured.
// Plain XMLHttpRequest (no libraries) so the file's bytes are sent exactly as they are, with progress.
const BLOB_API = "https://vercel.com/api/blob/";
const t = window.studioT || ((key, vars, fallback) => fallback || key);

function putToBlob(pathname, file, token, contentType, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", BLOB_API + "?pathname=" + encodeURIComponent(pathname));
    xhr.setRequestHeader("authorization", "Bearer " + token);
    xhr.setRequestHeader("x-api-version", "11");
    xhr.setRequestHeader("x-vercel-blob-access", "public");
    xhr.setRequestHeader("x-content-length", String(file.size));
    if (contentType) xhr.setRequestHeader("x-content-type", contentType);
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) onProgress((e.loaded / e.total) * 100);
    });
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else {
        let message = t("storage_refused", { status: xhr.status });
        try { message = JSON.parse(xhr.responseText).error.message || message; } catch (err) { /* keep default */ }
        reject(new Error(message));
      }
    };
    xhr.onerror = () => reject(new Error(t("network_error")));
    xhr.send(file);
  });
}

function csrfToken() {
  const input = document.querySelector("input[name=csrfmiddlewaretoken]");
  return input ? input.value : "";
}

async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || t("upload_failed", { status: resp.status }));
  return data;
}

async function uploadOne(file, urls, inQueue, onProgress) {
  const type = file.type || "";
  const permit = await postJSON(urls.token, { name: file.name, type, size: file.size });
  await putToBlob(permit.pathname, file, permit.token, type, onProgress);
  return postJSON(urls.complete, { pathname: permit.pathname, name: file.name, in_queue: inQueue });
}

async function uploadAll(input, status, inQueue) {
  const files = Array.from(input.files || []);
  const urls = { token: input.dataset.tokenUrl, complete: input.dataset.completeUrl };
  const done = [];
  const errors = [];
  for (const [i, file] of files.entries()) {
    const label = t("uploading", { i: i + 1, n: files.length, name: file.name });
    status.textContent = label + "…";
    try {
      done.push(await uploadOne(file, urls, inQueue, (pct) => {
        status.textContent = `${label} (${Math.round(pct)}%)`;
      }));
    } catch (err) {
      errors.push(`${file.name}: ${err.message}`);
    }
  }
  input.value = "";
  status.textContent = errors.length ? errors.join(" · ") : (done.length ? t("uploaded", { n: done.length }) : "");
  status.style.color = errors.length ? "var(--err)" : "";
  return done;
}

document.querySelectorAll("input[type=file][data-direct-upload]").forEach((input) => {
  const status = document.createElement("div");
  status.className = "small muted";
  status.setAttribute("role", "status");
  input.insertAdjacentElement("afterend", status);
  const form = input.form;
  const submitButtons = form ? form.querySelectorAll("button") : [];
  const setBusy = (busy) => submitButtons.forEach((b) => { b.disabled = busy; });

  if (input.dataset.directUpload === "picker") {
    // Post form: upload as soon as files are chosen and select them in the picker.
    input.addEventListener("change", async () => {
      setBusy(true);
      const assets = await uploadAll(input, status, false);
      assets.forEach((a) => window.studioPicker && window.studioPicker.add(a));
      setBusy(false);
    });
  } else if (form) {
    // Library page: upload on submit, then reload to show the new items.
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!input.files || !input.files.length) return;
      setBusy(true);
      const queue = form.querySelector("input[name=add_to_queue]");
      const assets = await uploadAll(input, status, Boolean(queue && queue.checked));
      setBusy(false);
      if (assets.length && status.style.color === "") window.location.reload();
    });
  }
});
