import type { Account, AccountUpdateInput, AccountValues, Operation, OperationChanges, OperationValues } from "../types/ledger";

// В PATCH уходят только изменённые поля, чтобы правка не затёрла то, что за это время поменяли в другой вкладке
export function collectAccountChanges(account: Account, values: AccountValues): AccountUpdateInput {
    const changes: AccountUpdateInput = {};

    if (values.name !== account.name) {
        changes.name = values.name;
    }

    if (values.initialBalance !== account.initialBalance) {
        changes.initialBalance = values.initialBalance;
    }

    if (values.isArchived !== account.isArchived) {
        changes.isArchived = values.isArchived;
    }

    return changes;
}

export function collectOperationChanges(operation: Operation, values: OperationValues): OperationChanges {
    const changes: OperationChanges = {};

    if (values.accountId !== operation.accountId) {
        changes.accountId = values.accountId;
    }

    if (values.categoryId !== operation.categoryId) {
        changes.categoryId = values.categoryId;
    }

    if (values.amount !== operation.amount) {
        changes.amount = values.amount;
    }

    if (values.date !== operation.date) {
        changes.date = values.date;
    }

    if (values.note !== operation.note) {
        changes.note = values.note;
    }

    return changes;
}
