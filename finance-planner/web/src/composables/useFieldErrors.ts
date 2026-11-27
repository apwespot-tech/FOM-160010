import { ref } from "vue";

import type { FieldErrors } from "../types/api";
import { buildErrorId, buildHintId } from "../utils/formIds";

export type InputDescription = Record<string, string | undefined>;

export interface InputDescriptionOptions {
    hasHint?: boolean;
    isRequired?: boolean;
}

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

    function readDescriptionId(inputId: string, fieldName: string, hasHint: boolean): string | undefined {
        if (fieldName in fieldErrors.value) {
            return buildErrorId(inputId);
        }

        if (hasHint) {
            return buildHintId(inputId);
        }

        return undefined;
    }

    // Связывает поле с ошибкой или подсказкой под ним, чтобы экранный диктор прочитал их вместе с полем
    function describeInput(inputId: string, fieldName: string, options: InputDescriptionOptions = {}): InputDescription {
        const hasError = fieldName in fieldErrors.value;

        return {
            "aria-describedby": readDescriptionId(inputId, fieldName, options.hasHint === true),
            "aria-invalid": hasError ? "true" : undefined,
            "aria-required": options.isRequired === true ? "true" : undefined,
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
