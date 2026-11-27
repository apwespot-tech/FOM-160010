<script setup lang="ts">
defineProps<{
    title: string;
}>();
</script>

<template>
    <div class="auth-page">
        <section class="auth-card" :aria-label="title">
            <div class="auth-card__brand">
                <svg class="auth-card__mark" viewBox="0 0 32 32" aria-hidden="true">
                    <rect width="32" height="32" rx="8" />
                    <path d="M8 21.5 13.5 16l4 3.5L24 11" />
                    <circle cx="24" cy="11" r="2.25" />
                </svg>
                <span class="auth-card__brand-title">Финансовый планер</span>
            </div>
            <h1 class="auth-card__title">{{ title }}</h1>
            <slot />
        </section>
    </div>
</template>

<style scoped>
.auth-page {
    display: grid;
    min-height: calc(100vh - 5rem);
    place-items: center;
}

.auth-card {
    display: grid;
    gap: 1.25rem;
    width: 100%;
    max-width: 26rem;
    padding: 2rem 1.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-large);
    background: var(--color-surface);
}

.auth-card__brand {
    display: flex;
    align-items: center;
    gap: 0.625rem;
}

.auth-card__mark {
    width: 2.25rem;
    height: 2.25rem;
    flex-shrink: 0;
}

.auth-card__mark rect {
    fill: var(--color-surface-raised);
}

.auth-card__mark path {
    fill: none;
    stroke: var(--color-accent);
    stroke-width: 2.75;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.auth-card__mark circle {
    fill: var(--color-success);
}

.auth-card__brand-title {
    color: var(--color-text-secondary);
    font-weight: 600;
}

.auth-card__title {
    font-size: 1.5rem;
    font-weight: 700;
    line-height: 1.2;
}

@media (max-width: 40rem) {
    .auth-page {
        min-height: auto;
    }

    .auth-card {
        padding: 1.5rem 1.25rem;
    }
}
</style>
