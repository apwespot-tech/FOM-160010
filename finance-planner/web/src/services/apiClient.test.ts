import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, buildUrl, collectFieldErrors, requestJson, setUnauthenticatedHandler } from "./apiClient";
import { CSRF_COOKIE_NAME } from "./csrf";
import { NON_BREAKING_SPACE } from "../utils/money";

function createJsonResponse(status: number, body: unknown): Response {
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function readHeader(init: RequestInit | undefined, name: string): string | null {
    return new Headers(init?.headers).get(name);
}

afterEach(() => {
    vi.unstubAllGlobals();
    setUnauthenticatedHandler(null);
    document.cookie = `${CSRF_COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
});

describe("collectFieldErrors", () => {
    it("keeps planner messages and replaces the English ones", () => {
        const fieldErrors = collectFieldErrors([
            { type: "planner_rule", loc: ["body", "payload", "account_id"], msg: "Счёт в архиве" },
            { type: "missing", loc: ["body", "payload", "amount"], msg: "Field required" },
            { type: "string_too_long", loc: ["body", "payload", "note"], msg: "String should have at most 255 characters" },
        ]);

        expect(fieldErrors).toEqual({
            account_id: "Счёт в архиве",
            amount: "Заполните поле",
            note: "Проверьте значение поля",
        });
    });

    it("shows the first error of a field", () => {
        const fieldErrors = collectFieldErrors([
            { type: "planner_format", loc: ["body", "payload", "amount"], msg: "Сумма записывается строкой вида 1250.50" },
            { type: "greater_than", loc: ["body", "payload", "amount"], msg: "Input should be greater than 0" },
        ]);

        expect(fieldErrors).toEqual({ amount: "Сумма записывается строкой вида 1250.50" });
    });
});

describe("buildUrl", () => {
    it("skips empty query values", () => {
        expect(buildUrl("/api/operations", { page: 2, kind: "", account_id: null, category_id: undefined })).toBe("/api/operations?page=2");
    });

    it("returns the path without a query", () => {
        expect(buildUrl("/api/accounts")).toBe("/api/accounts");
    });
});

describe("requestJson", () => {
    it("sends the CSRF token with an unsafe request", async () => {
        document.cookie = `${CSRF_COOKIE_NAME}=first-token`;
        const fetchMock = vi.fn().mockResolvedValue(createJsonResponse(201, { id: 1 }));
        vi.stubGlobal("fetch", fetchMock);

        const body = await requestJson<{ id: number }>("/api/accounts", { method: "POST", body: { name: "Карта" } });
        const [, init] = fetchMock.mock.calls[0];

        expect(body).toEqual({ id: 1 });
        expect(readHeader(init, "X-CSRFToken")).toBe("first-token");
        expect(init.credentials).toBe("same-origin");
    });

    it("asks for a CSRF token first when the cookie is missing", async () => {
        const fetchMock = vi.fn()
            .mockImplementationOnce(async () => {
                document.cookie = `${CSRF_COOKIE_NAME}=issued-token`;

                return new Response(null, { status: 204 });
            })
            .mockResolvedValueOnce(createJsonResponse(201, { id: 3 }));

        vi.stubGlobal("fetch", fetchMock);
        await requestJson("/api/accounts", { method: "POST", body: { name: "Наличные" } });
        const [, postInit] = fetchMock.mock.calls[1];

        expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/csrf");
        expect(readHeader(postInit, "X-CSRFToken")).toBe("issued-token");
    });

    it("sends a safe request without the CSRF header", async () => {
        document.cookie = `${CSRF_COOKIE_NAME}=some-token`;
        const fetchMock = vi.fn().mockResolvedValue(createJsonResponse(200, { items: [] }));
        vi.stubGlobal("fetch", fetchMock);

        await requestJson("/api/accounts");
        const [, init] = fetchMock.mock.calls[0];

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(readHeader(init, "X-CSRFToken")).toBeNull();
    });

    it("gets a new token and repeats the request once after csrf_failed", async () => {
        document.cookie = `${CSRF_COOKIE_NAME}=stale-token`;

        const fetchMock = vi.fn()
            .mockResolvedValueOnce(createJsonResponse(403, { code: "csrf_failed", detail: "Нет токена CSRF или он устарел" }))
            .mockImplementationOnce(async () => {
                document.cookie = `${CSRF_COOKIE_NAME}=fresh-token`;

                return new Response(null, { status: 204 });
            })
            .mockResolvedValueOnce(new Response(null, { status: 204 }));

        vi.stubGlobal("fetch", fetchMock);
        await requestJson<undefined>("/api/auth/logout", { method: "POST" });
        const [, retriedInit] = fetchMock.mock.calls[2];

        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(fetchMock.mock.calls[1][0]).toBe("/api/auth/csrf");
        expect(readHeader(retriedInit, "X-CSRFToken")).toBe("fresh-token");
    });

    it("gives up after a second csrf_failed instead of repeating again", async () => {
        document.cookie = `${CSRF_COOKIE_NAME}=stale-token`;
        const csrfFailure = { code: "csrf_failed", detail: "Нет токена CSRF или он устарел" };

        const fetchMock = vi.fn()
            .mockResolvedValueOnce(createJsonResponse(403, csrfFailure))
            .mockResolvedValueOnce(new Response(null, { status: 204 }))
            .mockResolvedValueOnce(createJsonResponse(403, csrfFailure));

        vi.stubGlobal("fetch", fetchMock);
        const request = requestJson("/api/auth/logout", { method: "POST" });

        await expect(request).rejects.toMatchObject({ status: 403, code: "csrf_failed" });
        expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    it("turns a validation error into field errors", async () => {
        const errorBody = {
            code: "validation_error",
            detail: [{ type: "planner_rule", loc: ["body", "payload", "date"], msg: "Дата не может быть позже сегодняшнего дня" }],
        };

        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(createJsonResponse(422, errorBody)));
        const request = requestJson("/api/operations", { method: "GET" });

        await expect(request).rejects.toMatchObject({
            status: 422,
            code: "validation_error",
            fieldErrors: { date: "Дата не может быть позже сегодняшнего дня" },
        });
    });

    it("reports a missing session to the handler", async () => {
        const unauthenticatedHandler = vi.fn();
        setUnauthenticatedHandler(unauthenticatedHandler);
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(createJsonResponse(401, { code: "not_authenticated", detail: "Требуется вход" })));

        await expect(requestJson("/api/accounts")).rejects.toBeInstanceOf(ApiError);
        expect(unauthenticatedHandler).toHaveBeenCalledTimes(1);
    });

    it("leaves a session probe to its caller", async () => {
        const unauthenticatedHandler = vi.fn();
        setUnauthenticatedHandler(unauthenticatedHandler);
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(createJsonResponse(401, { code: "not_authenticated", detail: "Требуется вход" })));

        await expect(requestJson("/api/auth/me", { isSessionProbe: true })).rejects.toMatchObject({ code: "not_authenticated" });
        expect(unauthenticatedHandler).not.toHaveBeenCalled();
    });

    it("treats a response that is not JSON as a general failure", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>Bad gateway</html>", { status: 502 })));

        await expect(requestJson("/api/accounts")).rejects.toMatchObject({ status: 502, code: "unexpected_response" });
    });

    it("tells a timeout apart from a lost connection", async () => {
        const timeoutError = new DOMException("The operation timed out", "TimeoutError");
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue(timeoutError));

        const expectedMessage = `Сервер не ответил за 15${NON_BREAKING_SPACE}секунд. Повторите попытку позже`;

        await expect(requestJson("/api/accounts")).rejects.toMatchObject({ status: null, code: "timeout", message: expectedMessage });
    });

    it("treats a lost connection as a network failure", async () => {
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

        await expect(requestJson("/api/accounts")).rejects.toMatchObject({ status: null, code: "network_failed" });
    });
});
