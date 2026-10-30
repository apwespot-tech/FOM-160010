import type { ApiHealth, HealthCheckResult, HealthResponseBody } from "../types/health";

const HEALTH_ENDPOINT = "/api/health";
const REQUEST_TIMEOUT_MS = 15000;

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function isHealthResponseBody(value: unknown): value is HealthResponseBody {
    if (!isRecord(value) || !isRecord(value.database)) {
        return false;
    }

    const hasServiceFields = typeof value.status === "string" && typeof value.django_version === "string";
    const hasDatabaseStatus = typeof value.database.status === "string";

    return hasServiceFields && hasDatabaseStatus;
}

function toApiHealth(body: HealthResponseBody): ApiHealth {
    return {
        status: body.status,
        pythonVersion: body.python_version,
        djangoVersion: body.django_version,
        database: {
            status: body.database.status,
            version: body.database.version,
            queryTimeMs: body.database.query_time_ms,
        },
    };
}

async function readHealthBody(response: Response): Promise<HealthResponseBody | null> {
    const contentType = response.headers.get("content-type") ?? "";

    if (!contentType.includes("application/json")) {
        return null;
    }

    let body: unknown;

    try {
        body = await response.json();
    } catch {
        return null;
    }

    if (!isHealthResponseBody(body)) {
        return null;
    }

    return body;
}

export async function requestHealth(): Promise<HealthCheckResult> {
    const startedAt = performance.now();
    let response: Response;

    try {
        response = await fetch(HEALTH_ENDPOINT, {
            headers: { Accept: "application/json" },
            signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
    } catch {
        return { health: null, httpStatus: null, responseTimeMs: null };
    }

    const body = await readHealthBody(response);
    const responseTimeMs = Math.round(performance.now() - startedAt);

    if (body === null) {
        return { health: null, httpStatus: response.status, responseTimeMs };
    }

    return { health: toApiHealth(body), httpStatus: response.status, responseTimeMs };
}
