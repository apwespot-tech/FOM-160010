import { afterEach, describe, expect, it } from "vitest";

import { CSRF_COOKIE_NAME, readCookie, readCsrfToken } from "./csrf";

describe("readCookie", () => {
    it("finds a cookie among others", () => {
        expect(readCookie("sessionid=abc; csrftoken=token-1; theme=dark", CSRF_COOKIE_NAME)).toBe("token-1");
    });

    it("does not confuse a cookie with a longer name", () => {
        expect(readCookie("xcsrftoken=wrong; csrftoken=right", CSRF_COOKIE_NAME)).toBe("right");
    });

    it("decodes an encoded value", () => {
        expect(readCookie("note=a%20b", "note")).toBe("a b");
    });

    it("keeps a value with a broken escape sequence", () => {
        expect(readCookie("note=100%", "note")).toBe("100%");
    });

    it("returns null when the cookie is missing", () => {
        expect(readCookie("", CSRF_COOKIE_NAME)).toBeNull();
        expect(readCookie("sessionid=abc", CSRF_COOKIE_NAME)).toBeNull();
    });
});

describe("readCsrfToken", () => {
    afterEach(() => {
        document.cookie = `${CSRF_COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    });

    it("reads the token from document.cookie", () => {
        document.cookie = `${CSRF_COOKIE_NAME}=browser-token`;

        expect(readCsrfToken()).toBe("browser-token");
    });
});
