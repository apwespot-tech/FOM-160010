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

export type AccountValues = Required<AccountUpdateInput>;

export type CategoryKind = "income" | "expense";
export type OperationKind = "income" | "expense" | "transfer_out" | "transfer_in";
export type OperationSort = "-date" | "date";

export interface CategoryBody {
    id: number;
    name: string;
    kind: CategoryKind;
    is_common: boolean;
}

export interface Category {
    id: number;
    name: string;
    kind: CategoryKind;
    isCommon: boolean;
}

export interface OperationBody {
    id: number;
    kind: OperationKind;
    account_id: number;
    category_id: number | null;
    amount: string;
    date: string;
    note: string;
    transfer_id: number | null;
    created_at: string;
}

export interface OperationPageBody {
    items: OperationBody[];
    count: number;
}

export interface Operation {
    id: number;
    kind: OperationKind;
    accountId: number;
    categoryId: number | null;
    amount: string;
    date: string;
    note: string;
    transferId: number | null;
    createdAt: string;
}

export interface OperationPage {
    items: Operation[];
    count: number;
}

export interface OperationFilters {
    dateFrom: string | null;
    dateTo: string | null;
    accountId: number | null;
    categoryId: number | null;
    kind: OperationKind | null;
}

export interface OperationListParameters extends OperationFilters {
    page: number;
    pageSize: number;
    sort: OperationSort;
}

export interface OperationInput {
    kind: CategoryKind;
    accountId: number;
    categoryId: number;
    amount: string;
    date: string;
    note: string;
}

export type OperationValues = Omit<OperationInput, "kind">;
export type OperationChanges = Partial<OperationValues>;
