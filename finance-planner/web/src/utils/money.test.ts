import { describe, expect, it } from "vitest";

import {
    COLUMN_GROUPING_DIGITS,
    formatMoney,
    groupThousands,
    isZeroAmount,
    MINUS_SIGN,
    NON_BREAKING_SPACE,
    normalizeAmountInput,
} from "./money";

function spaced(text: string): string {
    return text.replaceAll("_", NON_BREAKING_SPACE);
}

describe("formatMoney", () => {
    it.each([
        ["1250.50", "1250.50_₽"],
        ["15000.00", "15_000.00_₽"],
        ["1234567.89", "1_234_567.89_₽"],
        ["0.00", "0.00_₽"],
        ["99.9", "99.90_₽"],
        ["7", "7.00_₽"],
    ])("formats %s with a dot, two decimals and the currency sign after the number", (amount, expected) => {
        expect(formatMoney(amount, "RUB")).toBe(spaced(expected));
    });

    it("writes negative amounts with the minus sign instead of a hyphen", () => {
        expect(formatMoney("-15000.00", "RUB")).toBe(`${MINUS_SIGN}${spaced("15_000.00_₽")}`);
    });

    it("does not put a minus before zero", () => {
        expect(formatMoney("-0.00", "RUB")).toBe(spaced("0.00_₽"));
    });

    it("groups four digits in table columns", () => {
        expect(formatMoney("1250.50", "RUB", { groupingDigits: COLUMN_GROUPING_DIGITS })).toBe(spaced("1_250.50_₽"));
    });

    it("shows the code of a currency without a sign", () => {
        expect(formatMoney("10.00", "USD")).toBe(spaced("10.00_USD"));
    });

    it("returns text that is not an amount unchanged", () => {
        expect(formatMoney("нет данных", "RUB")).toBe("нет данных");
    });
});

describe("groupThousands", () => {
    it.each([
        ["1", "1"],
        ["1234", "1234"],
        ["12345", "12_345"],
        ["123456", "123_456"],
        ["1234567", "1_234_567"],
    ])("groups %s", (digits, expected) => {
        expect(groupThousands(digits)).toBe(spaced(expected));
    });
});

describe("normalizeAmountInput", () => {
    it.each([
        ["1250.5", "1250.50"],
        ["1250,5", "1250.50"],
        [" 15 000 ", "15000.00"],
        [spaced("15_000,75"), "15000.75"],
        ["7", "7.00"],
    ])("turns %s into %s", (text, expected) => {
        expect(normalizeAmountInput(text)).toBe(expected);
    });

    it.each(["", "abc", "1e3", "+5", "12.345", "1.2.3", "1234567890123", "-5"])("rejects %s", (text) => {
        expect(normalizeAmountInput(text)).toBeNull();
    });

    it("accepts a minus only where it is allowed", () => {
        expect(normalizeAmountInput(`${MINUS_SIGN}250`, true)).toBe("-250.00");
        expect(normalizeAmountInput("-250,5", true)).toBe("-250.50");
    });

    it("drops leading zeros so that a row of zeros reads as zero", () => {
        expect(normalizeAmountInput("00")).toBe("0.00");
        expect(normalizeAmountInput("007,5")).toBe("7.50");
    });

    it("does not make a negative zero", () => {
        expect(normalizeAmountInput("-0", true)).toBe("0.00");
        expect(normalizeAmountInput(`${MINUS_SIGN}0.00`, true)).toBe("0.00");
    });
});

describe("isZeroAmount", () => {
    it.each(["0.00", "0", "-0.00", "000.0"])("treats %s as zero", (amount) => {
        expect(isZeroAmount(amount)).toBe(true);
    });

    it.each(["0.01", "10.00", "-5.00"])("treats %s as a real amount", (amount) => {
        expect(isZeroAmount(amount)).toBe(false);
    });
});
