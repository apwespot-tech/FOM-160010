<script setup lang="ts">
import { computed } from "vue";

import type { ServiceDetail, ServiceState } from "../types/health";

const props = defineProps<{
    title: string;
    technology: string;
    state: ServiceState;
    details: ServiceDetail[];
}>();

const STATE_LABELS: Record<ServiceState, string> = {
    checking: "Проверка",
    offline: "Нет связи",
    online: "Работает",
    unknown: "Неизвестно",
};

const stateLabel = computed(() => STATE_LABELS[props.state]);
const badgeModifier = computed(() => `status-badge--${props.state}`);

function valueClass(detail: ServiceDetail): string {
    if (detail.isMissing) {
        return "service-card__value service-card__value--missing";
    }

    return "service-card__value";
}
</script>

<template>
    <article class="service-card">
        <header class="service-card__header">
            <div>
                <h3 class="service-card__title">{{ title }}</h3>
                <p class="service-card__technology">{{ technology }}</p>
            </div>
            <span class="status-badge" :class="badgeModifier">
                <span class="status-badge__dot" aria-hidden="true"></span>
                <span>{{ stateLabel }}</span>
            </span>
        </header>
        <dl class="service-card__details">
            <div v-for="detail in details" :key="detail.label" class="service-card__detail">
                <dt class="service-card__label">{{ detail.label }}</dt>
                <dd :class="valueClass(detail)">{{ detail.value }}</dd>
            </div>
        </dl>
    </article>
</template>

<style scoped>
.service-card {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    padding: 1.25rem 1.375rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-large);
    background: var(--color-surface);
}

.service-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}

.service-card__title {
    font-size: 1.0625rem;
    font-weight: 600;
    line-height: 1.4;
}

.service-card__technology {
    margin-top: 0.125rem;
    color: var(--color-text-secondary);
    font-size: 0.875rem;
}

.service-card__details {
    display: grid;
    gap: 0.625rem;
}

.service-card__detail {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding-top: 0.625rem;
    border-top: 1px solid var(--color-border);
}

.service-card__label {
    color: var(--color-text-tertiary);
    font-size: 0.875rem;
    font-weight: 600;
}

.service-card__value {
    font-size: 0.9375rem;
    font-variant-numeric: tabular-nums;
    text-align: right;
}

.service-card__value--missing {
    color: var(--color-text-tertiary);
}

.status-badge {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3125rem 0.75rem;
    border-radius: 999px;
    background: var(--badge-background);
    color: var(--badge-color);
    font-size: 0.8125rem;
    font-weight: 600;
    line-height: 1.2;
}

.status-badge__dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: currentColor;
}

.status-badge--checking {
    --badge-color: var(--color-warning);
    --badge-background: var(--color-warning-soft);
}

.status-badge--checking .status-badge__dot {
    animation: status-pulse 1.2s ease-in-out infinite;
}

.status-badge--online {
    --badge-color: var(--color-success);
    --badge-background: var(--color-success-soft);
}

.status-badge--offline {
    --badge-color: var(--color-danger);
    --badge-background: var(--color-danger-soft);
}

.status-badge--unknown {
    --badge-color: var(--color-neutral);
    --badge-background: var(--color-neutral-soft);
}

@keyframes status-pulse {
    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: 0.35;
    }
}

@media (prefers-reduced-motion: reduce) {
    .status-badge--checking .status-badge__dot {
        animation: none;
    }
}
</style>
