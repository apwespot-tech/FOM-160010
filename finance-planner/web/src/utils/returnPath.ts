import type { LocationQueryRaw } from "vue-router";

const HOME_PATH = "/";

function isOwnPath(nextValue: unknown): nextValue is string {
    return typeof nextValue === "string" && nextValue.startsWith("/") && !nextValue.startsWith("//");
}

// Адрес возврата приходит из строки запроса, которую может подставить кто угодно, поэтому принимается только свой путь
export function readReturnPath(nextValue: unknown): string {
    if (isOwnPath(nextValue)) {
        return nextValue;
    }

    return HOME_PATH;
}

// Ссылки между входом и регистрацией и страница проверки сервисов передают адрес возврата дальше, а не теряют его
export function buildReturnQuery(nextValue: unknown): LocationQueryRaw {
    if (isOwnPath(nextValue)) {
        return { next: nextValue };
    }

    return {};
}
