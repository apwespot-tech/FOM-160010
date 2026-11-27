<script setup lang="ts">
defineProps<{
    title: string;
    description: string;
}>();
</script>

<template>
    <section class="section-placeholder">
        <header class="page-heading">
            <h1 class="page-heading__title">{{ title }}</h1>
        </header>
        <div class="section-placeholder__card">
            <p class="section-placeholder__status">Раздел в разработке</p>
            <p class="section-placeholder__description">{{ description }}</p>
        </div>
    </section>
</template>

<style scoped>
.section-placeholder__card {
    display: grid;
    gap: 0.5rem;
    max-width: 40rem;
    padding: 1.25rem 1.375rem;
    border: 1px dashed var(--color-border-strong);
    border-radius: var(--radius-large);
    background: var(--color-surface);
}

.section-placeholder__status {
    font-weight: 600;
}

.section-placeholder__description {
    color: var(--color-text-secondary);
}
</style>
