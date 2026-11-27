import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

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
    test: {
        // Тесты компонентов и функций, которым нужен document, идут в лёгком окружении браузера без самого браузера
        environment: "happy-dom",
        include: ["src/**/*.test.ts"],
    },
});
