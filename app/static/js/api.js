const ApiClient = {
    async _request(url, options = {}) {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });
        if (!response.ok) {
            if (response.status === 204) return null;
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `Request failed: ${response.status}`);
        }
        if (response.status === 204) return null;
        return response.json();
    },

    async getDashboard() {
        return this._request("/api/dashboard");
    },

    gateway: {
        async listApis() {
            return ApiClient._request("/api/gateway/apis");
        },
        async createApi(apiId) {
            return ApiClient._request(`/api/gateway/apis?api_id=${encodeURIComponent(apiId)}`, { method: "POST" });
        },
        async getApi(apiId) {
            return ApiClient._request(`/api/gateway/apis/${encodeURIComponent(apiId)}`);
        },
        async deleteApi(apiId) {
            return ApiClient._request(`/api/gateway/apis/${encodeURIComponent(apiId)}`, { method: "DELETE" });
        },
        async createConfig(apiId, data) {
            return ApiClient._request(`/api/gateway/apis/${encodeURIComponent(apiId)}/configs`, {
                method: "POST",
                body: JSON.stringify(data),
            });
        },
        async listConfigs(apiId) {
            return ApiClient._request(`/api/gateway/apis/${encodeURIComponent(apiId)}/configs`);
        },
        async deleteConfig(apiId, configId) {
            return ApiClient._request(
                `/api/gateway/apis/${encodeURIComponent(apiId)}/configs/${encodeURIComponent(configId)}`,
                { method: "DELETE" }
            );
        },
        async createGateway(data) {
            return ApiClient._request("/api/gateway/gateways", {
                method: "POST",
                body: JSON.stringify(data),
            });
        },
        async getGateway(gwId, location) {
            return ApiClient._request(`/api/gateway/gateways/${encodeURIComponent(gwId)}?location=${encodeURIComponent(location)}`);
        },
        async updateGateway(gwId, data, location) {
            return ApiClient._request(`/api/gateway/gateways/${encodeURIComponent(gwId)}?location=${encodeURIComponent(location)}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            });
        },
        async deleteGateway(gwId, location) {
            return ApiClient._request(`/api/gateway/gateways/${encodeURIComponent(gwId)}?location=${encodeURIComponent(location)}`, {
                method: "DELETE",
            });
        },
        async getDashboard() {
            return ApiClient._request("/api/gateway/dashboard");
        },
    },

    proxy: {
        async getStatus(serviceName, region) {
            const params = new URLSearchParams();
            if (serviceName) params.set("service_name", serviceName);
            if (region) params.set("region", region);
            return ApiClient._request(`/api/proxy/status?${params}`);
        },
        async preview(data) {
            return ApiClient._request("/api/proxy/preview", {
                method: "POST",
                body: JSON.stringify(data),
            });
        },
        async deploy(data) {
            return ApiClient._request("/api/proxy/deploy", {
                method: "POST",
                body: JSON.stringify(data),
            });
        },
        async delete(serviceName, region) {
            const params = new URLSearchParams({ service_name: serviceName, region });
            return ApiClient._request(`/api/proxy?${params}`, { method: "DELETE" });
        },
    },

    keys: {
        async list() {
            return ApiClient._request("/api/keys");
        },
        async create(data) {
            return ApiClient._request("/api/keys", {
                method: "POST",
                body: JSON.stringify(data),
            });
        },
        async getKeyString(keyId) {
            return ApiClient._request(`/api/keys/${encodeURIComponent(keyId)}/key-string`);
        },
        async delete(keyId) {
            return ApiClient._request(`/api/keys/${encodeURIComponent(keyId)}`, {
                method: "DELETE",
            });
        },
    },
};
