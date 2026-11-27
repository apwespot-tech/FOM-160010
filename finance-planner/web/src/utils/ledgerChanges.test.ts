import { describe, expect, it } from "vitest";

import type { Account, Operation } from "../types/ledger";
import { collectAccountChanges, collectOperationChanges } from "./ledgerChanges";

const ACCOUNT: Account = {
    id: 3,
    name: "Карта",
    kind: "card",
    currency: "RUB",
    initialBalance: "15000.00",
    balance: "14200.00",
    isArchived: false,
    createdAt: "2026-11-27T08:00:00Z",
};

const OPERATION: Operation = {
    id: 8,
    kind: "expense",
    accountId: 3,
    categoryId: 4,
    amount: "1250.50",
    date: "2026-11-18",
    note: "Продукты на неделю",
    transferId: null,
    createdAt: "2026-11-27T08:05:00Z",
};

describe("collectAccountChanges", () => {
    it("sends nothing when the form is unchanged", () => {
        expect(collectAccountChanges(ACCOUNT, { name: "Карта", initialBalance: "15000.00", isArchived: false })).toEqual({});
    });

    it("sends only the changed fields", () => {
        expect(collectAccountChanges(ACCOUNT, { name: "Карта", initialBalance: "15000.00", isArchived: true })).toEqual({ isArchived: true });
    });
});

describe("collectOperationChanges", () => {
    const unchangedValues = { accountId: 3, categoryId: 4, amount: "1250.50", date: "2026-11-18", note: "Продукты на неделю" };

    it("sends nothing when the form is unchanged", () => {
        expect(collectOperationChanges(OPERATION, unchangedValues)).toEqual({});
    });

    it("leaves out the fields that another tab may have changed", () => {
        expect(collectOperationChanges(OPERATION, { ...unchangedValues, note: "Рынок" })).toEqual({ note: "Рынок" });
    });
});
