// Те же границы, что у схем API: проверка на клиенте лишь подсказывает раньше, последнее слово за сервером
export const USERNAME_MIN_LENGTH = 3;
export const USERNAME_MAX_LENGTH = 150;
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

export const REQUIRED_FIELD_TEXT = "Заполните поле";
export const PASSWORDS_DIFFER_TEXT = "Пароли не совпадают";

// Как у валидатора логина Django: буквы и цифры любого алфавита, подчёркивание и знаки @ . + -
const USERNAME_CHARACTERS_PATTERN = /^[\p{L}\p{N}_.@+-]+$/u;

export function checkRequired(value: string): string | null {
    if (value.trim() === "") {
        return REQUIRED_FIELD_TEXT;
    }

    return null;
}

export function checkNewUsername(value: string): string | null {
    const username = value.trim();

    if (username === "") {
        return REQUIRED_FIELD_TEXT;
    }

    if (username.length < USERNAME_MIN_LENGTH) {
        return `Логин не короче ${USERNAME_MIN_LENGTH} знаков`;
    }

    if (username.length > USERNAME_MAX_LENGTH) {
        return `Логин не длиннее ${USERNAME_MAX_LENGTH} знаков`;
    }

    if (!USERNAME_CHARACTERS_PATTERN.test(username)) {
        return "Логин может состоять только из букв, цифр и знаков @ . + - _";
    }

    return null;
}

export function checkNewPassword(value: string): string | null {
    if (value === "") {
        return REQUIRED_FIELD_TEXT;
    }

    if (value.length < PASSWORD_MIN_LENGTH) {
        return `Пароль не короче ${PASSWORD_MIN_LENGTH} знаков`;
    }

    if (value.length > PASSWORD_MAX_LENGTH) {
        return `Пароль не длиннее ${PASSWORD_MAX_LENGTH} знаков`;
    }

    return null;
}

export function checkPasswordConfirmation(password: string, confirmation: string): string | null {
    if (confirmation === "") {
        return REQUIRED_FIELD_TEXT;
    }

    if (confirmation !== password) {
        return PASSWORDS_DIFFER_TEXT;
    }

    return null;
}
