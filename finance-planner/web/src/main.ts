import { VueQueryPlugin } from "@tanstack/vue-query";
import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import ConfirmationService from "primevue/confirmationservice";
import ToastService from "primevue/toastservice";
import { createApp } from "vue";

import "./assets/styles/main.css";

import App from "./App.vue";
import { router } from "./router";
import { setUnauthenticatedHandler } from "./services/apiClient";
import { createQueryClient } from "./services/queryClient";
import { useSessionStore } from "./stores/session";
import { plannerPreset } from "./theme/plannerPreset";
import { russianLocale } from "./theme/russianLocale";

const application = createApp(App);
const pinia = createPinia();
const queryClient = createQueryClient();

application.use(pinia);
application.use(router);
application.use(VueQueryPlugin, { queryClient });
application.use(ToastService);
application.use(ConfirmationService);

application.use(PrimeVue, {
    theme: {
        preset: plannerPreset,
        // Класс стоит на <html> всегда: у планера только тёмная тема
        options: { darkModeSelector: ".app-dark" },
    },
    locale: russianLocale,
});

setUnauthenticatedHandler(() => {
    const session = useSessionStore(pinia);
    const currentRoute = router.currentRoute.value;

    session.forgetUser();
    queryClient.clear();

    if (!currentRoute.meta.isPublic) {
        void router.push({ name: "login", query: { next: currentRoute.fullPath } });
    }
});

// Приложение монтируется сразу: пока идёт первая проверка сессии, App.vue сам показывает индикатор или сбой загрузки
application.mount("#app");
