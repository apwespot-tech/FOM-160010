<script setup lang="ts">
import Button from "primevue/button";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";
import { useConfirm } from "primevue/useconfirm";
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import OperationDialog from "../components/OperationDialog.vue";
import OperationFilters from "../components/OperationFilters.vue";
import OperationsTable from "../components/OperationsTable.vue";
import { useAccountsQuery } from "../composables/useAccounts";
import { useCategoriesQuery } from "../composables/useCategories";
import { useDelayedFlag } from "../composables/useDelayedFlag";
import { useNotifier } from "../composables/useNotifier";
import { useOperationMutations, useOperationsQuery } from "../composables/useOperations";
import { describeError } from "../services/apiClient";
import { useSessionStore } from "../stores/session";
import type { Operation, OperationFilters as OperationFilterValues, OperationListParameters, OperationSort } from "../types/ledger";
import { formatOperationAmount } from "../utils/ledgerLabels";

const DEFAULT_PAGE_SIZE = 20;
const FIRST_PAGE = 1;
const DEFAULT_SORT: OperationSort = "-date";
const FALLBACK_TIME_ZONE = "UTC";
const DEFAULT_CURRENCY = "RUB";
const ACCOUNTS_ROUTE = { name: "accounts" };
const CANCEL_BUTTON = { label: "Отмена", severity: "secondary", outlined: true };

function createEmptyFilters(): OperationFilterValues {
    return {
        dateFrom: null,
        dateTo: null,
        accountId: null,
        categoryId: null,
        kind: null,
    };
}

const session = useSessionStore();
const confirm = useConfirm();
const { notifyError, notifySuccess } = useNotifier();
const accountsQuery = useAccountsQuery();
const categoriesQuery = useCategoriesQuery();
const { deleteMutation } = useOperationMutations();

const filters = ref<OperationFilterValues>(createEmptyFilters());
const page = ref(FIRST_PAGE);
const pageSize = ref(DEFAULT_PAGE_SIZE);
const sort = ref<OperationSort>(DEFAULT_SORT);
const isDialogOpen = ref(false);
const editedOperation = ref<Operation | null>(null);

const listParameters = computed<OperationListParameters>(() => ({
    ...filters.value,
    page: page.value,
    pageSize: pageSize.value,
    sort: sort.value,
}));

const { data, error, isError, isFetching, isPending, refetch } = useOperationsQuery(listParameters);

const accounts = computed(() => accountsQuery.data.value?.items ?? []);
const categories = computed(() => categoriesQuery.data.value ?? []);
const operations = computed(() => data.value?.items ?? []);
const totalCount = computed(() => data.value?.count ?? 0);
const firstRowIndex = computed(() => (page.value - FIRST_PAGE) * pageSize.value);
const timeZone = computed(() => session.currentUser?.timeZone ?? FALLBACK_TIME_ZONE);
const isReferenceLoading = computed(() => accountsQuery.isPending.value || categoriesQuery.isPending.value);
const isFirstLoad = computed(() => isPending.value || isReferenceLoading.value);
const isLoadingVisible = useDelayedFlag(isFirstLoad);
const hasAccounts = computed(() => accounts.value.length > 0);
const hasActiveFilters = computed(() => Object.values(filters.value).some((value) => value !== null));
const hasOperations = computed(() => totalCount.value > 0);
const loadError = computed(() => error.value ?? accountsQuery.error.value ?? categoriesQuery.error.value);
const hasLoadError = computed(() => isError.value || accountsQuery.isError.value || categoriesQuery.isError.value);
const loadErrorText = computed(() => describeError(loadError.value));

// Новый фильтр показывает подборку с первой страницы
watch(
    filters,
    () => {
        page.value = FIRST_PAGE;
    },
    { deep: true },
);

// Если удалили последнюю строку последней страницы, показывается предыдущая
watch(data, (currentPage) => {
    const isPageBeyondEnd = currentPage !== undefined && currentPage.items.length === 0 && page.value > FIRST_PAGE;

    if (isPageBeyondEnd) {
        page.value -= 1;
    }
});

function resetFilters(): void {
    filters.value = createEmptyFilters();
}

function changePage(nextPage: number, rowsPerPage: number): void {
    page.value = nextPage;
    pageSize.value = rowsPerPage;
}

function changeSort(nextSort: OperationSort): void {
    sort.value = nextSort;
    page.value = FIRST_PAGE;
}

function openCreateDialog(): void {
    editedOperation.value = null;
    isDialogOpen.value = true;
}

function openEditDialog(operation: Operation): void {
    editedOperation.value = operation;
    isDialogOpen.value = true;
}

function retryLoading(): void {
    void refetch();
    void accountsQuery.refetch();
    void categoriesQuery.refetch();
}

async function removeOperation(operation: Operation): Promise<void> {
    try {
        await deleteMutation.mutateAsync(operation.id);
        notifySuccess("Операция удалена");
    } catch (removalError) {
        notifyError(removalError);
    }
}

function confirmRemoval(operation: Operation): void {
    const currencyCode = accounts.value.find((account) => account.id === operation.accountId)?.currency ?? DEFAULT_CURRENCY;
    const amountText = formatOperationAmount(operation.kind, operation.amount, currencyCode);

    confirm.require({
        header: "Удалить операцию?",
        message: `Операция от ${operation.date} на ${amountText} будет удалена без возможности восстановления`,
        acceptProps: { label: "Удалить операцию", severity: "danger" },
        rejectProps: CANCEL_BUTTON,
        defaultFocus: "reject",
        accept: () => void removeOperation(operation),
    });
}
</script>

<template>
    <div class="operations-page">
        <header class="page-heading">
            <h1 class="page-heading__title">Операции</h1>
            <Button label="Добавить операцию" :disabled="!hasAccounts" @click="openCreateDialog" />
        </header>

        <div v-if="isFirstLoad" class="operations-page__loading" :aria-busy="true" aria-label="Загрузка операций">
            <Skeleton v-if="isLoadingVisible" height="20rem" border-radius="0.875rem" />
        </div>

        <div v-else-if="hasLoadError" class="state-card">
            <Message severity="error" :closable="false">{{ loadErrorText }}</Message>
            <Button label="Повторить" severity="secondary" outlined @click="retryLoading" />
        </div>

        <div v-else-if="!hasAccounts" class="state-card">
            <p class="state-card__title">Сначала добавьте счёт</p>
            <p class="state-card__text">Доход или расход записывается на счёт, а счетов пока нет</p>
            <RouterLink :to="ACCOUNTS_ROUTE">Перейти к счетам</RouterLink>
        </div>

        <template v-else>
            <OperationFilters
                v-model:filters="filters"
                :accounts="accounts"
                :categories="categories"
                :has-active-filters="hasActiveFilters"
                @reset="resetFilters"
            />

            <div v-if="!hasOperations && !hasActiveFilters" class="state-card">
                <p class="state-card__title">Операций пока нет</p>
                <p class="state-card__text">Запишите первый доход или расход, баланс счёта пересчитается сам</p>
                <Button label="Добавить операцию" @click="openCreateDialog" />
            </div>

            <div v-else-if="!hasOperations" class="state-card">
                <p class="state-card__title">Ничего не найдено</p>
                <p class="state-card__text">По выбранным условиям операций нет</p>
                <Button label="Сбросить фильтры" severity="secondary" outlined @click="resetFilters" />
            </div>

            <OperationsTable
                v-else
                :operations="operations"
                :total-count="totalCount"
                :first-row-index="firstRowIndex"
                :rows-per-page="pageSize"
                :sort="sort"
                :is-loading="isFetching"
                :accounts="accounts"
                :categories="categories"
                @page="changePage"
                @sort="changeSort"
                @edit="openEditDialog"
                @remove="confirmRemoval"
            />
        </template>

        <OperationDialog
            v-model:visible="isDialogOpen"
            :operation="editedOperation"
            :accounts="accounts"
            :categories="categories"
            :time-zone="timeZone"
        />
    </div>
</template>

<style scoped>
.operations-page {
    display: grid;
    gap: 1.5rem;
}

.operations-page .page-heading {
    margin-bottom: 0;
}
</style>
