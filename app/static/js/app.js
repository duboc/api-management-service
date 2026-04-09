let gatewayDashboardData = null;

document.addEventListener("DOMContentLoaded", () => {
    loadAll();

    document.getElementById("btn-refresh-all").addEventListener("click", loadAll);
    document.getElementById("btn-test-gateway").addEventListener("click", handleTestGateway);
    document.getElementById("btn-create-api").addEventListener("click", () => renderCreateApiModal());
    document.getElementById("btn-create-config").addEventListener("click", handleCreateConfig);
    document.getElementById("btn-deploy-gateway").addEventListener("click", handleDeployGateway);
    document.getElementById("btn-preview-proxy").addEventListener("click", handlePreviewProxy);
    document.getElementById("btn-deploy-proxy").addEventListener("click", () => renderDeployProxyModal());
    document.getElementById("btn-create-key").addEventListener("click", () => renderCreateKeyModal());

    // Event delegation for keys section
    document.getElementById("keys-section").addEventListener("click", (e) => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const keyId = btn.dataset.keyId;
        if (btn.dataset.action === "reveal-key") handleRevealKey(keyId);
        if (btn.dataset.action === "delete-key") handleDeleteKey(keyId);
    });

    // Modal close on backdrop/escape
    document.getElementById("app-modal").addEventListener("click", (e) => {
        if (e.target === e.currentTarget) closeModal();
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeModal();
    });
});

function loadAll() {
    loadDashboard();
    loadGatewaySection();
    loadProxySection();
    loadApiKeysSection();
}

async function loadDashboard() {
    try {
        const data = await ApiClient.getDashboard();
        renderDashboard(data);
    } catch (err) {
        showToast(`Dashboard: ${err.message}`, "error");
    }
}

async function loadGatewaySection() {
    try {
        gatewayDashboardData = await ApiClient.gateway.getDashboard();
        renderGatewaySection(gatewayDashboardData);
        loadCurlExample();
    } catch (err) {
        document.getElementById("gateway-section").innerHTML =
            `<p class="text-red-500 text-sm">${escapeHtml(err.message)}</p>`;
    }
}

async function loadCurlExample() {
    if (!gatewayDashboardData?.gateway_exists || !gatewayDashboardData?.gateway_url) return;
    try {
        const keysData = await ApiClient.keys.list();
        if (keysData.keys && keysData.keys.length > 0) {
            const keyId = extractKeyId(keysData.keys[0].name);
            const resp = await ApiClient.keys.getKeyString(keyId);
            renderCurlExample(gatewayDashboardData.gateway_url, resp.key_string);
        }
    } catch {
        // Silently skip if keys can't be loaded
    }
}

async function loadProxySection() {
    try {
        const status = await ApiClient.proxy.getStatus();
        renderProxySection(status);
    } catch (err) {
        document.getElementById("proxy-section").innerHTML =
            `<p class="text-red-500 text-sm">${escapeHtml(err.message)}</p>`;
    }
}

async function loadApiKeysSection() {
    try {
        const data = await ApiClient.keys.list();
        renderApiKeysSection(data);
    } catch (err) {
        document.getElementById("keys-section").innerHTML =
            `<p class="text-red-500 text-sm">${escapeHtml(err.message)}</p>`;
    }
}

// --- Gateway Handlers ---

async function submitCreateApi() {
    const apiId = document.getElementById("form-api-id").value.trim();
    if (!apiId) { showToast("API ID is required", "error"); return; }

    closeModal();
    showLoading("Creating API... This may take a moment.");
    try {
        await ApiClient.gateway.createApi(apiId);
        showToast("API created successfully", "success");
        loadAll();
    } catch (err) {
        showToast(`Failed to create API: ${err.message}`, "error");
    } finally {
        hideLoading();
    }
}

function handleCreateConfig() {
    if (!gatewayDashboardData?.api_exists) {
        showToast("Create an API first", "error");
        return;
    }
    const apiId = extractKeyId(gatewayDashboardData.api_name);
    renderCreateConfigModal(apiId);
}

async function submitCreateConfig() {
    const apiId = document.getElementById("form-api-id-for-config").value;
    const configId = document.getElementById("form-config-id").value.trim();
    const backendUrl = document.getElementById("form-backend-url").value.trim();
    const saEmail = document.getElementById("form-sa-email").value.trim();

    if (!configId || !backendUrl || !saEmail) {
        showToast("All fields are required", "error");
        return;
    }

    closeModal();
    showLoading("Creating API config... This may take several minutes.");
    try {
        await ApiClient.gateway.createConfig(apiId, {
            config_id: configId,
            backend_url: backendUrl,
            service_account_email: saEmail,
        });
        showToast("API config created successfully", "success");
        loadAll();
    } catch (err) {
        showToast(`Failed to create config: ${err.message}`, "error");
    } finally {
        hideLoading();
    }
}

function handleDeployGateway() {
    if (!gatewayDashboardData?.api_exists) {
        showToast("Create an API and config first", "error");
        return;
    }
    const apiId = extractKeyId(gatewayDashboardData.api_name);
    renderDeployGatewayModal(apiId, gatewayDashboardData.configs || []);
}

async function submitDeployGateway() {
    const gatewayId = document.getElementById("form-gateway-id").value.trim();
    const configId = document.getElementById("form-gateway-config").value;
    const location = document.getElementById("form-gateway-region").value;

    if (!gatewayId || !configId) {
        showToast("Gateway ID and config are required", "error");
        return;
    }

    closeModal();
    showLoading("Deploying gateway... This may take 2-5 minutes.");
    try {
        await ApiClient.gateway.createGateway({
            gateway_id: gatewayId,
            api_config_id: configId,
            location: location,
        });
        showToast("Gateway deployed successfully", "success");
        loadAll();
    } catch (err) {
        showToast(`Failed to deploy gateway: ${err.message}`, "error");
    } finally {
        hideLoading();
    }
}

// --- Test Gateway ---

function handleTestGateway() {
    const gwUrl = gatewayDashboardData?.gateway_url || "";
    renderTestGatewayModal(gwUrl);
}

async function loadKeyForTest() {
    try {
        const data = await ApiClient.keys.list();
        if (data.keys && data.keys.length > 0) {
            const keyId = extractKeyId(data.keys[0].name);
            const resp = await ApiClient.keys.getKeyString(keyId);
            document.getElementById("form-test-api-key").value = resp.key_string;
            showToast("API key loaded", "success");
        } else {
            showToast("No API keys found", "error");
        }
    } catch (err) {
        showToast(`Failed to load key: ${err.message}`, "error");
    }
}

async function submitTestGateway() {
    const gatewayUrl = document.getElementById("form-test-gateway-url").value.trim();
    const apiKey = document.getElementById("form-test-api-key").value.trim();
    const model = document.getElementById("form-test-model").value.trim();
    const prompt = document.getElementById("form-test-prompt").value.trim();

    if (!gatewayUrl || !apiKey) {
        showToast("Gateway URL and API key are required", "error");
        return;
    }

    const btn = document.getElementById("btn-submit-test");
    btn.disabled = true;
    btn.textContent = "Sending...";

    try {
        const result = await ApiClient.gateway.test({
            gateway_url: gatewayUrl,
            api_key: apiKey,
            model: model,
            prompt: prompt,
        });
        renderTestResult(result);
    } catch (err) {
        renderTestResult({ success: false, status_code: 0, error: err.message });
    } finally {
        btn.disabled = false;
        btn.textContent = "Send Request";
    }
}

// --- Proxy Handlers ---

async function handlePreviewProxy() {
    showLoading("Generating preview...");
    try {
        const files = await ApiClient.proxy.preview({
            vertex_ai_region: "us-central1",
            service_name: "vertex-ai-proxy",
        });
        hideLoading();
        renderCodePreviewModal(files);
    } catch (err) {
        hideLoading();
        showToast(`Preview failed: ${err.message}`, "error");
    }
}

async function submitDeployProxy() {
    const region = document.getElementById("form-vertex-region").value.trim();
    const serviceName = document.getElementById("form-proxy-name").value.trim();
    const saEmail = document.getElementById("form-proxy-sa").value.trim();

    closeModal();
    showLoading("Deploying proxy to Cloud Run... This may take 2-5 minutes.");
    try {
        await ApiClient.proxy.deploy({
            vertex_ai_region: region,
            service_name: serviceName,
            service_account_email: saEmail,
        });
        showToast("Proxy deployed successfully", "success");
        loadAll();
    } catch (err) {
        showToast(`Failed to deploy proxy: ${err.message}`, "error");
    } finally {
        hideLoading();
    }
}

// --- API Key Handlers ---

async function submitCreateKey() {
    const displayName = document.getElementById("form-key-name").value.trim();

    closeModal();
    showLoading("Creating API key...");
    try {
        const key = await ApiClient.keys.create({
            display_name: displayName,
        });
        hideLoading();
        if (key.key_string) {
            renderKeyStringModal(key.uid, key.key_string);
            showToast("API key created", "success");
        } else {
            showToast("API key created", "success");
        }
        loadApiKeysSection();
        loadDashboard();
    } catch (err) {
        hideLoading();
        showToast(`Failed to create key: ${err.message}`, "error");
    }
}

async function handleRevealKey(keyId) {
    showLoading("Fetching key string...");
    try {
        const resp = await ApiClient.keys.getKeyString(keyId);
        hideLoading();
        renderKeyStringModal(keyId, resp.key_string);
    } catch (err) {
        hideLoading();
        showToast(`Failed to get key string: ${err.message}`, "error");
    }
}

async function handleDeleteKey(keyId) {
    const confirmed = await showConfirmDialog("Delete this API key? This action cannot be undone.");
    if (!confirmed) return;

    showLoading("Deleting key...");
    try {
        await ApiClient.keys.delete(keyId);
        showToast("Key deleted", "success");
        loadApiKeysSection();
        loadDashboard();
    } catch (err) {
        showToast(`Failed to delete key: ${err.message}`, "error");
    } finally {
        hideLoading();
    }
}
