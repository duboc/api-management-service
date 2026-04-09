function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return "\u2014";
    return new Date(dateStr).toLocaleString();
}

function extractKeyId(name) {
    const parts = name.split("/");
    return parts[parts.length - 1];
}

// --- Dashboard ---

function renderDashboard(data) {
    const cards = [
        {
            label: "Gateway",
            value: data.api_gateway_deployed ? "Deployed" : "Not Deployed",
            color: data.api_gateway_deployed ? "green" : "gray",
            sub: data.gateway_url ? data.gateway_url.replace("https://", "") : "",
            icon: "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z",
        },
        {
            label: "Proxy",
            value: data.proxy_deployed ? "Running" : "Not Deployed",
            color: data.proxy_deployed ? "green" : "gray",
            sub: data.proxy_url ? data.proxy_url.replace("https://", "") : "",
            icon: "M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2",
        },
        {
            label: "API Keys",
            value: data.api_key_count,
            color: "blue",
            sub: "",
            icon: "M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z",
        },
    ];

    const container = document.getElementById("dashboard-cards");
    container.innerHTML = cards.map(card => `
        <div class="bg-white rounded-lg shadow p-5">
            <div class="flex items-center gap-3 mb-2">
                <div class="p-2 bg-${card.color}-100 rounded-full">
                    <svg class="w-5 h-5 text-${card.color}-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${card.icon}"/>
                    </svg>
                </div>
                <p class="text-sm text-gray-500">${card.label}</p>
            </div>
            <p class="text-xl font-bold text-gray-900">${card.value}</p>
            ${card.sub ? `<p class="text-xs text-gray-400 mt-1 truncate" title="${escapeHtml(card.sub)}">${escapeHtml(card.sub)}</p>` : ""}
        </div>
    `).join("");

    // Console links
    if (data.gateway_console_url) {
        container.innerHTML += `
            <div class="bg-white rounded-lg shadow p-5 col-span-2 md:col-span-3 flex gap-4 text-sm">
                <a href="${escapeHtml(data.gateway_console_url)}" target="_blank" class="text-blue-600 hover:underline">API Gateway Console</a>
                <a href="${escapeHtml(data.cloud_run_console_url)}" target="_blank" class="text-blue-600 hover:underline">Cloud Run Console</a>
                <a href="${escapeHtml(data.vertex_ai_console_url)}" target="_blank" class="text-blue-600 hover:underline">Vertex AI Console</a>
            </div>
        `;
    }
}

// --- Gateway Section ---

function renderGatewaySection(gwDashboard) {
    const container = document.getElementById("gateway-section");

    if (!gwDashboard.api_exists) {
        container.innerHTML = `
            <div class="text-center py-6 text-gray-500">
                <p class="mb-2">No API Gateway API found.</p>
                <p class="text-sm">Click <strong>Create API</strong> to get started.</p>
            </div>
        `;
        return;
    }

    let html = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div class="bg-gray-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">API Name</p>
                <p class="font-mono text-sm">${escapeHtml(gwDashboard.api_name)}</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Managed Service</p>
                <p class="font-mono text-xs break-all">${escapeHtml(gwDashboard.managed_service) || "\u2014"}</p>
            </div>
        </div>
    `;

    if (gwDashboard.gateway_exists) {
        html += `
            <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                <div class="flex items-center gap-2 mb-2">
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">${escapeHtml(gwDashboard.gateway_state)}</span>
                    <span class="text-sm font-medium text-green-800">Gateway Deployed</span>
                </div>
                <p class="text-sm text-gray-600">URL: <a href="${escapeHtml(gwDashboard.gateway_url)}" target="_blank" class="text-blue-600 hover:underline font-mono text-xs">${escapeHtml(gwDashboard.gateway_url)}</a></p>
                <p class="text-sm text-gray-600 mt-1">Active Config: <span class="font-mono text-xs">${escapeHtml(gwDashboard.active_config)}</span></p>
            </div>
            <div id="curl-example" class="mb-4 hidden">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-sm font-medium text-gray-700">curl Example</h3>
                    <button onclick="copyCurlExample()" class="text-xs text-blue-600 hover:text-blue-800">Copy</button>
                </div>
                <pre id="curl-example-code" class="bg-gray-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto whitespace-pre"></pre>
            </div>
        `;
    } else {
        html += `
            <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                <p class="text-sm text-amber-800">Gateway not yet deployed. Create a config and deploy a gateway.</p>
            </div>
        `;
    }

    // Configs list
    if (gwDashboard.configs && gwDashboard.configs.length > 0) {
        html += `
            <h3 class="text-sm font-medium text-gray-700 mb-2">API Configs</h3>
            <div class="space-y-2">
                ${gwDashboard.configs.map(cfg => {
                    const cfgName = extractKeyId(cfg.name);
                    return `
                        <div class="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2">
                            <div>
                                <span class="font-mono text-sm">${escapeHtml(cfgName)}</span>
                                <span class="ml-2 px-2 py-0.5 text-xs rounded-full ${cfg.state === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}">${escapeHtml(cfg.state)}</span>
                            </div>
                            <span class="text-xs text-gray-400">${formatDate(cfg.create_time)}</span>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    container.innerHTML = html;
}

// --- Proxy Section ---

function renderProxySection(proxyStatus) {
    const container = document.getElementById("proxy-section");

    if (!proxyStatus.deployed) {
        container.innerHTML = `
            <div class="text-center py-6 text-gray-500">
                <p class="mb-2">Transparent auth proxy not deployed.</p>
                <p class="text-sm">Click <strong>Deploy Proxy</strong> to deploy the Cloud Run proxy that adds OAuth2 tokens for Vertex AI.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="bg-gray-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Service</p>
                <p class="font-mono text-sm">${escapeHtml(proxyStatus.service_name)}</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">URL</p>
                <p class="font-mono text-xs break-all"><a href="${escapeHtml(proxyStatus.url)}" target="_blank" class="text-blue-600 hover:underline">${escapeHtml(proxyStatus.url)}</a></p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Type</p>
                <p class="text-sm">Transparent auth proxy (forwards all paths to Vertex AI)</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Region</p>
                <p class="text-sm">${escapeHtml(proxyStatus.region)}</p>
            </div>
        </div>
        ${proxyStatus.logs_url ? `<p class="mt-3 text-sm"><a href="${escapeHtml(proxyStatus.logs_url)}" target="_blank" class="text-blue-600 hover:underline">View Logs</a></p>` : ""}
    `;
}

// --- API Keys Section ---

function renderApiKeysSection(keysData) {
    const container = document.getElementById("keys-section");

    if (!keysData.keys || keysData.keys.length === 0) {
        container.innerHTML = `
            <div class="text-center py-6 text-gray-500">
                <p>No API keys found. Create one to access the gateway.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <table class="min-w-full">
            <thead>
                <tr>
                    <th class="text-left text-xs font-medium text-gray-500 uppercase pb-2">Display Name</th>
                    <th class="text-left text-xs font-medium text-gray-500 uppercase pb-2">Key ID</th>
                    <th class="text-left text-xs font-medium text-gray-500 uppercase pb-2">Created</th>
                    <th class="text-right text-xs font-medium text-gray-500 uppercase pb-2">Actions</th>
                </tr>
            </thead>
            <tbody id="keys-table-body" class="divide-y divide-gray-100">
                ${keysData.keys.map(key => {
                    const keyId = extractKeyId(key.name);
                    return `
                        <tr>
                            <td class="py-3 text-sm font-medium text-gray-900">${escapeHtml(key.display_name) || "Unnamed"}</td>
                            <td class="py-3 text-sm text-gray-500 font-mono">${escapeHtml(keyId)}</td>
                            <td class="py-3 text-sm text-gray-500">${formatDate(key.create_time)}</td>
                            <td class="py-3 text-right">
                                <button class="text-blue-600 hover:text-blue-800 text-sm mr-2" data-action="reveal-key" data-key-id="${keyId}">Show Key</button>
                                <button class="text-red-600 hover:text-red-800 text-sm" data-action="delete-key" data-key-id="${keyId}">Delete</button>
                            </td>
                        </tr>
                    `;
                }).join("")}
            </tbody>
        </table>
    `;
}

// --- Modal Renderers ---

function renderCreateApiModal() {
    document.getElementById("modal-title").textContent = "Create API";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">API ID</label>
                <input type="text" id="form-api-id" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="vertex-proxy-api" pattern="[a-z0-9-]+" title="Lowercase letters, numbers, and dashes only">
                <p class="text-xs text-gray-400 mt-1">Lowercase letters, numbers, dashes. Max 63 chars.</p>
            </div>
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
        <button onclick="submitCreateApi()" class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700">Create</button>
    `;
    openModal();
}

function renderCreateConfigModal(apiId) {
    document.getElementById("modal-title").textContent = "Create API Config";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Config ID</label>
                <input type="text" id="form-config-id" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="vertex-proxy-config-v1">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Backend URL (Cloud Run service URL)</label>
                <input type="text" id="form-backend-url" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="https://vertex-ai-proxy-abc123-uc.a.run.app">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Service Account Email</label>
                <input type="text" id="form-sa-email" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="compute@developer.gserviceaccount.com">
                <p class="text-xs text-gray-400 mt-1">Must have roles/run.invoker to call the Cloud Run proxy.</p>
            </div>
            <input type="hidden" id="form-api-id-for-config" value="${escapeHtml(apiId)}">
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
        <button onclick="submitCreateConfig()" class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700">Create Config</button>
    `;
    openModal();
}

function renderDeployGatewayModal(apiId, configs) {
    const configOptions = configs.map(c => {
        const cName = extractKeyId(c.name);
        return `<option value="${escapeHtml(cName)}">${escapeHtml(cName)}</option>`;
    }).join("");

    document.getElementById("modal-title").textContent = "Deploy Gateway";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Gateway ID</label>
                <input type="text" id="form-gateway-id" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="vertex-proxy-gw" value="${escapeHtml(apiId)}">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">API Config</label>
                <select id="form-gateway-config" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                    ${configOptions || '<option value="">No configs available</option>'}
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Region</label>
                <select id="form-gateway-region" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                    <option value="us-central1">us-central1</option>
                    <option value="us-east1">us-east1</option>
                    <option value="us-east4">us-east4</option>
                    <option value="us-west2">us-west2</option>
                    <option value="europe-west1">europe-west1</option>
                    <option value="europe-west2">europe-west2</option>
                    <option value="asia-northeast1">asia-northeast1</option>
                    <option value="australia-southeast1">australia-southeast1</option>
                </select>
            </div>
            <p class="text-xs text-amber-600">Deploying a gateway may take 2-5 minutes.</p>
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
        <button onclick="submitDeployGateway()" class="px-4 py-2 text-white bg-green-600 rounded-lg hover:bg-green-700">Deploy</button>
    `;
    openModal();
}

function renderDeployProxyModal() {
    document.getElementById("modal-title").textContent = "Deploy Transparent Auth Proxy";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-4">
            <p class="text-sm text-gray-600">
                Deploys a transparent Cloud Run proxy that forwards all requests to Vertex AI,
                adding only the OAuth2 bearer token. Works with any Vertex AI method
                (generateContent, predict, countTokens, etc.).
            </p>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Vertex AI Region</label>
                <input type="text" id="form-vertex-region" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" value="us-central1">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Service Name</label>
                <input type="text" id="form-proxy-name" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" value="vertex-ai-proxy">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Service Account Email (optional)</label>
                <input type="text" id="form-proxy-sa" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Leave empty for default compute SA">
                <p class="text-xs text-gray-400 mt-1">Must have roles/aiplatform.user</p>
            </div>
            <p class="text-xs text-amber-600">Deployment may take 2-5 minutes.</p>
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
        <button onclick="submitDeployProxy()" class="px-4 py-2 text-white bg-green-600 rounded-lg hover:bg-green-700">Deploy</button>
    `;
    openModal();
}

function renderCreateKeyModal() {
    document.getElementById("modal-title").textContent = "Create API Key";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                <input type="text" id="form-key-name" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="My API Key">
            </div>
            <p class="text-xs text-gray-500">Key will be restricted to the API Gateway managed service.</p>
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
        <button onclick="submitCreateKey()" class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700">Create Key</button>
    `;
    openModal();
}

function renderKeyStringModal(keyId, keyString) {
    document.getElementById("modal-title").textContent = "API Key String";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-3">
            <p class="text-sm text-gray-500">Key ID: <span class="font-mono">${escapeHtml(keyId)}</span></p>
            <div class="bg-gray-50 rounded-lg p-4">
                <code class="font-mono text-sm break-all select-all">${escapeHtml(keyString)}</code>
            </div>
            <button onclick="navigator.clipboard.writeText('${escapeHtml(keyString)}').then(() => showToast('Copied to clipboard', 'success'))" class="text-sm text-blue-600 hover:text-blue-800">Copy to clipboard</button>
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Close</button>
    `;
    openModal();
}

function renderTestGatewayModal(gatewayUrl) {
    document.getElementById("modal-title").textContent = "Test API Gateway";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Gateway URL</label>
                <input type="text" id="form-test-gateway-url" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" value="${escapeHtml(gatewayUrl || '')}">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <div class="flex gap-2">
                    <input type="text" id="form-test-api-key" class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="AIza...">
                    <button onclick="loadKeyForTest()" class="px-3 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 whitespace-nowrap" title="Load first available key">Load Key</button>
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                <input type="text" id="form-test-model" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" value="gemini-2.5-flash">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
                <textarea id="form-test-prompt" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">Say hello in one sentence.</textarea>
            </div>
            <div id="test-result" class="hidden"></div>
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Close</button>
        <button onclick="submitTestGateway()" id="btn-submit-test" class="px-4 py-2 text-white bg-purple-600 rounded-lg hover:bg-purple-700">Send Request</button>
    `;
    openModal();
}

function renderTestResult(result) {
    const container = document.getElementById("test-result");
    container.classList.remove("hidden");

    if (result.success) {
        container.innerHTML = `
            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                <div class="flex items-center gap-2 mb-2">
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">${result.status_code}</span>
                    <span class="text-sm font-medium text-green-800">Success</span>
                </div>
                <div class="bg-white rounded p-3 mt-2">
                    <p class="text-sm text-gray-800 whitespace-pre-wrap">${escapeHtml(result.response_text)}</p>
                </div>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-center gap-2 mb-2">
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">${result.status_code || 'Error'}</span>
                    <span class="text-sm font-medium text-red-800">Failed</span>
                </div>
                <pre class="text-xs text-red-700 mt-2 whitespace-pre-wrap overflow-x-auto">${escapeHtml(result.error)}</pre>
            </div>
        `;
    }
}

function renderCodePreviewModal(files) {
    document.getElementById("modal-title").textContent = "Proxy Source Code";
    document.getElementById("modal-body").innerHTML = `
        <div class="space-y-4">
            <div>
                <h4 class="text-sm font-medium text-gray-700 mb-1">main.py</h4>
                <pre class="bg-gray-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-60">${escapeHtml(files.main_py)}</pre>
            </div>
            <div>
                <h4 class="text-sm font-medium text-gray-700 mb-1">requirements.txt</h4>
                <pre class="bg-gray-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto">${escapeHtml(files.requirements_txt)}</pre>
            </div>
            <div>
                <h4 class="text-sm font-medium text-gray-700 mb-1">Dockerfile</h4>
                <pre class="bg-gray-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto">${escapeHtml(files.dockerfile)}</pre>
            </div>
        </div>
    `;
    document.getElementById("modal-footer").innerHTML = `
        <button onclick="closeModal()" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Close</button>
    `;
    openModal();
}

// --- curl Example ---

function renderCurlExample(gatewayUrl, apiKey, model) {
    const container = document.getElementById("curl-example");
    const codeEl = document.getElementById("curl-example-code");
    if (!container || !codeEl) return;

    if (!gatewayUrl || !apiKey) {
        container.classList.add("hidden");
        return;
    }

    model = model || "gemini-2.5-flash";
    const curl = `curl -X POST "${gatewayUrl}/publishers/google/models/${model}/generateContent?key=${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "contents": [{
      "role": "user",
      "parts": [{"text": "Explain API Gateway in one sentence."}]
    }]
  }'`;

    codeEl.textContent = curl;
    container.classList.remove("hidden");
}

function copyCurlExample() {
    const code = document.getElementById("curl-example-code");
    if (code) {
        navigator.clipboard.writeText(code.textContent)
            .then(() => showToast("Copied to clipboard", "success"));
    }
}

// --- Utilities ---

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const colors = { success: "bg-green-500", error: "bg-red-500", info: "bg-blue-500" };
    const toast = document.createElement("div");
    toast.className = `${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg toast-enter mb-2 flex items-center justify-between min-w-[300px]`;
    toast.innerHTML = `<span>${escapeHtml(message)}</span><button onclick="this.parentElement.remove()" class="ml-4 text-white/80 hover:text-white">&times;</button>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove("toast-enter");
        toast.classList.add("toast-exit");
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function showLoading(text = "") {
    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("loading-text").textContent = text;
}

function hideLoading() {
    document.getElementById("loading").classList.add("hidden");
}

function showConfirmDialog(message) {
    return new Promise((resolve) => {
        const backdrop = document.createElement("div");
        backdrop.className = "fixed inset-0 z-[60] flex items-center justify-center modal-backdrop";
        backdrop.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4">
                <p class="text-gray-700 mb-4">${escapeHtml(message)}</p>
                <div class="flex justify-end gap-2">
                    <button id="confirm-cancel" class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
                    <button id="confirm-ok" class="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700">Confirm</button>
                </div>
            </div>
        `;
        document.body.appendChild(backdrop);
        backdrop.querySelector("#confirm-cancel").onclick = () => { backdrop.remove(); resolve(false); };
        backdrop.querySelector("#confirm-ok").onclick = () => { backdrop.remove(); resolve(true); };
    });
}

function openModal() {
    document.getElementById("app-modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("app-modal").classList.add("hidden");
}
