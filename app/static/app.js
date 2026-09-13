const noteFilters = document.querySelector("[data-note-filters]");
if (noteFilters) {
  const search = noteFilters.elements.q;
  const tag = noteFilters.elements.tag;
  const results = document.querySelector("[data-note-results]");
  const error = document.querySelector("[data-filter-error]");
  let loadedUrl = window.location.href;
  let pendingRequest;
  let searchTimer;

  const cancelPending = () => {
    clearTimeout(searchTimer);
    pendingRequest?.controller.abort();
    pendingRequest = null;
    results.removeAttribute("aria-busy");
  };

  const loadResults = async (url) => {
    clearTimeout(searchTimer);
    if (pendingRequest?.url === url.href) return;
    cancelPending();
    error.hidden = true;
    if (url.href === loadedUrl) return;
    const request = { url: url.href, controller: new AbortController() };
    pendingRequest = request;
    results.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(url, {
        signal: request.controller.signal,
        credentials: "same-origin",
        redirect: "error",
      });
      if (!response.ok) throw new Error("Search failed");
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const nextResults = page.querySelector("[data-note-results]");
      if (!nextResults) throw new Error("Missing search results");
      if (pendingRequest !== request) return;
      results.replaceChildren(...nextResults.childNodes);
      window.history.replaceState(null, "", url);
      loadedUrl = url.href;
    } catch {
      if (pendingRequest !== request) return;
      error.textContent = "Could not load notes. Change a filter or press Enter to retry.";
      error.hidden = false;
    } finally {
      if (pendingRequest === request) {
        pendingRequest = null;
        results.removeAttribute("aria-busy");
      }
    }
  };

  const applyFilters = () => {
    const url = new URL(noteFilters.action);
    url.search = new URLSearchParams(new FormData(noteFilters)).toString();
    return loadResults(url);
  };

  const scheduleSearch = () => {
    cancelPending();
    searchTimer = setTimeout(applyFilters, 200);
  };
  search.addEventListener("input", (event) => {
    cancelPending();
    if (!event.isComposing) scheduleSearch();
  });
  search.addEventListener("compositionend", scheduleSearch);
  search.addEventListener("blur", applyFilters);
  tag.addEventListener("change", applyFilters);
  noteFilters.addEventListener("submit", (event) => {
    event.preventDefault();
    return applyFilters();
  });
  results.addEventListener("click", (event) => {
    const link = event.target.closest("nav[aria-label='Pagination'] a");
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    return loadResults(new URL(link.href));
  });
}

document.addEventListener("submit", (event) => {
  const form = event.target.closest("form[data-confirm]");
  if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
});
document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const input = document.getElementById(button.dataset.copy);
    const status = document.getElementById("copy-status");
    try {
      await navigator.clipboard.writeText(input.value);
      status.textContent = "Token copied.";
    } catch {
      input.select();
      status.textContent = "Clipboard unavailable. The token is selected for copying.";
    }
  });
});
