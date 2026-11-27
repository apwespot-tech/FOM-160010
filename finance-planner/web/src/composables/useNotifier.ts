import { useToast } from "primevue/usetoast";

import { describeError } from "../services/apiClient";

const NOTIFICATION_LIFE_MS = 6000;
const ERROR_SUMMARY = "Не получилось";

export function useNotifier() {
    const toast = useToast();

    function notifySuccess(summary: string): void {
        toast.add({ severity: "success", summary, life: NOTIFICATION_LIFE_MS });
    }

    function notifyError(error: unknown): void {
        toast.add({ severity: "error", summary: ERROR_SUMMARY, detail: describeError(error), life: NOTIFICATION_LIFE_MS });
    }

    return {
        notifyError,
        notifySuccess,
    };
}
