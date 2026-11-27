import type { ApiErrorBody, FieldErrors, ValidationErrorItem } from "../types/api";
import { readCsrfToken } from "./csrf";

const CSRF_ENDPOINT = "/api/auth/csrf";
const CSRF_HEADER_NAME = "X-CSRFToken";
const REQUEST_TIMEOUT_MS = 15000;
const NO_CONTENT_STATUS = 204;
const FORBIDDEN_STATUS = 403;
const UNSAFE_METHODS: ReadonlySet<HttpMethod> = new Set(["POST", "PATCH", "DELETE"]);
// Свои тексты по-русски приходят только у этих видов ошибок, остальные Pydantic пишет по-английски (docs/api.md, раздел 2)
const PLANNER_ERROR_TYPES: ReadonlySet<string> = new Set(["planner_format", "planner_rule"]);

const NETWORK_FAILURE_TEXT = "Нет связи с сервером. Проверьте подключение и повторите попытку";
const UNEXPECTED_RESPONSE_TEXT = "Сервер ответил неожиданно. Повторите попытку позже";
const FORM_ERRORS_TEXT = "Проверьте поля формы";
const MISSING_FIELD_TEXT = "Заполните поле";
const INVALID_FIELD_TEXT = "Проверьте значение поля";

export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";
export type QueryValue = string | number | null | undefined;

export interface RequestOptions {
    method?: HttpMethod;
    body?: unknown;
    query?: Record<string, QueryValue>;
    // Проверка сессии сама разбирает ответ 401 и не должна уводить на страницу входа
    isSessionProbe?: boolean;
}

interface RequestResult {
    response: Response;
    responseBody: unknown;
}

export class ApiError extends Error {
    readonly status: number | null;
    readonly code: string;
    readonly fieldErrors: FieldErrors;

    constructor(status: number | null, code: string, message: string, fieldErrors: FieldErrors = {}) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
        this.fieldErrors = fieldErrors;
    }
}

let unauthenticatedHandler: (() => void) | null = null;
let pendingCsrfRequest: Promise<void> | null = null;

export function setUnauthenticatedHandler(handler: () => void): void {
    unauthenticatedHandler = handler;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
    if (!isRecord(value)) {
        return false;
    }

    const hasDetail = typeof value.detail === "string" || Array.isArray(value.detail);

    return typeof value.code === "string" && hasDetail;
}

export function describeFieldError(item: ValidationErrorItem): string {
    if (PLANNER_ERROR_TYPES.has(item.type)) {
        return item.msg;
    }

    if (item.type === "missing") {
        return MISSING_FIELD_TEXT;
    }

    return INVALID_FIELD_TEXT;
}

export function collectFieldErrors(items: ValidationErrorItem[]): FieldErrors {
    const fieldErrors: FieldErrors = {};

    for (const item of items) {
        const fieldName = String(item.loc.at(-1));

        if (!(fieldName in fieldErrors)) {
            fieldErrors[fieldName] = describeFieldError(item);
        }
    }

    return fieldErrors;
}

export function buildUrl(path: string, query?: Record<string, QueryValue>): string {
    const parameters = new URLSearchParams();

    for (const [name, value] of Object.entries(query ?? {})) {
        const hasValue = value !== null && value !== undefined && value !== "";

        if (hasValue) {
            parameters.append(name, String(value));
        }
    }

    const queryText = parameters.toString();

    if (queryText === "") {
        return path;
    }

    return `${path}?${queryText}`;
}

function toApiError(status: number, body: unknown): ApiError {
    if (!isApiErrorBody(body)) {
        return new ApiError(status, "unexpected_response", UNEXPECTED_RESPONSE_TEXT);
    }

    if (Array.isArray(body.detail)) {
        return new ApiError(status, body.code, FORM_ERRORS_TEXT, collectFieldErrors(body.detail));
    }

    return new ApiError(status, body.code, body.detail);
}

async function readJsonBody(response: Response): Promise<unknown> {
    const contentType = response.headers.get("content-type") ?? "";

    if (!contentType.includes("application/json")) {
        return undefined;
    }

    try {
        return await response.json();
    } catch {
        // Обрезанное или испорченное тело разбирается дальше как неожиданный ответ
        return undefined;
    }
}

async function sendRequest(method: HttpMethod, url: string, headers: Record<string, string>, body: unknown): Promise<Response> {
    const requestBody = body === undefined ? undefined : JSON.stringify(body);

    try {
        return await fetch(url, {
            method,
            headers,
            body: requestBody,
            credentials: "same-origin",
            signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
    } catch {
        throw new ApiError(null, "network_failed", NETWORK_FAILURE_TEXT);
    }
}

async function requestCsrfCookie(): Promise<void> {
    const response = await sendRequest("GET", CSRF_ENDPOINT, { Accept: "application/json" }, undefined);

    if (!response.ok) {
        throw new ApiError(response.status, "unexpected_response", UNEXPECTED_RESPONSE_TEXT);
    }
}

export async function refreshCsrfToken(): Promise<void> {
    // Параллельные запросы ждут одну выдачу токена, а не просят его каждый сам
    if (pendingCsrfRequest === null) {
        pendingCsrfRequest = requestCsrfCookie().finally(() => {
            pendingCsrfRequest = null;
        });
    }

    await pendingCsrfRequest;
}

async function buildHeaders(method: HttpMethod, hasBody: boolean): Promise<Record<string, string>> {
    const headers: Record<string, string> = { Accept: "application/json" };

    if (hasBody) {
        headers["Content-Type"] = "application/json";
    }

    if (!UNSAFE_METHODS.has(method)) {
        return headers;
    }

    if (readCsrfToken() === null) {
        await refreshCsrfToken();
    }

    // После входа Django меняет токен, поэтому кука читается перед каждым изменяющим запросом
    headers[CSRF_HEADER_NAME] = readCsrfToken() ?? "";

    return headers;
}

async function performRequest(method: HttpMethod, url: string, body: unknown): Promise<RequestResult> {
    const headers = await buildHeaders(method, body !== undefined);
    const response = await sendRequest(method, url, headers, body);
    const responseBody = await readJsonBody(response);

    return { response, responseBody };
}

function isCsrfFailure(response: Response, responseBody: unknown): boolean {
    return response.status === FORBIDDEN_STATUS && isApiErrorBody(responseBody) && responseBody.code === "csrf_failed";
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const method = options.method ?? "GET";
    const url = buildUrl(path, options.query);
    let { response, responseBody } = await performRequest(method, url, options.body);

    if (isCsrfFailure(response, responseBody)) {
        // Токен устарел или пропал: получаем новый и повторяем запрос один раз
        await refreshCsrfToken();
        ({ response, responseBody } = await performRequest(method, url, options.body));
    }

    if (response.ok) {
        const isBodyMissing = responseBody === undefined && response.status !== NO_CONTENT_STATUS;

        if (isBodyMissing) {
            throw new ApiError(response.status, "unexpected_response", UNEXPECTED_RESPONSE_TEXT);
        }

        return responseBody as T;
    }

    const error = toApiError(response.status, responseBody);
    const shouldLeaveSession = error.code === "not_authenticated" && options.isSessionProbe !== true;

    if (shouldLeaveSession) {
        unauthenticatedHandler?.();
    }

    throw error;
}

export function describeError(error: unknown): string {
    if (error instanceof ApiError) {
        return error.message;
    }

    return UNEXPECTED_RESPONSE_TEXT;
}
