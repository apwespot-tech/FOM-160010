import type { AccountKind } from "../types/ledger";

export const ACCOUNT_KIND_LABELS: Record<AccountKind, string> = {
    cash: "Наличные",
    card: "Карта",
    savings: "Накопительный",
};

export const ACCOUNT_KIND_OPTIONS = Object.entries(ACCOUNT_KIND_LABELS).map(([value, label]) => ({ value, label }));
