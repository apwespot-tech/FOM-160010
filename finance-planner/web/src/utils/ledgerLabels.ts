import type { AccountKind, CategoryKind, OperationKind } from "../types/ledger";
import { COLUMN_GROUPING_DIGITS, formatMoney } from "./money";
import type { MoneyFormatOptions } from "./money";

export interface ChoiceOption<T extends string> {
    value: T;
    label: string;
}

export const ACCOUNT_KIND_LABELS: Record<AccountKind, string> = {
    cash: "Наличные",
    card: "Карта",
    savings: "Накопительный",
};

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

// Списки собраны из тех же словарей подписей, но с явным типом значения: v-model получает вид, а не любую строку
export const ACCOUNT_KIND_OPTIONS: ChoiceOption<AccountKind>[] = [
    { value: "cash", label: ACCOUNT_KIND_LABELS.cash },
    { value: "card", label: ACCOUNT_KIND_LABELS.card },
    { value: "savings", label: ACCOUNT_KIND_LABELS.savings },
];

export const CATEGORY_KIND_OPTIONS: ChoiceOption<CategoryKind>[] = [
    { value: "expense", label: CATEGORY_KIND_LABELS.expense },
    { value: "income", label: CATEGORY_KIND_LABELS.income },
];

export const OPERATION_KIND_OPTIONS: ChoiceOption<OperationKind>[] = [
    { value: "expense", label: OPERATION_KIND_LABELS.expense },
    { value: "income", label: OPERATION_KIND_LABELS.income },
    { value: "transfer_out", label: OPERATION_KIND_LABELS.transfer_out },
    { value: "transfer_in", label: OPERATION_KIND_LABELS.transfer_in },
];

const DECREASING_KINDS: ReadonlySet<OperationKind> = new Set(["expense", "transfer_out"]);
const COLUMN_FORMAT: MoneyFormatOptions = { groupingDigits: COLUMN_GROUPING_DIGITS };

export function isDecreasingKind(kind: OperationKind): boolean {
    return DECREASING_KINDS.has(kind);
}

export function isCategoryKind(kind: OperationKind): kind is CategoryKind {
    return kind === "income" || kind === "expense";
}

// Знак суммы показывает направление движения, а не только цвет строки. По умолчанию разряды делятся, как в столбце таблицы
export function formatOperationAmount(
    kind: OperationKind,
    amount: string,
    currencyCode: string,
    options: MoneyFormatOptions = COLUMN_FORMAT,
): string {
    if (isDecreasingKind(kind)) {
        return formatMoney(`-${amount}`, currencyCode, options);
    }

    return `+${formatMoney(amount, currencyCode, options)}`;
}
