const extension = globalThis.browser || globalThis.chrome;
const serverInput = document.getElementById("server");
const tokenInput = document.getElementById("token");
const status = document.getElementById("status");
const dashboard = document.getElementById("dashboard");
const save = document.getElementById("save");

extension.storage.local.get(["server", "token"]).then(({ server, token }) => {
  serverInput.value = server || "https://twitter-notes.tina.moe";
  tokenInput.value = token || "";
  if (server) {
    dashboard.href = server;
    dashboard.hidden = false;
  }
});

document.getElementById("show-token").addEventListener("change", (event) => {
  tokenInput.type = event.target.checked ? "text" : "password";
});

document.getElementById("settings").addEventListener("submit", async (event) => {
  event.preventDefault();
  save.disabled = true;
  status.textContent = "Connecting...";
  try {
    const url = new URL(serverInput.value.trim());
    const local = ["localhost", "127.0.0.1"].includes(url.hostname);
    if ((url.protocol !== "https:" && !(local && url.protocol === "http:")) ||
        url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
      throw new Error("Use an HTTPS origin without a path. HTTP is allowed only on localhost.");
    }
    const token = tokenInput.value.trim();
    if (!/^tn_[a-zA-Z0-9_-]{43}$/.test(token)) throw new Error("Enter an API token generated from the dashboard.");
    const permission = `${url.protocol}//${url.hostname}/*`;
    const granted = await extension.permissions.request({ origins: [permission] });
    if (!granted) throw new Error("Server permission was not granted.");
    await extension.storage.local.set({ server: url.origin, token });
    const response = await extension.runtime.sendMessage({ action: "check" });
    if (!response?.ok) throw new Error(response?.error || "Server connection failed.");
    status.textContent = `Connected as @${response.data.username}.`;
    dashboard.href = url.origin;
    dashboard.hidden = false;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    save.disabled = false;
  }
});

document.getElementById("disconnect").addEventListener("click", async () => {
  await extension.storage.local.remove(["server", "token"]);
  tokenInput.value = "";
  dashboard.hidden = true;
  status.textContent = "Disconnected.";
});