import { describe, expect, it } from "vitest";

import { buildReturnQuery, readReturnPath } from "./returnPath";

describe("readReturnPath", () => {
    it("returns a path of the planner with its query", () => {
        expect(readReturnPath("/operations?page=2")).toBe("/operations?page=2");
    });

    it.each(["//example.com", "https://example.com", "operations", "", undefined, null, ["/accounts"]])("sends %s to the home page", (nextValue) => {
        expect(readReturnPath(nextValue)).toBe("/");
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
