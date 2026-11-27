import { ref } from "vue";

import type { FieldErrors } from "../types/api";

export type InputDescription = Record<string, string | undefined>;

export function useFieldErrors() {
    const fieldErrors = ref<FieldErrors>({});

    function setFieldError(fieldName: string, message: string | null): void {
        const nextErrors = { ...fieldErrors.value };

        if (message === null) {
            delete nextErrors[fieldName];
        } else {
            nextErrors[fieldName] = message;
        }

        fieldErrors.value = nextErrors;
    }

    function replaceFieldErrors(errors: FieldErrors): void {
        fieldErrors.value = { ...errors };
    }

    function clearFieldErrors(): void {
        fieldErrors.value = {};
    }

    function hasFieldErrors(): boolean {
        return Object.keys(fieldErrors.value).length > 0;
    }

    // Связывает поле с текстом ошибки под ним, чтобы экранный диктор прочитал её вместе с полем
    function describeInput(inputId: string, fieldName: string): InputDescription {
        const hasError = fieldName in fieldErrors.value;

        return {
            "aria-describedby": hasError ? `${inputId}-error` : undefined,
            "aria-invalid": hasError ? "true" : undefined,
        };
    }

    return {
        clearFieldErrors,
        describeInput,
        fieldErrors,
        hasFieldErrors,
        replaceFieldErrors,
        setFieldError,
    };
}
