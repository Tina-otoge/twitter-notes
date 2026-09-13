const extension = globalThis.browser || globalThis.chrome;

if (extension.storage.local.setAccessLevel) {
  extension.storage.local.setAccessLevel({ accessLevel: "TRUSTED_CONTEXTS" });
}

function serverOrigin(value) {
  const url = new URL(value);
  const local = ["localhost", "127.0.0.1"].includes(url.hostname);
  if ((url.protocol !== "https:" && !(local && url.protocol === "http:")) ||
      url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
    throw new Error("Use an HTTPS server origin, or HTTP localhost, without a path.");
  }
  return url.origin;
}

async function apiRequest(path, method = "GET", body) {
  const { server, token } = await extension.storage.local.get(["server", "token"]);
  if (!server || !token) throw new Error("Configure your server and API token from the extension icon.");
  const origin = serverOrigin(server);
  const response = await fetch(origin + path, {
    method,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "omit",
    redirect: "error",
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (response.status === 401) throw new Error("API token is invalid or revoked. Update it from the extension icon.");
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || `Server returned ${response.status}.`);
  }
  return response.status === 204 ? null : response.json();
}

async function handleMessage(message, sender) {
  const popup = sender.url === extension.runtime.getURL("popup.html");
  const page = sender.tab && ["https://x.com", "https://twitter.com"].includes(new URL(sender.url).origin);
  if (!popup && !page) throw new Error("Untrusted request.");
  if (message.action === "check" && popup) return apiRequest("/api/me");
  if (message.action === "tags") return apiRequest("/api/tags");
  if (typeof message.userId !== "string" || !/^[0-9]{1,20}$/.test(message.userId)) {
    throw new Error("A resolved Twitter user ID is required.");
  }
  const path = `/api/notes/${message.userId}`;
  if (message.action === "read") return apiRequest(path);
  if (message.action === "save") return apiRequest(path, "PUT", message.note);
  if (message.action === "delete") return apiRequest(path, "DELETE");
  throw new Error("Unknown action.");
}

extension.runtime.onMessage.addListener((message, sender, respond) => {
  handleMessage(message, sender).then(
    (data) => respond({ ok: true, data }),
    (error) => respond({ ok: false, error: error.message || "Cannot reach the notes server." }),
  );
  return true;
});
