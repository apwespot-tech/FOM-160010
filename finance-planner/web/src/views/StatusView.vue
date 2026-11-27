<script setup lang="ts">
import Button from "primevue/button";
import { computed, onMounted, version as vueVersion } from "vue";

import ServiceCard from "../components/ServiceCard.vue";
import { useHealthCheck } from "../composables/useHealthCheck";
import type { ServiceDetail } from "../types/health";

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
    <div class="status-page">
        <header class="page-heading">
            <div>
                <p class="page-heading__caption">Окружение разработки</p>
                <h1 class="page-heading__title">Состояние сервисов</h1>
            </div>
            <Button class="status-page__button" :label="buttonLabel" :disabled="isChecking" @click="checkNow" />
        </header>

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
    </div>
</template>

<style scoped>
.status-page {
    display: grid;
    gap: 2rem;
}

.status-page .page-heading {
    margin-bottom: 0;
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

.services {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
    gap: 1rem;
}

@media (max-width: 40rem) {
    .status-page__button {
        width: 100%;
    }
}
</style>
