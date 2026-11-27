<script setup lang="ts">
import { useQueryClient } from "@tanstack/vue-query";
import Button from "primevue/button";
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { useNotifier } from "../composables/useNotifier";
import { useSessionStore } from "../stores/session";

interface NavigationLink {
    routeName: string;
    label: string;
}

const NAVIGATION_LINKS: NavigationLink[] = [
    { routeName: "dashboard", label: "Сводка" },
    { routeName: "accounts", label: "Счета" },
    { routeName: "operations", label: "Операции" },
    { routeName: "budgets", label: "Бюджеты" },
    { routeName: "goals", label: "Цели" },
    { routeName: "recurring", label: "Периодические" },
];

const HOME_ROUTE = { name: "dashboard" };
const LOGIN_ROUTE = { name: "login" };

const session = useSessionStore();
const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();
const { notifyError } = useNotifier();

const isMenuOpen = ref(false);
const isLoggingOut = ref(false);

const username = computed(() => session.currentUser?.username ?? "");
const menuClasses = computed(() => ({ "app-header__menu--open": isMenuOpen.value }));

function toggleMenu(): void {
    isMenuOpen.value = !isMenuOpen.value;
}

function buildLinkTarget(link: NavigationLink): { name: string } {
    return { name: link.routeName };
}

async function logOut(): Promise<void> {
    isLoggingOut.value = true;

    try {
        await session.logOut();
        queryClient.clear();
        await router.push(LOGIN_ROUTE);
    } catch (error) {
        notifyError(error);
    } finally {
        isLoggingOut.value = false;
    }
}

watch(
    () => route.fullPath,
    () => {
        isMenuOpen.value = false;
    },
);
</script>

<template>
    <header class="app-header">
        <div class="app-header__bar">
            <RouterLink class="brand" :to="HOME_ROUTE">
                <svg class="brand__mark" viewBox="0 0 32 32" aria-hidden="true">
                    <rect width="32" height="32" rx="8" />
                    <path d="M8 21.5 13.5 16l4 3.5L24 11" />
                    <circle cx="24" cy="11" r="2.25" />
                </svg>
                <span class="brand__title">Финансовый планер</span>
            </RouterLink>

            <template v-if="session.isAuthenticated">
                <button
                    class="app-header__menu-button"
                    type="button"
                    aria-controls="main-navigation"
                    :aria-expanded="isMenuOpen"
                    @click="toggleMenu"
                >
                    Меню
                </button>

                <div id="main-navigation" class="app-header__menu" :class="menuClasses">
                    <nav class="app-nav" aria-label="Разделы">
                        <RouterLink
                            v-for="link in NAVIGATION_LINKS"
                            :key="link.routeName"
                            class="app-nav__link"
                            exact-active-class="app-nav__link--active"
                            :to="buildLinkTarget(link)"
                        >
                            {{ link.label }}
                        </RouterLink>
                    </nav>

                    <div class="app-header__user">
                        <span class="app-header__username" :title="username">{{ username }}</span>
                        <Button label="Выйти" severity="secondary" size="small" outlined :loading="isLoggingOut" @click="logOut" />
                    </div>
                </div>
            </template>

            <RouterLink v-else class="app-header__login-link" :to="LOGIN_ROUTE">Войти</RouterLink>
        </div>
    </header>
</template>

<style scoped>
.app-header {
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
}

.app-header__bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem 1.5rem;
    max-width: 72rem;
    min-height: 4rem;
    margin: 0 auto;
    padding: 0.625rem 1.5rem;
}

.brand {
    display: inline-flex;
    align-items: center;
    gap: 0.625rem;
    border-radius: var(--radius-medium);
    color: var(--color-text);
    text-decoration: none;
}

.brand:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
}

.brand__mark {
    width: 2.25rem;
    height: 2.25rem;
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

.brand__title {
    font-size: 1.0625rem;
    font-weight: 700;
    white-space: nowrap;
}

.app-header__menu-button {
    display: none;
}

.app-header__menu {
    display: flex;
    flex: 1;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem 1.5rem;
}

.app-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
}

.app-nav__link,
.app-header__login-link {
    display: inline-flex;
    align-items: center;
    min-height: 2.25rem;
    padding: 0 0.75rem;
    border-radius: var(--radius-medium);
    color: var(--color-text-secondary);
    font-size: 0.9375rem;
    font-weight: 600;
    text-decoration: none;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.app-nav__link:hover,
.app-header__login-link:hover {
    background: var(--color-surface-raised);
    color: var(--color-text);
}

.app-nav__link:focus-visible,
.app-header__login-link:focus-visible,
.app-header__menu-button:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
}

.app-nav__link--active {
    background: var(--color-surface-raised);
    color: var(--color-text);
    box-shadow: inset 0 -0.125rem 0 var(--color-accent);
}

.app-header__login-link {
    margin-left: auto;
}

.app-header__user {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    min-width: 0;
    margin-left: auto;
}

.app-header__username {
    overflow: hidden;
    max-width: 12rem;
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

@media (max-width: 40rem) {
    .app-header__bar {
        justify-content: space-between;
        column-gap: 0.75rem;
        padding: 0.625rem 1rem;
    }

    .brand__title {
        font-size: 1rem;
    }

    .app-header__menu-button {
        display: inline-flex;
        align-items: center;
        min-height: 2.5rem;
        padding: 0 0.75rem;
        border: 1px solid var(--color-border-strong);
        border-radius: var(--radius-medium);
        background: transparent;
        color: var(--color-text);
        font: inherit;
        font-size: 0.9375rem;
        font-weight: 600;
        cursor: pointer;
    }

    .app-header__menu {
        display: none;
        flex-basis: 100%;
        flex-direction: column;
        align-items: stretch;
    }

    .app-header__menu--open {
        display: flex;
    }

    .app-nav {
        flex-direction: column;
    }

    .app-nav__link {
        min-height: 2.75rem;
    }

    .app-header__user {
        justify-content: space-between;
        margin-left: 0;
        padding-top: 0.75rem;
        border-top: 1px solid var(--color-border);
    }
}

@media (prefers-reduced-motion: reduce) {
    .app-nav__link,
    .app-header__login-link {
        transition: none;
    }
}
</style>
