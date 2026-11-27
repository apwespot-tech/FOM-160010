import { describe, expect, it } from "vitest";

import { buildReturnQuery, findOwnPath, readReturnPath } from "./returnPath";

// Браузер читает обратную косую черту как прямую и выбрасывает из адреса табуляцию и переводы строки
const FOREIGN_PATHS = [
    "//example.com",
    "/\\example.com",
    "/\t/example.com",
    "/\n/example.com",
    "https://example.com",
    "operations",
    "",
];

describe("findOwnPath", () => {
    it("returns a path of the planner with its query and fragment", () => {
        expect(findOwnPath("/operations?page=2#top")).toBe("/operations?page=2#top");
    });

    it.each(FOREIGN_PATHS)("rejects %j", (nextValue) => {
        expect(findOwnPath(nextValue)).toBeNull();
    });

    it.each([undefined, null, ["/accounts"]])("rejects a value that is not a string: %j", (nextValue) => {
        expect(findOwnPath(nextValue)).toBeNull();
    });
});

describe("readReturnPath", () => {
    it("returns an own path", () => {
        expect(readReturnPath("/accounts")).toBe("/accounts");
    });

    it("sends a foreign or missing path to the home page", () => {
        expect(readReturnPath("/\\example.com")).toBe("/");
        expect(readReturnPath(undefined)).toBe("/");
    });
});

describe("buildReturnQuery", () => {
    it("passes an own path on", () => {
        expect(buildReturnQuery("/accounts")).toEqual({ next: "/accounts" });
    });

    it("drops a foreign or missing path", () => {
        expect(buildReturnQuery("//example.com")).toEqual({});
        expect(buildReturnQuery(undefined)).toEqual({});
    });
});
