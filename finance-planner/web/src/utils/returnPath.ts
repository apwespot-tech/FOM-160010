import type { LocationQueryRaw } from "vue-router";

const HOME_PATH = "/";

function parseUrl(text: string, baseUrl: string): URL | null {
    try {
        return new URL(text, baseUrl);
    } catch {
        // Строку, которую браузер не разбирает как адрес, своей страницей не считаем
        return null;
    }
}

// Адрес возврата приходит из строки запроса, которую может подставить кто угодно. Браузер уводит на чужой сайт и по адресам
// вида /\site или со знаком табуляции внутри, поэтому путь проверяет сам разбор адреса, а наружу идёт уже разобранный путь
export function findOwnPath(nextValue: unknown): string | null {
    if (typeof nextValue !== "string" || !nextValue.startsWith("/")) {
        return null;
    }

    const origin = window.location.origin;
    const parsedUrl = parseUrl(nextValue, origin);

    if (parsedUrl === null || parsedUrl.origin !== origin) {
        return null;
    }

    return `${parsedUrl.pathname}${parsedUrl.search}${parsedUrl.hash}`;
}

export function readReturnPath(nextValue: unknown): string {
    return findOwnPath(nextValue) ?? HOME_PATH;
}

// Ссылки между входом и регистрацией передают адрес возврата дальше, а не теряют его
export function buildReturnQuery(nextValue: unknown): LocationQueryRaw {
    const ownPath = findOwnPath(nextValue);

    if (ownPath === null) {
        return {};
    }

    return { next: ownPath };
}
