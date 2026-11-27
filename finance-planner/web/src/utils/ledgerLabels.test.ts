import { describe, expect, it } from "vitest";

import { formatOperationAmount } from "./ledgerLabels";
import { MINUS_SIGN, NON_BREAKING_SPACE } from "./money";

describe("formatOperationAmount", () => {
    it("puts a minus before expenses and transfer debits", () => {
        expect(formatOperationAmount("expense", "1250.50", "RUB")).toBe(`${MINUS_SIGN}1${NON_BREAKING_SPACE}250.50${NON_BREAKING_SPACE}₽`);
        expect(formatOperationAmount("transfer_out", "300.00", "RUB")).toBe(`${MINUS_SIGN}300.00${NON_BREAKING_SPACE}₽`);
    });

    it("puts a plus before incomes and transfer credits", () => {
        expect(formatOperationAmount("income", "35000.00", "RUB")).toBe(`+35${NON_BREAKING_SPACE}000.00${NON_BREAKING_SPACE}₽`);
        expect(formatOperationAmount("transfer_in", "300.00", "RUB")).toBe(`+300.00${NON_BREAKING_SPACE}₽`);
    });
});
