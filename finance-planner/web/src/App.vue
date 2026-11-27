<script setup lang="ts">
import ConfirmDialog from "primevue/confirmdialog";
import Toast from "primevue/toast";
import { computed } from "vue";
import { RouterView, useRoute } from "vue-router";

import AppHeader from "./components/AppHeader.vue";

const route = useRoute();
const hasHeader = computed(() => route.meta.isGuestOnly !== true);
</script>

<template>
    <Toast position="top-right" />
    <ConfirmDialog />
    <AppHeader v-if="hasHeader" />
    <main class="app-content">
        <RouterView />
    </main>
</template>

<style scoped>
.app-content {
    width: 100%;
    max-width: 72rem;
    margin: 0 auto;
    padding: 2rem 1.5rem 3rem;
}

@media (max-width: 40rem) {
    .app-content {
        padding: 1.25rem 1rem 2rem;
    }
}
</style>
