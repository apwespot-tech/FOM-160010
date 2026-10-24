import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const defaultProxyTarget = "http://localhost:8000";
const proxyTarget = process.env.API_PROXY_TARGET || defaultProxyTarget;

export default defineConfig({
    plugins: [vue()],
    server: {
        port: 5173,
        strictPort: true,
        proxy: {
            "/api": {
                target: proxyTarget,
            },
        },
    },
});
