const ISO_DATE_PATTERN = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/;
const MONTH_OFFSET = 1;
const DATE_PART_LENGTH = 2;

function padDatePart(value: number): string {
    return String(value).padStart(DATE_PART_LENGTH, "0");
}

// Части даты берутся из Intl с латинскими цифрами: так «сегодня» считается в поясе пользователя, а не браузера
export function formatIsoDateInTimeZone(moment: Date, timeZone: string): string {
    const formatter = new Intl.DateTimeFormat("en-US", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" });
    const partValues = new Map(formatter.formatToParts(moment).map((part) => [part.type, part.value]));
    const year = partValues.get("year") ?? "";
    const month = partValues.get("month") ?? "";
    const day = partValues.get("day") ?? "";

    return `${year}-${month}-${day}`;
}

export function readTodayInTimeZone(timeZone: string): string {
    return formatIsoDateInTimeZone(new Date(), timeZone);
}

// Календарь PrimeVue работает с местной полуночью браузера, а API с датой без времени
export function isoDateToLocalDate(isoDate: string): Date | null {
    const match = ISO_DATE_PATTERN.exec(isoDate);

    if (match === null) {
        return null;
    }

    const [, year, month, day] = match;

    return new Date(Number(year), Number(month) - MONTH_OFFSET, Number(day));
}

export function localDateToIsoDate(localDate: Date): string {
    const year = localDate.getFullYear();
    const month = padDatePart(localDate.getMonth() + MONTH_OFFSET);
    const day = padDatePart(localDate.getDate());

    return `${year}-${month}-${day}`;
}
