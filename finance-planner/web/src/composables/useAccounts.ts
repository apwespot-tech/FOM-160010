import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import { createAccount, deleteAccount, fetchAccounts, updateAccount } from "../services/accountsApi";
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

    const createMutation = useMutation({
        mutationFn: createAccount,
        onSuccess: refreshAccounts,
    });

    const updateMutation = useMutation({
        mutationFn: ({ accountId, changes }: AccountChanges) => updateAccount(accountId, changes),
        onSuccess: refreshAccounts,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteAccount,
        onSuccess: refreshAccounts,
    });

    return {
        createMutation,
        deleteMutation,
        updateMutation,
    };
}
