import type { Account, AccountBody, AccountCreateInput, AccountList, AccountListBody, AccountUpdateInput } from "../types/ledger";
import { requestJson } from "./apiClient";

const ACCOUNTS_ENDPOINT = "/api/accounts";

function buildAccountUrl(accountId: number): string {
    return `${ACCOUNTS_ENDPOINT}/${accountId}`;
}

export function toAccount(body: AccountBody): Account {
    return {
        id: body.id,
        name: body.name,
        kind: body.kind,
        currency: body.currency,
        initialBalance: body.initial_balance,
        balance: body.balance,
        isArchived: body.is_archived,
        createdAt: body.created_at,
    };
}

export async function fetchAccounts(): Promise<AccountList> {
    const body = await requestJson<AccountListBody>(ACCOUNTS_ENDPOINT);

    return {
        items: body.items.map(toAccount),
        totalBalance: body.total_balance,
    };
}

export async function createAccount(input: AccountCreateInput): Promise<Account> {
    const body = await requestJson<AccountBody>(ACCOUNTS_ENDPOINT, {
        method: "POST",
        body: { name: input.name, kind: input.kind, initial_balance: input.initialBalance },
    });

    return toAccount(body);
}

export async function updateAccount(accountId: number, changes: AccountUpdateInput): Promise<Account> {
    const requestBody: Record<string, string | boolean> = {};

    // PATCH меняет только присланные поля, поэтому неуказанные изменения в тело не попадают
    if (changes.name !== undefined) {
        requestBody.name = changes.name;
    }

    if (changes.initialBalance !== undefined) {
        requestBody.initial_balance = changes.initialBalance;
    }

    if (changes.isArchived !== undefined) {
        requestBody.is_archived = changes.isArchived;
    }

    const body = await requestJson<AccountBody>(buildAccountUrl(accountId), { method: "PATCH", body: requestBody });

    return toAccount(body);
}

export async function deleteAccount(accountId: number): Promise<void> {
    await requestJson<undefined>(buildAccountUrl(accountId), { method: "DELETE" });
}
