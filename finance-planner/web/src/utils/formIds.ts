// Подпись, подсказка и ошибка поля получают id от id самого поля: так их связывают атрибуты aria у полей любого вида
export function buildLabelId(inputId: string): string {
    return `${inputId}-label`;
}

export function buildHintId(inputId: string): string {
    return `${inputId}-hint`;
}

export function buildErrorId(inputId: string): string {
    return `${inputId}-error`;
}
