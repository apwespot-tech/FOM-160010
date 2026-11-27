import { createRouter, createWebHistory } from "vue-router";
import type { RouteLocationNormalized, RouteLocationRaw } from "vue-router";

import { useSessionStore } from "../stores/session";
import { readReturnPath } from "../utils/returnPath";

const APPLICATION_TITLE = "Финансовый планер";

declare module "vue-router" {
    interface RouteMeta {
        title: string;
        isPublic?: boolean;
        isGuestOnly?: boolean;
    }
}

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: "/login",
            name: "login",
            component: () => import("../views/LoginView.vue"),
            meta: { title: "Вход", isPublic: true, isGuestOnly: true },
        },
        {
            path: "/register",
            name: "register",
            component: () => import("../views/RegisterView.vue"),
            meta: { title: "Регистрация", isPublic: true, isGuestOnly: true },
        },
        {
            path: "/status",
            name: "status",
            component: () => import("../views/StatusView.vue"),
            meta: { title: "Состояние сервисов", isPublic: true },
        },
        {
            path: "/",
            name: "dashboard",
            component: () => import("../views/DashboardView.vue"),
            meta: { title: "Сводка" },
        },
        {
            path: "/accounts",
            name: "accounts",
            component: () => import("../views/AccountsView.vue"),
            meta: { title: "Счета" },
        },
        {
            path: "/operations",
            name: "operations",
            component: () => import("../views/OperationsView.vue"),
            meta: { title: "Операции" },
        },
        {
            path: "/budgets",
            name: "budgets",
            component: () => import("../views/BudgetsView.vue"),
            meta: { title: "Бюджеты" },
        },
        {
            path: "/goals",
            name: "goals",
            component: () => import("../views/GoalsView.vue"),
            meta: { title: "Цели" },
        },
        {
            path: "/recurring",
            name: "recurring",
            component: () => import("../views/RecurringView.vue"),
            meta: { title: "Периодические операции" },
        },
        {
            path: "/:unknownPath(.*)*",
            redirect: { name: "dashboard" },
            meta: { title: APPLICATION_TITLE },
        },
    ],
});

type GuardedRoute = Pick<RouteLocationNormalized, "fullPath" | "meta" | "query">;

export async function checkAccess(to: GuardedRoute): Promise<RouteLocationRaw | true> {
    if (to.meta.isPublic && !to.meta.isGuestOnly) {
        return true;
    }

    const session = useSessionStore();

    await session.loadCurrentUser();

    // Исходная страница уходит в адрес проверки сервисов, чтобы к ней можно было вернуться, когда API ответит
    if (session.hasLoadFailed && !to.meta.isPublic) {
        return { name: "status", query: { next: to.fullPath } };
    }

    if (!to.meta.isPublic && !session.isAuthenticated) {
        return { name: "login", query: { next: to.fullPath } };
    }

    if (to.meta.isGuestOnly && session.isAuthenticated) {
        return readReturnPath(to.query.next);
    }

    return true;
}

router.beforeEach(checkAccess);

router.afterEach((to) => {
    document.title = `${to.meta.title} · ${APPLICATION_TITLE}`;
});
