import { describe, expect, it } from "vitest";

import { formatIsoDateInTimeZone, isoDateToLocalDate, localDateToIsoDate } from "./dates";

describe("formatIsoDateInTimeZone", () => {
    it("uses the date of the given time zone", () => {
        const moment = new Date("2026-11-20T20:30:00Z");

        expect(formatIsoDateInTimeZone(moment, "Asia/Yekaterinburg")).toBe("2026-11-21");
        expect(formatIsoDateInTimeZone(moment, "UTC")).toBe("2026-11-20");
        expect(formatIsoDateInTimeZone(moment, "America/New_York")).toBe("2026-11-20");
    });
});

describe("isoDateToLocalDate and localDateToIsoDate", () => {
    it("keep the calendar date", () => {
        const localDate = isoDateToLocalDate("2026-02-28");

        expect(localDate).not.toBeNull();
        expect(localDateToIsoDate(localDate as Date)).toBe("2026-02-28");
    });

    it("pads the month and the day", () => {
        expect(localDateToIsoDate(new Date(2026, 0, 5))).toBe("2026-01-05");
    });

    it.each(["", "2026-2-28", "28.02.2026", "2026-02-28T00:00"])("rejects %s", (text) => {
        expect(isoDateToLocalDate(text)).toBeNull();
    });
});
