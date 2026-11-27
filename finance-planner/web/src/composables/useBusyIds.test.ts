import { describe, expect, it } from "vitest";

import { useBusyIds } from "./useBusyIds";

describe("useBusyIds", () => {
    it("keeps each record busy until its own request ends", () => {
        const { busyIds, markBusy, releaseBusy } = useBusyIds();

        markBusy(3);
        markBusy(5);
        releaseBusy(3);

        expect([...busyIds.value]).toEqual([5]);
    });
});
