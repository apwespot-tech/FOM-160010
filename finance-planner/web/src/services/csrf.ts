export const CSRF_COOKIE_NAME = "csrftoken";

function decodeCookieValue(rawValue: string): string {
    try {
        return decodeURIComponent(rawValue);
    } catch {
        // Испорченную escape-последовательность отдаём как есть: сервер сам отклонит такой токен
        return rawValue;
    }
}

export function readCookie(cookieText: string, cookieName: string): string | null {
    const prefix = `${cookieName}=`;

    for (const part of cookieText.split(";")) {
        const trimmedPart = part.trim();

        if (trimmedPart.startsWith(prefix)) {
            return decodeCookieValue(trimmedPart.slice(prefix.length));
        }
    }

    return null;
}

export function readCsrfToken(): string | null {
    return readCookie(document.cookie, CSRF_COOKIE_NAME);
}
