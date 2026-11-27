export type AccountKind = "cash" | "card" | "savings";

export interface AccountBody {
    id: number;
    name: string;
    kind: AccountKind;
    currency: string;
    initial_balance: string;
    balance: string;
    is_archived: boolean;
    created_at: string;
}

export interface AccountListBody {
    items: AccountBody[];
    total_balance: string;
}

export interface Account {
    id: number;
    name: string;
    kind: AccountKind;
    currency: string;
    initialBalance: string;
    balance: string;
    isArchived: boolean;
    createdAt: string;
}

export interface AccountList {
    items: Account[];
    totalBalance: string;
}

export interface AccountCreateInput {
    name: string;
    kind: AccountKind;
    initialBalance: string;
}

export interface AccountUpdateInput {
    name?: string;
    initialBalance?: string;
    isArchived?: boolean;
}
