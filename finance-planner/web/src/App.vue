<script setup lang="ts">
import { computed, onMounted, version as vueVersion } from "vue";

import ServiceCard from "./components/ServiceCard.vue";
import { useHealthCheck } from "./composables/useHealthCheck";
import type { ServiceDetail } from "./types/health";

const EMPTY_VALUE = "нет данных";

const { apiState, checkNow, checkedAt, databaseState, isChecking, lastResult } = useHealthCheck();

const timeFormatter = new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
});

function createDetail(label: string, value: string | null): ServiceDetail {
    if (value === null) {
        return { label, value: EMPTY_VALUE, isMissing: true };
    }

    return { label, value, isMissing: false };
}

function formatMilliseconds(value: number | null | undefined): string | null {
    if (value === null || value === undefined) {
        return null;
    }

    return `${value} мс`;
}

function describeBuildMode(): string {
    if (import.meta.env.DEV) {
        return "разработка";
    }

    return "сборка";
}

const interfaceDetails = computed<ServiceDetail[]>(() => [
    createDetail("Фреймворк", `Vue ${vueVersion}`),
    createDetail("Режим", describeBuildMode()),
]);

const apiDetails = computed<ServiceDetail[]>(() => {
    const health = lastResult.value?.health ?? null;
    const responseTimeMs = lastResult.value?.responseTimeMs ?? null;

    return [
        createDetail("Django", health?.djangoVersion ?? null),
        createDetail("Python", health?.pythonVersion ?? null),
        createDetail("Время ответа", formatMilliseconds(responseTimeMs)),
    ];
});

const databaseDetails = computed<ServiceDetail[]>(() => {
    const database = lastResult.value?.health?.database ?? null;

    return [
        createDetail("PostgreSQL", database?.version ?? null),
        createDetail("Время запроса", formatMilliseconds(database?.queryTimeMs)),
    ];
});

const summaryText = computed(() => {
    if (isChecking.value || lastResult.value === null) {
        return "Проверка сервисов…";
    }

    const allServicesOnline = apiState.value === "online" && databaseState.value === "online";

    if (allServicesOnline) {
        return "Все сервисы работают";
    }

    return "Часть сервисов недоступна";
});

const lastCheckText = computed(() => {
    if (checkedAt.value === null) {
        return "Идёт первая проверка";
    }

    return `Последняя проверка в ${timeFormatter.format(checkedAt.value)}`;
});

const buttonLabel = computed(() => {
    if (isChecking.value) {
        return "Проверка…";
    }

    return "Проверить снова";
});

onMounted(() => {
    void checkNow();
});
</script>

<template>
    <div class="page">
        <header class="page-header">
            <div class="brand">
                <svg class="brand__mark" viewBox="0 0 32 32" aria-hidden="true">
                    <rect width="32" height="32" rx="8" />
                    <path d="M8 21.5 13.5 16l4 3.5L24 11" />
                    <circle cx="24" cy="11" r="2.25" />
                </svg>
                <div>
                    <p class="brand__caption">Окружение разработки</p>
                    <h1 class="brand__title">Финансовый планер</h1>
                </div>
            </div>
            <button class="check-button" type="button" :disabled="isChecking" @click="checkNow">
                {{ buttonLabel }}
            </button>
        </header>

        <main class="page-content">
            <section class="summary" role="status" aria-live="polite">
                <p class="summary__title">{{ summaryText }}</p>
                <p class="summary__meta">{{ lastCheckText }}</p>
            </section>

            <section aria-labelledby="services-title">
                <h2 id="services-title" class="section-title">Сервисы</h2>
                <div class="services">
                    <ServiceCard title="Интерфейс" technology="Vue 3 · Vite" state="online" :details="interfaceDetails" />
                    <ServiceCard title="API" technology="Django · Django Ninja" :state="apiState" :details="apiDetails" />
                    <ServiceCard title="База данных" technology="PostgreSQL" :state="databaseState" :details="databaseDetails" />
                </div>
            </section>
        </main>
    </div>
</template>

<style scoped>
.page {
    width: 100%;
    max-width: 72rem;
    margin: 0 auto;
    padding: 2.5rem 1.5rem 3rem;
}

.page-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1.25rem 2rem;
}

.brand {
    display: flex;
    align-items: center;
    gap: 0.875rem;
}

.brand__mark {
    width: 2.75rem;
    height: 2.75rem;
    flex-shrink: 0;
}

.brand__mark rect {
    fill: var(--color-surface-raised);
}

.brand__mark path {
    fill: none;
    stroke: var(--color-accent);
    stroke-width: 2.75;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.brand__mark circle {
    fill: var(--color-success);
}

.brand__caption {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.brand__title {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.01em;
}

.check-button {
    min-height: 2.75rem;
    padding: 0 1.25rem;
    border: 0;
    border-radius: var(--radius-medium);
    background: var(--color-accent);
    color: var(--color-on-accent);
    font: inherit;
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.check-button:hover:not(:disabled) {
    background: var(--color-accent-hover);
}

.check-button:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
}

.check-button:disabled {
    background: var(--color-surface-raised);
    color: var(--color-text-tertiary);
    cursor: progress;
}

.page-content {
    display: grid;
    gap: 2rem;
    margin-top: 2.5rem;
}

.summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem 1.5rem;
    padding: 1.125rem 1.375rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-large);
    background: var(--color-surface);
}

.summary__title {
    font-size: 1.125rem;
    font-weight: 700;
}

.summary__meta {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    font-variant-numeric: tabular-nums;
}

.section-title {
    margin-bottom: 1rem;
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.services {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
    gap: 1rem;
}

@media (max-width: 40rem) {
    .page {
        padding: 1.5rem 1rem 2rem;
    }

    .brand__title {
        font-size: 1.5rem;
    }

    .check-button {
        width: 100%;
    }
}
</style>
