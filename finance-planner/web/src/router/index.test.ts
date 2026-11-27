import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { LocationQuery, RouteMeta } from "vue-router";

import * as authApi from "../services/authApi";
import { checkAccess } from "./index";

vi.mock("../services/authApi");

const USER = { id: 7, username: "anna", timeZone: "Asia/Yekaterinburg" };
const PRIVATE_META: RouteMeta = { title: "Счета" };
const GUEST_META: RouteMeta = { title: "Вход", isPublic: true, isGuestOnly: true };
const PUBLIC_META: RouteMeta = { title: "Состояние сервисов", isPublic: true };

function buildRoute(fullPath: string, meta: RouteMeta, nextValue?: string) {
    const query: LocationQuery = nextValue === undefined ? {} : { next: nextValue };

    return { fullPath, meta, query };
}

beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(authApi.fetchCurrentUser).mockReset();
});

describe("checkAccess", () => {
    it("opens the status page without asking about the session", async () => {
        await expect(checkAccess(buildRoute("/status", PUBLIC_META))).resolves.toBe(true);
        expect(authApi.fetchCurrentUser).not.toHaveBeenCalled();
    });

    it("lets a signed-in user open a private page", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(USER);

        await expect(checkAccess(buildRoute("/accounts", PRIVATE_META))).resolves.toBe(true);
    });

    it("sends a guest to the login page and keeps the requested page", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(null);

        const target = await checkAccess(buildRoute("/operations?page=2", PRIVATE_META));

        expect(target).toEqual({ name: "login", query: { next: "/operations?page=2" } });
    });

    it("sends to the status page when the API does not answer and keeps the requested page", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockRejectedValue(new Error("offline"));

        const target = await checkAccess(buildRoute("/accounts", PRIVATE_META));

        expect(target).toEqual({ name: "status", query: { next: "/accounts" } });
    });

    it("returns a signed-in user from the login page to the requested page", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(USER);

        await expect(checkAccess(buildRoute("/login?next=/operations", GUEST_META, "/operations"))).resolves.toBe("/operations");
    });

    it("does not follow a return path to another site", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(USER);

        await expect(checkAccess(buildRoute("/login?next=//example.com", GUEST_META, "//example.com"))).resolves.toBe("/");
    });

    it("lets a guest open the login page", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(null);

        await expect(checkAccess(buildRoute("/login", GUEST_META))).resolves.toBe(true);
    });
});
