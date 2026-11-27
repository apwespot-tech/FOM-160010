import { describe, expect, it } from "vitest";

import {
    checkNewPassword,
    checkNewUsername,
    checkPasswordConfirmation,
    checkRequired,
    PASSWORDS_DIFFER_TEXT,
    REQUIRED_FIELD_TEXT,
} from "./formChecks";
import { listTimeZones } from "./timeZones";

describe("checkRequired", () => {
    it("rejects an empty or blank value", () => {
        expect(checkRequired("")).toBe(REQUIRED_FIELD_TEXT);
        expect(checkRequired("   ")).toBe(REQUIRED_FIELD_TEXT);
    });

    it("accepts a filled value", () => {
        expect(checkRequired("anna")).toBeNull();
    });
});

describe("checkNewUsername", () => {
    it.each(["anna", "анна", "anna.k+1@home", " bor ", "b".repeat(150)])("accepts %s", (username) => {
        expect(checkNewUsername(username)).toBeNull();
    });

    it.each([
        ["", REQUIRED_FIELD_TEXT],
        ["ab", "Логин не короче 3 знаков"],
        ["b".repeat(151), "Логин не длиннее 150 знаков"],
        ["anna!", "Логин может состоять только из букв, цифр и знаков @ . + - _"],
        ["anna k", "Логин может состоять только из букв, цифр и знаков @ . + - _"],
    ])("rejects %s", (username, expectedMessage) => {
        expect(checkNewUsername(username)).toBe(expectedMessage);
    });
});

describe("checkNewPassword", () => {
    it("checks the length", () => {
        expect(checkNewPassword("")).toBe(REQUIRED_FIELD_TEXT);
        expect(checkNewPassword("short")).toBe("Пароль не короче 8 знаков");
        expect(checkNewPassword("x".repeat(129))).toBe("Пароль не длиннее 128 знаков");
        expect(checkNewPassword("quiet-river-2026")).toBeNull();
    });
});

describe("checkPasswordConfirmation", () => {
    it("requires the same password", () => {
        expect(checkPasswordConfirmation("quiet-river-2026", "")).toBe(REQUIRED_FIELD_TEXT);
        expect(checkPasswordConfirmation("quiet-river-2026", "quiet-river-2025")).toBe(PASSWORDS_DIFFER_TEXT);
        expect(checkPasswordConfirmation("quiet-river-2026", "quiet-river-2026")).toBeNull();
    });
});

describe("listTimeZones", () => {
    it("keeps the current time zone even when the browser does not list it", () => {
        const timeZones = listTimeZones("Europe/Kiev");

        expect(timeZones).toContain("Europe/Kiev");
        expect(timeZones).toEqual([...timeZones].sort());
    });
});
