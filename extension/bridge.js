(() => {
  const identities = new Map();
  const responseEvent = "twitter-notes:identity";

  function publish(identity) {
    window.dispatchEvent(new CustomEvent(responseEvent, { detail: JSON.stringify(identity) }));
  }

  function inspect(data) {
    let budget = 20000;
    function visit(value, depth) {
      if (!value || typeof value !== "object" || depth > 16 || --budget < 0) return;
      const username = value.core?.screen_name || value.legacy?.screen_name;
      const userId = value.rest_id;
      if (typeof username === "string" && /^[a-zA-Z0-9_]{1,15}$/.test(username) &&
          typeof userId === "string" && /^[0-9]{1,20}$/.test(userId) &&
          (!value.__typename || value.__typename === "User")) {
        const identity = { username, userId };
        identities.set(username.toLowerCase(), identity);
        if (identities.size > 200) identities.delete(identities.keys().next().value);
        publish(identity);
      }
      for (const child of Object.values(value)) visit(child, depth + 1);
    }
    visit(data, 0);
  }

  function isProfileResponse(value) {
    try {
      const url = new URL(value, location.origin);
      return ["x.com", "twitter.com", "api.x.com", "api.twitter.com"].includes(url.hostname) &&
        url.pathname.includes("/graphql/") &&
        ["UserByScreenName", "UserByRestId", "UsersByRestIds"].includes(url.pathname.split("/").pop());
    } catch {
      return false;
    }
  }

  const originalFetch = window.fetch;
  window.fetch = function (...args) {
    const result = originalFetch.apply(this, args);
    const url = args[0] instanceof Request ? args[0].url : String(args[0]);
    if (isProfileResponse(url)) {
      result.then((response) => response.clone().json()).then(inspect).catch(() => {});
    }
    return result;
  };

  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...args) {
    if (isProfileResponse(String(url))) {
      this.addEventListener("load", () => {
        try {
          inspect(this.responseType === "json" ? this.response : JSON.parse(this.responseText));
        } catch {}
      }, { once: true });
    }
    return originalOpen.call(this, method, url, ...args);
  };

  window.addEventListener("twitter-notes:request-identities", () => {
    for (const identity of identities.values()) publish(identity);
  });
})();