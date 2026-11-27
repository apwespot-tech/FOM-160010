import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import { createAccount, deleteAccount, fetchAccounts, updateAccount } from "../services/accountsApi";
import { ApiError } from "../services/apiClient";
import { queryKeys } from "../services/queryKeys";
import type { AccountUpdateInput } from "../types/ledger";

interface AccountChanges {
    accountId: number;
    changes: AccountUpdateInput;
}

export function useAccountsQuery() {
    return useQuery({
        queryKey: queryKeys.accounts,
        queryFn: fetchAccounts,
    });
}

export function useAccountMutations() {
    const queryClient = useQueryClient();

    // Мутация ждёт обновления списка, поэтому новые балансы видны сразу после закрытия диалога
    async function refreshAccounts(): Promise<void> {
        await queryClient.invalidateQueries({ queryKey: queryKeys.accounts });
    }

    // Ответ 404 значит, что счёт уже удалили в другой вкладке: список обновляется, как обещает docs/api.md
    async function refreshAfterMissing(error: Error): Promise<void> {
        if (error instanceof ApiError && error.code === "not_found") {
            await refreshAccounts();
        }
    }

    const createMutation = useMutation({
        mutationFn: createAccount,
        onSuccess: refreshAccounts,
    });

    const updateMutation = useMutation({
        mutationFn: ({ accountId, changes }: AccountChanges) => updateAccount(accountId, changes),
        onSuccess: refreshAccounts,
        onError: refreshAfterMissing,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteAccount,
        onSuccess: refreshAccounts,
        onError: refreshAfterMissing,
    });

    return {
        createMutation,
        deleteMutation,
        updateMutation,
    };
}
