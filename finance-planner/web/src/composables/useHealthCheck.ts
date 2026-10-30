import { computed, ref } from "vue";

import { requestHealth } from "../services/healthApi";
import type { HealthCheckResult, ServiceState } from "../types/health";

export function useHealthCheck() {
    const isChecking = ref(false);
    const lastResult = ref<HealthCheckResult | null>(null);
    const checkedAt = ref<Date | null>(null);

    const apiState = computed<ServiceState>(() => {
        if (isChecking.value || lastResult.value === null) {
            return "checking";
        }

        if (lastResult.value.health === null) {
            return "offline";
        }

        return "online";
    });

    const databaseState = computed<ServiceState>(() => {
        if (isChecking.value || lastResult.value === null) {
            return "checking";
        }

        const health = lastResult.value.health;

        if (health === null) {
            return "unknown";
        }

        if (health.database.status === "ok") {
            return "online";
        }

        return "offline";
    });

    async function checkNow(): Promise<void> {
        if (isChecking.value) {
            return;
        }

        isChecking.value = true;

        try {
            lastResult.value = await requestHealth();
            checkedAt.value = new Date();
        } finally {
            isChecking.value = false;
        }
    }

    return {
        apiState,
        checkNow,
        checkedAt,
        databaseState,
        isChecking,
        lastResult,
    };
}
