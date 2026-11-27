import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed } from "vue";
import type { Ref } from "vue";

import { createOperation, deleteOperation, fetchOperations, updateOperation } from "../services/operationsApi";
import { queryKeys } from "../services/queryKeys";
import type { OperationChanges, OperationListParameters } from "../types/ledger";

interface OperationUpdate {
    operationId: number;
    changes: OperationChanges;
}

export function useOperationsQuery(parameters: Ref<OperationListParameters>) {
    // Параметры входят в ключ: смена фильтра или страницы сама запрашивает новый список,
    // а прежняя страница остаётся на экране, пока не пришла следующая
    const queryKey = computed(() => [...queryKeys.operations, parameters.value]);

    return useQuery({
        queryKey,
        queryFn: () => fetchOperations(parameters.value),
        placeholderData: keepPreviousData,
    });
}

export function useOperationMutations() {
    const queryClient = useQueryClient();

    // Операция меняет и историю, и балансы счетов, поэтому устаревают оба списка
    async function refreshLedger(): Promise<void> {
        await Promise.all([
            queryClient.invalidateQueries({ queryKey: queryKeys.operations }),
            queryClient.invalidateQueries({ queryKey: queryKeys.accounts }),
        ]);
    }

    const createMutation = useMutation({
        mutationFn: createOperation,
        onSuccess: refreshLedger,
    });

    const updateMutation = useMutation({
        mutationFn: ({ operationId, changes }: OperationUpdate) => updateOperation(operationId, changes),
        onSuccess: refreshLedger,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteOperation,
        onSuccess: refreshLedger,
    });

    return {
        createMutation,
        deleteMutation,
        updateMutation,
    };
}
