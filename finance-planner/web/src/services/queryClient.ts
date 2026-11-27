import { QueryClient } from "@tanstack/vue-query";

import { ApiError } from "./apiClient";

const MAX_QUERY_RETRIES = 1;
const QUERY_STALE_TIME_MS = 30000;
const FIRST_SERVER_ERROR_STATUS = 500;

function shouldRetryQuery(failureCount: number, error: Error): boolean {
    // Ответ 4xx повтор не исправит, повторяется только сбой сети или сервера
    const isClientError = error instanceof ApiError && error.status !== null && error.status < FIRST_SERVER_ERROR_STATUS;

    if (isClientError) {
        return false;
    }

    return failureCount < MAX_QUERY_RETRIES;
}

export function createQueryClient(): QueryClient {
    return new QueryClient({
        defaultOptions: {
            queries: {
                retry: shouldRetryQuery,
                refetchOnWindowFocus: false,
                staleTime: QUERY_STALE_TIME_MS,
            },
            mutations: {
                retry: false,
            },
        },
    });
}
