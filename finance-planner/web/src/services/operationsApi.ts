import type {
    Operation,
    OperationBody,
    OperationChanges,
    OperationInput,
    OperationListParameters,
    OperationPage,
    OperationPageBody,
} from "../types/ledger";
import { requestJson } from "./apiClient";

const OPERATIONS_ENDPOINT = "/api/operations";

function buildOperationUrl(operationId: number): string {
    return `${OPERATIONS_ENDPOINT}/${operationId}`;
}

function toOperation(body: OperationBody): Operation {
    return {
        id: body.id,
        kind: body.kind,
        accountId: body.account_id,
        categoryId: body.category_id,
        amount: body.amount,
        date: body.date,
        note: body.note,
        transferId: body.transfer_id,
        createdAt: body.created_at,
    };
}

export async function fetchOperations(parameters: OperationListParameters): Promise<OperationPage> {
    const body = await requestJson<OperationPageBody>(OPERATIONS_ENDPOINT, {
        query: {
            date_from: parameters.dateFrom,
            date_to: parameters.dateTo,
            account_id: parameters.accountId,
            category_id: parameters.categoryId,
            kind: parameters.kind,
            sort: parameters.sort,
            page: parameters.page,
            page_size: parameters.pageSize,
        },
    });

    return {
        items: body.items.map(toOperation),
        count: body.count,
    };
}

export async function createOperation(input: OperationInput): Promise<Operation> {
    const body = await requestJson<OperationBody>(OPERATIONS_ENDPOINT, {
        method: "POST",
        body: {
            kind: input.kind,
            account_id: input.accountId,
            category_id: input.categoryId,
            amount: input.amount,
            date: input.date,
            note: input.note,
        },
    });

    return toOperation(body);
}

export async function updateOperation(operationId: number, changes: OperationChanges): Promise<Operation> {
    // В теле PATCH только присланные поля: так правка не затирает то, что пользователь не трогал
    const requestBody: Record<string, string | number> = {};

    if (changes.accountId !== undefined) {
        requestBody.account_id = changes.accountId;
    }

    if (changes.categoryId !== undefined) {
        requestBody.category_id = changes.categoryId;
    }

    if (changes.amount !== undefined) {
        requestBody.amount = changes.amount;
    }

    if (changes.date !== undefined) {
        requestBody.date = changes.date;
    }

    if (changes.note !== undefined) {
        requestBody.note = changes.note;
    }

    const body = await requestJson<OperationBody>(buildOperationUrl(operationId), { method: "PATCH", body: requestBody });

    return toOperation(body);
}

export async function deleteOperation(operationId: number): Promise<void> {
    await requestJson<undefined>(buildOperationUrl(operationId), { method: "DELETE" });
}
