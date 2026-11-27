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

// Варианты выбора строятся из словаря подписей: тип Record требует подпись у каждого вида, поэтому ни один вид не потеряется,
// а v-model получает вид, а не любую строку
function listChoices<T extends string>(labels: Record<T, string>): ChoiceOption<T>[] {
    // Object.keys возвращает просто строки, а ключи словаря подписей и есть виды
    const values = Object.keys(labels) as T[];

    return values.map((value) => ({ value, label: labels[value] }));
}

export const ACCOUNT_KIND_OPTIONS = listChoices(ACCOUNT_KIND_LABELS);
export const CATEGORY_KIND_OPTIONS = listChoices(CATEGORY_KIND_LABELS);
export const OPERATION_KIND_OPTIONS = listChoices(OPERATION_KIND_LABELS);

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
