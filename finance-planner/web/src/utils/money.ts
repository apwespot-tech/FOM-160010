// Невидимые и похожие на дефис знаки записаны кодами, чтобы их было видно в исходнике
export const NON_BREAKING_SPACE = "\u00a0";
export const MINUS_SIGN = "\u2212";

const CURRENCY_SIGNS: Record<string, string> = {
    RUB: "₽",
};

const AMOUNT_PATTERN = /^(-?)([0-9]+)(?:\.([0-9]{1,2}))?$/;
const INPUT_AMOUNT_PATTERN = /^-?[0-9]{1,12}(?:\.[0-9]{1,2})?$/;
const LEADING_ZEROS_PATTERN = /^0+(?=[0-9])/;
const ZERO_DIGITS_PATTERN = /^0+$/;
const WHITESPACE_PATTERN = /\s/g;
const UNICODE_MINUS_PATTERN = /\u2212/g;
const GROUP_SIZE = 3;
const CENT_DIGITS = 2;
// Разряды отделяются в числах от пяти знаков, четырёхзначные пишутся слитно. В столбце таблицы делят и четырёхзначные
export const DEFAULT_GROUPING_DIGITS = 5;
export const COLUMN_GROUPING_DIGITS = 4;

export interface MoneyFormatOptions {
    groupingDigits?: number;
}

export function groupThousands(integerDigits: string, groupingDigits: number = DEFAULT_GROUPING_DIGITS): string {
    if (integerDigits.length < groupingDigits) {
        return integerDigits;
    }

    const groups: string[] = [];

    for (let groupEnd = integerDigits.length; groupEnd > 0; groupEnd -= GROUP_SIZE) {
        const groupStart = Math.max(0, groupEnd - GROUP_SIZE);
        groups.unshift(integerDigits.slice(groupStart, groupEnd));
    }

    return groups.join(NON_BREAKING_SPACE);
}

export function describeCurrency(currencyCode: string): string {
    return CURRENCY_SIGNS[currencyCode] ?? currencyCode;
}

// Сумма приходит из API строкой: так она не теряет копейки, а точка и разряды не зависят от языка браузера
export function formatMoney(amount: string, currencyCode: string, options: MoneyFormatOptions = {}): string {
    const match = AMOUNT_PATTERN.exec(amount);

    if (match === null) {
        return amount;
    }

    const [, minus, rawIntegerDigits, rawCents = ""] = match;
    const integerDigits = rawIntegerDigits.replace(LEADING_ZEROS_PATTERN, "");
    const cents = rawCents.padEnd(CENT_DIGITS, "0");
    const isZero = ZERO_DIGITS_PATTERN.test(integerDigits) && ZERO_DIGITS_PATTERN.test(cents);
    const sign = minus === "-" && !isZero ? MINUS_SIGN : "";
    const groupedDigits = groupThousands(integerDigits, options.groupingDigits);
    const currencySign = describeCurrency(currencyCode);

    return `${sign}${groupedDigits}.${cents}${NON_BREAKING_SPACE}${currencySign}`;
}

// Ввод снисходителен: принимаются запятая, пробелы между разрядами и знак минуса, на сервер уходит строка вида 1234.50
export function normalizeAmountInput(text: string, isNegativeAllowed: boolean = false): string | null {
    const compactText = text.replace(WHITESPACE_PATTERN, "").replace(UNICODE_MINUS_PATTERN, "-").replace(",", ".");

    if (!INPUT_AMOUNT_PATTERN.test(compactText)) {
        return null;
    }

    const isNegative = compactText.startsWith("-");

    if (isNegative && !isNegativeAllowed) {
        return null;
    }

    // Ведущие нули убираются, чтобы «00» распознавался как ноль ещё в браузере, а «−0» не давал отрицательного нуля
    const [integerPart, fractionPart = ""] = compactText.replace("-", "").split(".");
    const integerDigits = integerPart.replace(LEADING_ZEROS_PATTERN, "");
    const cents = fractionPart.padEnd(CENT_DIGITS, "0");
    const isZero = ZERO_DIGITS_PATTERN.test(integerDigits) && ZERO_DIGITS_PATTERN.test(cents);
    const sign = isNegative && !isZero ? "-" : "";

    return `${sign}${integerDigits}.${cents}`;
}

export function isZeroAmount(normalizedAmount: string): boolean {
    const [integerPart, fractionPart = ""] = normalizedAmount.replace("-", "").split(".");

    return ZERO_DIGITS_PATTERN.test(integerPart) && ZERO_DIGITS_PATTERN.test(fractionPart.padEnd(CENT_DIGITS, "0"));
}
