const DEFAULT_CONFIG = {
    backendUrl: window.location.origin,
    identityMode: "token",
};

async function loadRuntimeConfig() {
    try {
        const response = await fetch("runtime.config.json", { cache: "no-store" });
        if (!response.ok) {
            return DEFAULT_CONFIG;
        }
        const data = await response.json();
        return { ...DEFAULT_CONFIG, ...data };
    } catch (error) {
        console.warn("Falling back to default runtime config", error);
        return DEFAULT_CONFIG;
    }
}

function getQueryParams() {
    const params = {};
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.forEach((value, key) => {
        params[key] = value;
    });
    return params;
}

async function handleAuthIfNeeded(identityMode) {
    if (identityMode !== "entra") {
        return;
    }

    try {
        const response = await fetch("/.auth/me", { cache: "no-store" });
        const data = await response.json();
        if (data.clientPrincipal) {
            const aadToken = data.clientPrincipal.idToken || "";
            sessionStorage.setItem("aadToken", aadToken);
        }
    } catch (error) {
        console.error("Auth check failed:", error);
    }
}

function containsFairytaleTrigger(text) {
    return text.toLowerCase().includes("show me the fairytale");
}

function detectLanguage(text) {
    return /[äöüß]/i.test(text) ? "de" : "en";
}

function buildFairytale(language, seedText) {
    const base = seedText.slice(0, 120);
    if (language === "de") {
        return `\
            <h3>SITS Märchen-Generator</h3>
            <p>Es war einmal im klinischen Spiegelgarten, wo folgender Satz ganz besonders wichtig war:</p>
            <blockquote>${escapeHtml(base)}...</blockquote>
            <p>Die Logikprüfung macht kurz Pause und schenkt Ihnen stattdessen dieses kleine Märchen. Viel Freude damit!</p>
        `;
    }
    return `\
        <h3>SITS Fairytale Mode</h3>
        <p>Once upon a time inside the Logic Checker, the following phrase echoed through the halls:</p>
        <blockquote>${escapeHtml(base)}...</blockquote>
        <p>The system paused compliance duties to spin a whimsical story just for you. Enjoy the detour!</p>
    `;
}

function abbreviate(text, max = 220) {
    if (!text) {
        return "";
    }
    const trimmed = text.replace(/\s+/g, " ").trim();
    return trimmed.length > max ? `${trimmed.slice(0, max)}…` : trimmed;
}

function escapeHtml(value) {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function sanitizeHtml(content) {
    if (window.DOMPurify) {
        return DOMPurify.sanitize(content, {
            USE_PROFILES: { html: true },
        });
    }
    return `<pre>${escapeHtml(content)}</pre>`;
}

document.addEventListener("DOMContentLoaded", async () => {
    const config = await loadRuntimeConfig();
    await handleAuthIfNeeded(config.identityMode);

    const urlParams = getQueryParams();
    const token = urlParams.token;
    const action = urlParams.action;

    const outputText = document.getElementById("output-text");
    const copyBtn = document.getElementById("copy-btn");
    const pasteHint = document.getElementById("paste-hint");
    const inputPreview = document.getElementById("input-preview");
    const statusDot = document.getElementById("status-dot");
    const toast = document.getElementById("toast");
    const shell = document.querySelector(".shell");

    let isProcessing = false;

    if (shell) {
        shell.focus();
        // shell.addEventListener("click", () => shell.focus());
    }

    if (!token || !action) {
        renderError("Required 'token' and 'action' parameters are missing from the URL.");
        setStatus("Config error", "error");
        return;
    }

    document.addEventListener("paste", (event) => {
        const textData = event.clipboardData?.getData("text")?.trim();
        if (!textData) {
            showToast("Clipboard was empty.", true);
            return;
        }

        event.preventDefault();
        updatePreview(textData);
        analyzeText(token, action, textData);
    });

    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "v") {
            pasteHint?.classList.add("active");
        }
    });

    document.addEventListener("keyup", (event) => {
        if (event.key.toLowerCase() === "v") {
            pasteHint?.classList.remove("active");
        }
    });

    copyBtn?.addEventListener("click", async () => {
        const copySource = outputText.innerText.trim();
        if (!copySource) {
            showToast("Nothing to copy yet.", true);
            return;
        }

        try {
            await navigator.clipboard.writeText(copySource);
            copyBtn.classList.add("success");
            showToast("Analysis copied.");
            setTimeout(() => copyBtn.classList.remove("success"), 1500);
        } catch (error) {
            console.error("Clipboard copy failed", error);
            showToast("Clipboard blocked.", true);
        }
    });

    async function analyzeText(currentToken, currentAction, textData) {
        if (isProcessing) {
            showToast("Still processing previous input.");
            return;
        }

        if (!textData) {
            renderError("Clipboard did not contain text.");
            setStatus("Idle");
            return;
        }

        if (containsFairytaleTrigger(textData)) {
            const language = detectLanguage(textData);
            renderAnalysis(buildFairytale(language, textData));
            showToast("Enjoy the detour.");
            setStatus("Fairytale", "success");
            return;
        }

        isProcessing = true;
        setStatus("Analyzing…", "running");

        const requestData = {
            text: textData,
            action: currentAction,
            fairytale: false,
        };

        try {
            const response = await fetch(`${config.backendUrl}/api/v1/analyze`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${currentToken}`,
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                mode: "cors",
                body: JSON.stringify(requestData),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || `HTTP error: ${response.status}`);
            }

            const analysis = data.analysis || "No analysis returned.";
            renderAnalysis(analysis);
            showToast("Analysis ready.");
            setStatus("Complete", "success");
        } catch (error) {
            console.error("Request failed:", error);
            renderError(error.message);
            showToast(error.message, true);
            setStatus("Error", "error");
        } finally {
            isProcessing = false;
        }
    }

    function renderAnalysis(content) {
        outputText.innerHTML = sanitizeHtml(content);
    }

    function renderError(message) {
        outputText.innerHTML = `<p class="error-message">Error: ${escapeHtml(message)}</p>`;
    }

    function updatePreview(text) {
        if (inputPreview) {
            inputPreview.innerText = abbreviate(text);
        }
    }

    function setStatus(label, variant = "idle") {
        if (!statusDot) {
            return;
        }
        statusDot.innerText = label;
        statusDot.className = `status ${variant}`.trim();
    }

    function showToast(message, isError = false) {
        if (!toast) {
            return;
        }
        toast.innerText = message;
        toast.style.background = isError ? "#e25255" : "#0b1f3a";
        toast.classList.add("show");
        setTimeout(() => toast.classList.remove("show"), 2000);
    }

});
document.getElementById('set-config-btn').addEventListener('click', function() {
    const action = document.getElementById('action').value;
    const token = document.getElementById('token').value;
    const url = new URL(window.location);
    url.searchParams.set('action', action);
    url.searchParams.set('token', token);
    window.location = url.toString();
});

document.getElementById('upload-btn').addEventListener('click', function() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please select a file.');
        return;
    }
    const action = document.getElementById('action').value;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('filename', file.name);
    formData.append('action', action);
    formData.append('fairytale', false);
    const currentToken = document.getElementById('token').value;
    console.log(formData);

    // Update status
    document.getElementById('status-dot').textContent = 'Uploading...';
    fetch('/api/v1/upload', {
        method: "POST",
        headers: {
            Authorization: `Bearer ${currentToken}`,
            Accept: "application/json",
        },
        mode: "cors",
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        // Update output and status
        document.getElementById('output-text').innerHTML = data.result || 'Processing complete.';
        document.getElementById('status-dot').textContent = 'Idle';
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('status-dot').textContent = 'Error';
    });
});
