import type { User, UserBody } from "../types/api";
import { ApiError, requestJson } from "./apiClient";

const PROFILE_ENDPOINT = "/api/auth/me";

function toUser(body: UserBody): User {
    return {
        id: body.id,
        username: body.username,
        timeZone: body.time_zone,
    };
}

function isNotAuthenticated(error: unknown): boolean {
    return error instanceof ApiError && error.code === "not_authenticated";
}

export async function fetchCurrentUser(): Promise<User | null> {
    try {
        const body = await requestJson<UserBody>(PROFILE_ENDPOINT, { isSessionProbe: true });

        return toUser(body);
    } catch (error) {
        if (isNotAuthenticated(error)) {
            return null;
        }

        throw error;
    }
}

export async function logIn(username: string, password: string): Promise<User> {
    const body = await requestJson<UserBody>("/api/auth/login", {
        method: "POST",
        body: { username, password },
    });

    return toUser(body);
}

export async function register(username: string, password: string, timeZone: string | null): Promise<User> {
    const requestBody: Record<string, string> = { username, password };

    // Без пояса сервер подставит свой, поэтому пустое значение не отправляется
    if (timeZone !== null) {
        requestBody.time_zone = timeZone;
    }

    const body = await requestJson<UserBody>("/api/auth/register", {
        method: "POST",
        body: requestBody,
    });

    return toUser(body);
}

export async function logOut(): Promise<void> {
    try {
        await requestJson<undefined>("/api/auth/logout", { method: "POST", isSessionProbe: true });
    } catch (error) {
        // Сессия уже закончилась сама: выход всё равно состоялся
        if (!isNotAuthenticated(error)) {
            throw error;
        }
    }
}

export async function updateTimeZone(timeZone: string): Promise<User> {
    const body = await requestJson<UserBody>(PROFILE_ENDPOINT, {
        method: "PATCH",
        body: { time_zone: timeZone },
    });

    return toUser(body);
}
