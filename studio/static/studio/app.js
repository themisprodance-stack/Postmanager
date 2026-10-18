(function () {
  "use strict";

  // Translated texts come from the page (see js_i18n in context_processors.py).
  let texts = {};
  try { texts = JSON.parse(document.getElementById("studio-i18n").textContent); } catch (err) { texts = {}; }
  function t(key, vars, fallback) {
    let text = texts[key] || fallback || key;
    Object.entries(vars || {}).forEach(([k, v]) => { text = text.replace("%(" + k + ")s", v); });
    return text;
  }
  window.studioT = t;

  function csrfToken() {
    const input = document.querySelector("input[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  // Ordered media picker: clicking tiles adds/removes them; the order is the carousel order.
  const picker = document.querySelector("[data-media-picker]");
  const mediaInput = document.getElementById("id_media_ids");
  function selectedIds() {
    return mediaInput && mediaInput.value ? mediaInput.value.split(",").filter(Boolean) : [];
  }
  function renderSelection() {
    if (!picker) return;
    const ids = selectedIds();
    picker.querySelectorAll("[data-asset]").forEach((tile) => {
      const pos = ids.indexOf(tile.dataset.asset);
      tile.classList.toggle("selected", pos >= 0);
      tile.setAttribute("aria-pressed", pos >= 0 ? "true" : "false");
      tile.querySelector(".order").textContent = pos >= 0 ? pos + 1 : "";
    });
    const count = document.querySelector("[data-selected-count]");
    if (count) count.textContent = ids.length ? t("selected", { n: ids.length }) : t("none_selected");
    updateHint();
  }
  if (picker && mediaInput) {
    picker.addEventListener("click", (event) => {
      const tile = event.target.closest("[data-asset]");
      if (!tile) return;
      event.preventDefault();
      const ids = selectedIds();
      const pos = ids.indexOf(tile.dataset.asset);
      if (pos >= 0) ids.splice(pos, 1);
      else ids.push(tile.dataset.asset);
      mediaInput.value = ids.join(",");
      renderSelection();
    });
    renderSelection();
  }

  // Used by direct uploads to add a freshly uploaded file to the picker and select it.
  window.studioPicker = {
    add(asset) {
      if (!mediaInput) return;
      if (picker) {
        const tile = document.createElement("button");
        tile.type = "button";
        tile.className = "media-tile";
        tile.dataset.asset = String(asset.id);
        tile.title = asset.title;
        const media = document.createElement(asset.is_video ? "video" : "img");
        media.src = asset.url;
        if (asset.is_video) { media.muted = true; media.preload = "metadata"; }
        tile.appendChild(media);
        if (asset.is_video) {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = t("video");
          tile.appendChild(tag);
        }
        const order = document.createElement("span");
        order.className = "order";
        tile.appendChild(order);
        picker.prepend(tile);
      }
      const ids = selectedIds();
      ids.push(String(asset.id));
      mediaInput.value = ids.join(",");
      renderSelection();
    },
  };

  // Post type hints
  const hints = {
    feed: t("hint_feed"), carousel: t("hint_carousel"), reel: t("hint_reel"), story: t("hint_story"),
  };
  function currentType() {
    const checked = document.querySelector("input[name=post_type]:checked");
    return checked ? checked.value : "feed";
  }
  function updateHint() {
    const hint = document.querySelector("[data-type-hint]");
    if (!hint) return;
    hint.textContent = hints[currentType()] || "";
    const reelOnly = document.querySelector("[data-reel-only]");
    if (reelOnly) reelOnly.hidden = currentType() !== "reel";
    const captionBlock = document.querySelector("[data-caption-block]");
    if (captionBlock) captionBlock.hidden = currentType() === "story";
    const tagsField = document.querySelector("[data-tags-field]");
    if (tagsField) tagsField.hidden = currentType() === "story";
    const collabField = document.querySelector("[data-collab-field]");
    if (collabField) collabField.hidden = currentType() === "story";
  }
  document.querySelectorAll("input[name=post_type]").forEach((el) => el.addEventListener("change", updateHint));
  updateHint();

  // Caption counter
  const caption = document.getElementById("id_caption");
  const counter = document.querySelector("[data-caption-count]");
  function updateCounter() {
    if (!caption || !counter) return;
    const tags = (caption.value.match(/#[^\s#]+/g) || []).length;
    counter.textContent = t("counter", { chars: caption.value.length, tags: tags });
    counter.style.color = caption.value.length > 2200 || tags > 30 ? "var(--err)" : "";
  }
  if (caption) { caption.addEventListener("input", updateCounter); updateCounter(); }

  // Submit buttons set the action (draft / schedule / now)
  const actionInput = document.getElementById("id_action");
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", (event) => {
      if (actionInput) actionInput.value = button.dataset.action;
      if (button.dataset.action === "now" && !confirm(t("confirm_publish"))) {
        event.preventDefault();
      }
    });
  });

  // AI caption suggestions
  const aiButton = document.querySelector("[data-ai-suggest]");
  if (aiButton) {
    aiButton.addEventListener("click", async () => {
      const out = document.querySelector("[data-ai-results]");
      const brief = document.getElementById("ai-brief");
      const body = new FormData();
      body.append("brief", brief ? brief.value : "");
      body.append("media_ids", mediaInput ? mediaInput.value : "");
      body.append("post_type", currentType());
      aiButton.disabled = true;
      const label = aiButton.textContent;
      aiButton.textContent = t("writing");
      out.innerHTML = "";
      try {
        const resp = await fetch(aiButton.dataset.url, {
          method: "POST", body, headers: { "X-CSRFToken": csrfToken() }, credentials: "same-origin",
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || t("went_wrong"));
        data.captions.forEach((text) => {
          const box = document.createElement("div");
          box.className = "suggestion";
          box.textContent = text;
          const use = document.createElement("button");
          use.type = "button";
          use.className = "btn btn-sm";
          use.textContent = t("use_caption");
          use.addEventListener("click", () => {
            caption.value = text;
            updateCounter();
            caption.focus();
          });
          box.appendChild(document.createElement("br"));
          box.appendChild(use);
          out.appendChild(box);
        });
      } catch (err) {
        const p = document.createElement("p");
        p.className = "error-text";
        p.textContent = err.message;
        out.appendChild(p);
      } finally {
        aiButton.disabled = false;
        aiButton.textContent = label;
      }
    });
  }

  // Show/hide sections depending on a radio choice: data-show-when="field=value"
  const conditional = document.querySelectorAll("[data-show-when]");
  function updateConditional() {
    conditional.forEach((el) => {
      const [name, value] = el.dataset.showWhen.split("=");
      const checked = document.querySelector(`input[name="${name}"]:checked`);
      el.hidden = !checked || checked.value !== value;
    });
  }
  if (conditional.length) {
    document.addEventListener("change", (e) => { if (e.target.matches("input[type=radio]")) updateConditional(); });
    updateConditional();
  }

  // Copy buttons
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        const label = button.textContent;
        button.textContent = t("copied");
        setTimeout(() => { button.textContent = label; }, 1500);
      } catch (err) {
        window.prompt(t("copy_this"), button.dataset.copy);
      }
    });
  });

  // Confirm destructive actions
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
})();
