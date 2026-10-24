export type ServiceState = "checking" | "online" | "offline" | "unknown";

export interface ServiceDetail {
    label: string;
    value: string;
    isMissing: boolean;
}

export interface DatabaseHealthBody {
    status: string;
    version: string | null;
    query_time_ms: number | null;
}

export interface HealthResponseBody {
    status: string;
    python_version: string;
    django_version: string;
    database: DatabaseHealthBody;
}

export interface DatabaseHealth {
    status: string;
    version: string | null;
    queryTimeMs: number | null;
}

export interface ApiHealth {
    status: string;
    pythonVersion: string;
    djangoVersion: string;
    database: DatabaseHealth;
}

export interface HealthCheckResult {
    health: ApiHealth | null;
    httpStatus: number | null;
    responseTimeMs: number | null;
}
