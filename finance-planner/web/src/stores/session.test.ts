import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../services/authApi";
import { useSessionStore } from "./session";

vi.mock("../services/authApi");

const USER = { id: 7, username: "anna", timeZone: "Asia/Yekaterinburg" };

beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(authApi.fetchCurrentUser).mockReset();
});

describe("loadCurrentUser", () => {
    it("asks the API once for simultaneous checks", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(USER);
        const session = useSessionStore();

        await Promise.all([session.loadCurrentUser(), session.loadCurrentUser()]);

        expect(authApi.fetchCurrentUser).toHaveBeenCalledTimes(1);
        expect(session.currentUser).toEqual(USER);
        expect(session.isAuthenticated).toBe(true);
    });

    it("does not ask again after an answer", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(null);
        const session = useSessionStore();

        await session.loadCurrentUser();
        await session.loadCurrentUser();

        expect(authApi.fetchCurrentUser).toHaveBeenCalledTimes(1);
        expect(session.isAuthenticated).toBe(false);
    });

    it("remembers a failed check and asks again next time", async () => {
        vi.mocked(authApi.fetchCurrentUser).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(USER);
        const session = useSessionStore();

        await session.loadCurrentUser();

        expect(session.hasLoadFailed).toBe(true);

        await session.loadCurrentUser();

        expect(session.hasLoadFailed).toBe(false);
        expect(session.currentUser).toEqual(USER);
        expect(authApi.fetchCurrentUser).toHaveBeenCalledTimes(2);
    });
});
