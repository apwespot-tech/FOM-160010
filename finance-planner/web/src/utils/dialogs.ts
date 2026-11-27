// Те же свойства, что у крестика PrimeVue по умолчанию, плюс недоступность: пока идёт сохранение, диалог не закрывается,
// иначе ошибка ответа попала бы в уже скрытую форму и пользователь решил бы, что данные сохранены
export function buildCloseButtonProps(isBusy: boolean): Record<string, string | boolean> {
    return { severity: "secondary", text: true, rounded: true, disabled: isBusy };
}
