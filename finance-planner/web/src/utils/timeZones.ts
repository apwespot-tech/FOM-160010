interface IntlWithTimeZoneList {
    supportedValuesOf?: (key: "timeZone") => string[];
}

export function readBrowserTimeZone(): string | null {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    if (typeof timeZone !== "string" || timeZone === "") {
        return null;
    }

    return timeZone;
}

// Список браузера и база поясов сервера расходятся в отдельных именах (Europe/Kiev и Europe/Kyiv),
// поэтому текущий пояс пользователя добавляется к списку, даже если браузер его не перечисляет
export function listTimeZones(currentTimeZone: string): string[] {
    const intlWithList = Intl as IntlWithTimeZoneList;
    const browserTimeZones = intlWithList.supportedValuesOf?.("timeZone") ?? [];
    const timeZones = new Set(browserTimeZones);

    timeZones.add(currentTimeZone);

    return Array.from(timeZones).sort();
}
