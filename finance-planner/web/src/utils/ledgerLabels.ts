import type { AccountKind, CategoryKind, OperationKind } from "../types/ledger";
import { COLUMN_GROUPING_DIGITS, formatMoney } from "./money";

export const ACCOUNT_KIND_LABELS: Record<AccountKind, string> = {
    cash: "Наличные",
    card: "Карта",
    savings: "Накопительный",
};

export const ACCOUNT_KIND_OPTIONS = Object.entries(ACCOUNT_KIND_LABELS).map(([value, label]) => ({ value, label }));

export const CATEGORY_KIND_LABELS: Record<CategoryKind, string> = {
    expense: "Расход",
    income: "Доход",
};

export const OPERATION_KIND_LABELS: Record<OperationKind, string> = {
    expense: "Расход",
    income: "Доход",
    transfer_out: "Перевод: списание",
    transfer_in: "Перевод: зачисление",
};

export const OPERATION_KIND_OPTIONS = Object.entries(OPERATION_KIND_LABELS).map(([value, label]) => ({ value, label }));

const DECREASING_KINDS: ReadonlySet<OperationKind> = new Set(["expense", "transfer_out"]);

export function isDecreasingKind(kind: OperationKind): boolean {
    return DECREASING_KINDS.has(kind);
}

// Знак суммы показывает направление движения, а не только цвет строки
export function formatOperationAmount(kind: OperationKind, amount: string, currencyCode: string): string {
    const columnOptions = { groupingDigits: COLUMN_GROUPING_DIGITS };

    if (isDecreasingKind(kind)) {
        return formatMoney(`-${amount}`, currencyCode, columnOptions);
    }

    return `+${formatMoney(amount, currencyCode, columnOptions)}`;
}
