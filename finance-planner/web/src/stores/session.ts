import { defineStore } from "pinia";
import { computed, ref } from "vue";

import * as authApi from "../services/authApi";
import type { User } from "../types/api";

export const useSessionStore = defineStore("session", () => {
    const currentUser = ref<User | null>(null);
    const isLoaded = ref(false);
    const hasLoadFailed = ref(false);
    let pendingLoad: Promise<void> | null = null;

    const isAuthenticated = computed(() => currentUser.value !== null);

    async function readCurrentUser(): Promise<void> {
        try {
            currentUser.value = await authApi.fetchCurrentUser();
            isLoaded.value = true;
            hasLoadFailed.value = false;
        } catch {
            // API недоступен: защита маршрутов уведёт на страницу проверки сервисов, а следующий переход спросит снова
            hasLoadFailed.value = true;
        }
    }

    async function loadCurrentUser(): Promise<void> {
        if (isLoaded.value) {
            return;
        }

        if (pendingLoad === null) {
            pendingLoad = readCurrentUser().finally(() => {
                pendingLoad = null;
            });
        }

        await pendingLoad;
    }

    function rememberUser(user: User): void {
        currentUser.value = user;
        isLoaded.value = true;
        hasLoadFailed.value = false;
    }

    function forgetUser(): void {
        currentUser.value = null;
        isLoaded.value = true;
    }

    async function logIn(username: string, password: string): Promise<void> {
        rememberUser(await authApi.logIn(username, password));
    }

    async function register(username: string, password: string, timeZone: string): Promise<void> {
        rememberUser(await authApi.register(username, password, timeZone));
    }

    async function logOut(): Promise<void> {
        await authApi.logOut();
        forgetUser();
    }

    async function updateTimeZone(timeZone: string): Promise<void> {
        rememberUser(await authApi.updateTimeZone(timeZone));
    }

    return {
        currentUser,
        forgetUser,
        hasLoadFailed,
        isAuthenticated,
        isLoaded,
        loadCurrentUser,
        logIn,
        logOut,
        register,
        updateTimeZone,
    };
});
