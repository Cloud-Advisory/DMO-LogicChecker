const DEFAULT_CONFIG = {
  backendUrl: window.location.origin,
};

const state = {
  config: DEFAULT_CONFIG,
  routes: [],
};

const selectors = {
  tokenInput: document.getElementById("token"),
  actionInput: document.getElementById("action"),
  promptInput: document.getElementById("prompt"),
  endpointInput: document.getElementById("endpoint"),
  apiKeyInput: document.getElementById("apiKey"),
  form: document.getElementById("routeForm"),
  tableBody: document.getElementById("routesTable"),
  refreshBtn: document.getElementById("refreshBtn"),
  storeTokenBtn: document.getElementById("storeToken"),
  clearTokenBtn: document.getElementById("clearToken"),
  tokenStatus: document.getElementById("tokenStatus"),
  toast: document.getElementById("toast"),
};

async function loadRuntimeConfig() {
  try {
    const response = await fetch("runtime.config.json", { cache: "no-store" });
    if (response.ok) {
      const payload = await response.json();
      state.config = { ...DEFAULT_CONFIG, ...payload };
    }
  } catch (err) {
    console.warn("Falling back to default admin config", err);
  }
}

function showToast(message, isError = false) {
  const toast = selectors.toast;
  toast.textContent = message;
  toast.style.background = isError ? "#dc2626" : "#0f172a";
  toast.hidden = false;
  setTimeout(() => {
    toast.hidden = true;
  }, 3200);
}


async function fetchRoutes() {
  try {
    const response = await fetch(`${state.config.backendUrl}/api/v1/admin/routes`, {
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Request failed (${response.status})`);
    }

    state.routes = await response.json();
    renderRoutes();
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderRoutes() {
  if (!selectors.tableBody) {
    return;
  }

  if (!state.routes.length) {
    selectors.tableBody.innerHTML = '<tr><td colspan="5" class="empty">No routes stored.</td></tr>';
    return;
  }

  selectors.tableBody.innerHTML = state.routes
    .map(
      (route) => `
        <tr>
          <td>${route.token}</td>
          <td>${route.action}</td>
          <td>${route.endpoint || "—"}</td>
          <td class="prompt-cell">${route.prompt ? route.prompt.substring(0, 120) : "—"}</td>
          <td>
            <div class="route-actions">
              <button type="button" data-action="edit" data-token="${route.token}" data-route-action="${route.action}">Edit</button>
              <button type="button" class="delete" data-action="delete" data-token="${route.token}" data-route-action="${route.action}">Delete</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function handleTableClick(event) {
  const btn = event.target.closest("button[data-action]");
  if (!btn) {
    return;
  }
  const token = btn.dataset.token;
  const action = btn.dataset.routeAction;
  const route = state.routes.find((item) => item.token === token && item.action === action);

  if (btn.dataset.action === "edit" && route) {
    selectors.tokenInput.value = route.token;
    selectors.actionInput.value = route.action;
    selectors.promptInput.value = route.prompt || "";
    selectors.endpointInput.value = route.endpoint || "";
    selectors.apiKeyInput.value = route.api_key || "";
    showToast(`Loaded ${route.token} / ${route.action}`);
  }

  if (btn.dataset.action === "delete") {
    deleteRoute(token, action);
  }
}

async function deleteRoute(token, action) {
  if (!window.confirm(`Delete ${token} / ${action}?`)) {
    return;
  }

  try {
    const response = await fetch(`${state.config.backendUrl}/api/v1/admin/routes/${token}/${action}`, {
      method: "DELETE",
      headers: {
      },
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Delete failed (${response.status})`);
    }

    showToast("Route deleted");
    await fetchRoutes();
  } catch (err) {
    showToast(err.message, true);
  }
}

async function submitRoute(event) {
  event.preventDefault();

  const payload = {
    token: selectors.tokenInput.value.trim(),
    action: selectors.actionInput.value.trim(),
    prompt: selectors.promptInput.value.trim() || null,
    endpoint: selectors.endpointInput.value.trim() || null,
    api_key: selectors.apiKeyInput.value.trim() || null,
  };

  if (!payload.token || !payload.action) {
    showToast("Token and Action are required.", true);
    return;
  }

  try {
    const response = await fetch(`${state.config.backendUrl}/api/v1/admin/routes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errPayload = await response.json().catch(() => ({}));
      throw new Error(errPayload.detail || `Save failed (${response.status})`);
    }

    selectors.form.reset();
    showToast("Route saved");
    await fetchRoutes();
  } catch (err) {
    showToast(err.message, true);
  }
}

function wireEvents() {
  selectors.form?.addEventListener("submit", submitRoute);
  selectors.refreshBtn?.addEventListener("click", fetchRoutes);
  selectors.tableBody?.addEventListener("click", handleTableClick);
}

(async function init() {
  await loadRuntimeConfig();
  wireEvents();
})();
