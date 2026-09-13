(() => {
  const extension = globalThis.browser || globalThis.chrome;
  const identities = new Map();
  const excluded = new Set(["home", "explore", "notifications", "messages", "i", "settings", "search", "compose", "login", "logout", "signup", "tos", "privacy", "jobs", "communities", "premium", "intent"]);
  const profileTabs = new Set(["with_replies", "media", "highlights", "articles", "likes"]);
  let panel;
  let currentKey = "";
  let generation = 0;
  let timer;

  function profileHandle() {
    const parts = location.pathname.split("/").filter(Boolean);
    if (parts.length > 2 || (parts.length === 2 && !profileTabs.has(parts[1]))) return null;
    const handle = parts[0];
    return handle && /^[a-zA-Z0-9_]{1,15}$/.test(handle) && !excluded.has(handle.toLowerCase()) ? handle : null;
  }

  async function request(action, userId, note) {
    const response = await extension.runtime.sendMessage({ action, userId, note });
    if (!response?.ok) throw new Error(response?.error || "Extension connection lost. Reload this tab.");
    return response.data;
  }

  function element(tag, text, properties = {}) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    Object.assign(node, properties);
    return node;
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(syncProfile, 150);
  }

  async function syncProfile() {
    const username = profileHandle();
    const header = document.querySelector('main [data-testid="primaryColumn"] [data-testid="UserName"]') ||
      document.querySelector('main [data-testid="UserName"]:not(article [data-testid="UserName"])');
    if (!username || !header || header.closest("article")) {
      if (panel) panel.remove();
      panel = null;
      currentKey = "";
      generation++;
      return;
    }
    const identity = identities.get(username.toLowerCase());
    const key = `${username.toLowerCase()}:${identity?.userId || "pending"}`;
    if (key === currentKey && panel?.isConnected) return;
    currentKey = key;
    const run = ++generation;
    if (panel) panel.remove();
    panel = element("section");
    const shadow = panel.attachShadow({ mode: "closed" });
    for (const eventType of ["keydown", "keypress", "keyup"]) {
      shadow.addEventListener(eventType, (event) => event.stopPropagation());
    }
    const style = element("style");
    style.textContent = `
      :host { --accent:rgb(29, 155, 240); --line:light-dark(color-mix(in srgb, var(--accent) 20%, #d4d4d4),color-mix(in srgb, var(--accent) 20%, #444)); display:block; margin:16px 0; color-scheme:light dark; }
      * { box-sizing:border-box; }
      [hidden] { display:none !important; }
      section { font:14px/1.5 sans-serif; letter-spacing:0; color:light-dark(#202124,#eee); background:light-dark(color-mix(in srgb, var(--accent) 5%, white),color-mix(in srgb, var(--accent) 8%, #181818)); border:1px solid var(--line); border-radius:6px; padding:14px; }
      section.compact { background:transparent; border:0; padding:0; }
      .create-note { display:inline-flex; align-items:center; gap:6px; border:0; padding:4px 0; color:light-dark(#536471,#aaa); }
      .create-note:hover { color:var(--accent); }
      h2 { font-size:15px; margin:0 0 10px; }
      textarea { width:100%; min-height:90px; resize:vertical; padding:8px; border:1px solid var(--line); border-radius:4px; background:light-dark(white,#121212); color:inherit; font:inherit; }
      textarea:focus-visible, input:focus-visible, button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
      fieldset { display:flex; flex-wrap:wrap; gap:8px 12px; border:0; padding:10px 0; margin:0; }
      legend { font-size:12px; opacity:.75; padding:0; }
      label { display:flex; align-items:center; gap:5px; overflow-wrap:anywhere; max-width:100%; }
      input { flex-shrink:0; accent-color:var(--accent); }
      .swatch { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
      .actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
      button { font:inherit; cursor:pointer; min-height:32px; padding:4px 12px; border-radius:4px; border:1px solid var(--line); background:transparent; color:inherit; }
      button[type=submit] { background:var(--accent); color:#202124; border-color:var(--accent); }
      button:disabled { opacity:.5; cursor:default; }
      p { margin:8px 0 0; font-size:12px; overflow-wrap:anywhere; }
    `;
    shadow.append(style);
    const section = element("section");
    const heading = element("h2", "Private note");
    section.append(heading);
    const status = element("p", identity ? "Loading..." : "Waiting for Twitter's profile ID. Reload this profile if it stays unavailable.");
    status.setAttribute("role", "status");
    section.append(status);
    shadow.append(section);
    header.after(panel);
    if (!identity) return;
    const stillCurrent = () => run === generation && profileHandle()?.toLowerCase() === username.toLowerCase();
    try {
      const [noteData, tagData] = await Promise.all([request("read", identity.userId), request("tags")]);
      if (!stillCurrent()) return;
      status.textContent = "";
      const form = element("form", "", { id: "note-editor" });
      const create = element("button", "", { type: "button", className: "create-note" });
      const pencil = element("span", "\u270e");
      pencil.setAttribute("aria-hidden", "true");
      create.append(pencil, document.createTextNode("Create a private note"));
      create.setAttribute("aria-controls", form.id);
      section.insertBefore(create, status);
      const textarea = element("textarea", "", { value: noteData.note?.body || "", maxLength: 10000 });
      textarea.setAttribute("aria-label", `Private note for @${username}`);
      form.append(textarea);
      const tags = element("fieldset");
      tags.append(element("legend", "Tags"));
      const selected = new Set((noteData.note?.tags || []).map((tag) => tag.id));
      for (const tag of tagData.tags) {
        const label = element("label");
        const checkbox = element("input", "", { type: "checkbox", value: String(tag.id), checked: selected.has(tag.id) });
        const swatch = element("span", "", { className: "swatch" });
        swatch.style.backgroundColor = tag.color;
        label.append(checkbox, swatch, document.createTextNode(tag.name));
        tags.append(label);
      }
      form.append(tags);
      const actions = element("div", "", { className: "actions" });
      const save = element("button", "Save", { type: "submit" });
      const remove = element("button", "Delete", { type: "button", disabled: !noteData.note });
      actions.append(save, remove);
      form.append(actions);
      section.insertBefore(form, status);
      const setExpanded = (expanded) => {
        section.classList.toggle("compact", !expanded);
        heading.hidden = !expanded;
        form.hidden = !expanded;
        status.hidden = !expanded;
        create.hidden = expanded;
        create.setAttribute("aria-expanded", String(expanded));
      };
      setExpanded(Boolean(noteData.note?.body?.trim() || selected.size));
      create.addEventListener("click", () => {
        setExpanded(true);
        textarea.focus();
      });
      const setBusy = (busy) => {
        save.disabled = busy;
        remove.disabled = busy || !noteData.note;
        textarea.disabled = busy;
        tags.disabled = busy;
      };
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!stillCurrent()) return;
        setBusy(true);
        status.textContent = "Saving...";
        try {
          const data = await request("save", identity.userId, {
            username,
            body: textarea.value,
            tag_ids: [...tags.querySelectorAll("input:checked")].map((input) => Number(input.value)),
          });
          noteData.note = data.note;
          status.textContent = "Saved.";
        } catch (error) {
          status.textContent = error.message;
        } finally {
          setBusy(false);
        }
      });
      remove.addEventListener("click", async () => {
        if (!stillCurrent() || !window.confirm("Delete this private note and its tags?")) return;
        setBusy(true);
        try {
          await request("delete", identity.userId);
          noteData.note = null;
          textarea.value = "";
          tags.querySelectorAll("input").forEach((input) => { input.checked = false; });
          status.textContent = "Deleted.";
          setExpanded(false);
          create.focus();
        } catch (error) {
          status.textContent = error.message;
        } finally {
          setBusy(false);
        }
      });
    } catch (error) {
      if (!stillCurrent()) return;
      status.textContent = error.message;
      const retry = element("button", "Retry", { type: "button" });
      retry.addEventListener("click", () => { currentKey = ""; schedule(); });
      section.append(retry);
    }
  }

  window.addEventListener("twitter-notes:identity", (event) => {
    try {
      if (typeof event.detail !== "string" || event.detail.length > 200) return;
      const identity = JSON.parse(event.detail);
      if (!/^[0-9]{1,20}$/.test(identity.userId) || typeof identity.userId !== "string" ||
          typeof identity.username !== "string" || !/^[a-zA-Z0-9_]{1,15}$/.test(identity.username)) return;
      identities.set(identity.username.toLowerCase(), identity);
      if (identities.size > 200) identities.delete(identities.keys().next().value);
      schedule();
    } catch {}
  });
  window.dispatchEvent(new Event("twitter-notes:request-identities"));
  new MutationObserver(schedule).observe(document, { childList: true, subtree: true });
  window.addEventListener("popstate", schedule);
  window.addEventListener("pageshow", schedule);
  schedule();
})();
