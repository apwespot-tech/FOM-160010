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

// Список поясов браузера не содержит устаревших имён, которые знает сервер, поэтому текущий пояс добавляется к нему сам
export function listTimeZones(currentTimeZone: string): string[] {
    const intlWithList = Intl as IntlWithTimeZoneList;
    const browserTimeZones = intlWithList.supportedValuesOf?.("timeZone") ?? [];
    const timeZones = new Set(browserTimeZones);

    timeZones.add(currentTimeZone);

    return Array.from(timeZones).sort();
}
