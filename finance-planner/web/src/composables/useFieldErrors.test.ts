import { describe, expect, it } from "vitest";

import { useFieldErrors } from "./useFieldErrors";

describe("describeInput", () => {
    it("points to the hint while the field has no error", () => {
        const { describeInput } = useFieldErrors();

        expect(describeInput("register-password", "password", { hasHint: true, isRequired: true })).toEqual({
            "aria-describedby": "register-password-hint",
            "aria-invalid": undefined,
            "aria-required": "true",
        });
    });

    it("points to the error and marks the field invalid", () => {
        const { describeInput, setFieldError } = useFieldErrors();

        setFieldError("amount", "Введите сумму");

        expect(describeInput("operation-amount", "amount", { hasHint: true })).toEqual({
            "aria-describedby": "operation-amount-error",
            "aria-invalid": "true",
            "aria-required": undefined,
        });
    });

    it("leaves a field without a hint and an error undescribed", () => {
        const { describeInput } = useFieldErrors();

        expect(describeInput("operation-note", "note")["aria-describedby"]).toBeUndefined();
    });
});
