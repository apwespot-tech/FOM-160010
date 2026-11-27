<script setup lang="ts">
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import ProgressSpinner from "primevue/progressspinner";
import Toast from "primevue/toast";
import { computed, ref } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";

import AppHeader from "./components/AppHeader.vue";
import { useDelayedFlag } from "./composables/useDelayedFlag";

// На узком экране уведомление занимает ширину окна: фиксированные 25rem PrimeVue уходили бы за левый край
const TOAST_BREAKPOINTS = {
    "640px": { width: "calc(100vw - 2rem)", right: "1rem", left: "1rem" },
};

const route = useRoute();
const router = useRouter();
const isRouterReady = ref(false);
const hasStartFailed = ref(false);

const isStarting = computed(() => !isRouterReady.value && !hasStartFailed.value);
const isStartIndicatorVisible = useDelayedFlag(isStarting);
const hasHeader = computed(() => route.meta.isGuestOnly !== true);

router
    .isReady()
    .then(() => {
        isRouterReady.value = true;
    })
    .catch(() => {
        hasStartFailed.value = true;
    });

function reloadPage(): void {
    window.location.reload();
}
</script>

<template>
    <Toast position="top-right" :breakpoints="TOAST_BREAKPOINTS" />
    <ConfirmDialog />

    <template v-if="isRouterReady">
        <AppHeader v-if="hasHeader" />
        <main class="app-content">
            <RouterView />
        </main>
    </template>

    <main v-else-if="hasStartFailed" class="app-content">
        <div class="state-card" role="alert">
            <p class="state-card__title">Страница не загрузилась</p>
            <p class="state-card__text">Проверьте подключение и обновите страницу</p>
            <Button label="Обновить страницу" @click="reloadPage" />
        </div>
    </main>

    <main v-else class="app-content app-content--starting" :aria-busy="true" aria-label="Загрузка">
        <ProgressSpinner v-if="isStartIndicatorVisible" class="app-content__spinner" stroke-width="4" />
    </main>
</template>

<style scoped>
.app-content {
    width: 100%;
    max-width: 72rem;
    margin: 0 auto;
    padding: 2rem 1.5rem 3rem;
}

.app-content--starting {
    display: grid;
    min-height: 60vh;
    place-items: center;
}

.app-content__spinner {
    width: 3rem;
    height: 3rem;
}

@media (max-width: 40rem) {
    .app-content {
        padding: 1.25rem 1rem 2rem;
    }
}
</style>
