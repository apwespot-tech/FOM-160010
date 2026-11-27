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
import { useBusyIds } from "../composables/useBusyIds";
import { useCategoriesQuery } from "../composables/useCategories";
import { useDelayedFlag } from "../composables/useDelayedFlag";
import { useNotifier } from "../composables/useNotifier";
import { useOperationMutations, useOperationsQuery } from "../composables/useOperations";
import { describeError } from "../services/apiClient";
import { useSessionStore } from "../stores/session";
import type { Operation, OperationFilters as OperationFilterValues, OperationListParameters, OperationSort } from "../types/ledger";
import { formatOperationAmount } from "../utils/ledgerLabels";
import { DEFAULT_GROUPING_DIGITS } from "../utils/money";
import type { MoneyFormatOptions } from "../utils/money";

const DEFAULT_PAGE_SIZE = 20;
const FIRST_PAGE = 1;
const DEFAULT_SORT: OperationSort = "-date";
const FALLBACK_TIME_ZONE = "UTC";
const DEFAULT_CURRENCY = "RUB";
const ACCOUNTS_ROUTE = { name: "accounts" };
const CANCEL_BUTTON = { label: "Отмена", severity: "secondary", outlined: true };
const STALE_DATA_TEXT = "Список не обновился, на экране прежние данные";
// В тексте подтверждения сумма пишется как в предложении: четырёхзначные числа слитно, в отличие от столбца таблицы
const SENTENCE_MONEY_FORMAT: MoneyFormatOptions = { groupingDigits: DEFAULT_GROUPING_DIGITS };

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
const { busyIds: busyOperationIds, markBusy, releaseBusy } = useBusyIds();

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
const hasAccounts = computed(() => accounts.value.length > 0);
const hasActiveAccounts = computed(() => accounts.value.some((account) => !account.isArchived));
const hasActiveFilters = computed(() => Object.values(filters.value).some((value) => value !== null));
const hasOperations = computed(() => totalCount.value > 0);

// Счета и категории нужны и фильтрам, и таблице, поэтому без них страница ждёт целиком, а список операций ждёт отдельно
const isReferenceLoading = computed(() => accountsQuery.isPending.value || categoriesQuery.isPending.value);
const isReferenceLoadingVisible = useDelayedFlag(isReferenceLoading);
const isOperationsLoadingVisible = useDelayedFlag(isPending);
// Затемнение таблицы ждёт 400 мс, как и другие индикаторы, и держится, пока удаляется строка
const isTableBusy = computed(() => isFetching.value || deleteMutation.isPending.value);
const isTableBusyVisible = useDelayedFlag(isTableBusy);

// Сорвавшееся фоновое обновление не прячет уже загруженные данные: они остаются на экране с пометкой
const hasReferenceData = computed(() => accountsQuery.data.value !== undefined && categoriesQuery.data.value !== undefined);
const hasReferenceError = computed(() => accountsQuery.isError.value || categoriesQuery.isError.value);
const hasReferenceLoadError = computed(() => hasReferenceError.value && !hasReferenceData.value);
const hasOperationsLoadError = computed(() => isError.value && data.value === undefined);

const hasRefreshError = computed(() => {
    const hasStaleReferences = hasReferenceError.value && hasReferenceData.value;
    const hasStaleOperations = isError.value && data.value !== undefined;

    return hasStaleReferences || hasStaleOperations;
});

const loadError = computed(() => error.value ?? accountsQuery.error.value ?? categoriesQuery.error.value);
const loadErrorText = computed(() => describeError(loadError.value));
const refreshErrorText = computed(() => `${STALE_DATA_TEXT}. ${loadErrorText.value}`);

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
    markBusy(operation.id);

    try {
        await deleteMutation.mutateAsync(operation.id);
        notifySuccess("Операция удалена");
    } catch (removalError) {
        notifyError(removalError);
    } finally {
        releaseBusy(operation.id);
    }
}

function confirmRemoval(operation: Operation): void {
    const currencyCode = accounts.value.find((account) => account.id === operation.accountId)?.currency ?? DEFAULT_CURRENCY;
    const amountText = formatOperationAmount(operation.kind, operation.amount, currencyCode, SENTENCE_MONEY_FORMAT);

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
            <Button label="Добавить операцию" :disabled="!hasActiveAccounts" @click="openCreateDialog" />
        </header>

        <div v-if="isReferenceLoading" class="operations-page__loading" :aria-busy="true" aria-label="Загрузка операций">
            <Skeleton v-if="isReferenceLoadingVisible" height="20rem" border-radius="0.875rem" />
        </div>

        <div v-else-if="hasReferenceLoadError" class="state-card">
            <Message severity="error" :closable="false">{{ loadErrorText }}</Message>
            <Button label="Повторить" severity="secondary" outlined @click="retryLoading" />
        </div>

        <div v-else-if="!hasAccounts" class="state-card">
            <p class="state-card__title">Сначала добавьте счёт</p>
            <p class="state-card__text">Доход или расход записывается на счёт, а счетов пока нет</p>
            <RouterLink :to="ACCOUNTS_ROUTE">Перейти к счетам</RouterLink>
        </div>

        <template v-else>
            <Message v-if="!hasActiveAccounts" severity="info" :closable="false">
                <div class="inline-notice">
                    <span>Все счета в архиве. Чтобы записать операцию, верните счёт из архива</span>
                    <RouterLink :to="ACCOUNTS_ROUTE">Перейти к счетам</RouterLink>
                </div>
            </Message>

            <Message v-if="hasRefreshError" severity="warn" :closable="false">
                <div class="inline-notice">
                    <span>{{ refreshErrorText }}</span>
                    <Button label="Повторить" size="small" severity="secondary" outlined @click="retryLoading" />
                </div>
            </Message>

            <OperationFilters
                v-model:filters="filters"
                :accounts="accounts"
                :categories="categories"
                :has-active-filters="hasActiveFilters"
                @reset="resetFilters"
            />

            <div v-if="isPending" class="operations-page__loading" :aria-busy="true" aria-label="Загрузка операций">
                <Skeleton v-if="isOperationsLoadingVisible" height="20rem" border-radius="0.875rem" />
            </div>

            <div v-else-if="hasOperationsLoadError" class="state-card">
                <Message severity="error" :closable="false">{{ loadErrorText }}</Message>
                <Button label="Повторить" severity="secondary" outlined @click="retryLoading" />
            </div>

            <div v-else-if="!hasOperations && !hasActiveFilters" class="state-card">
                <p class="state-card__title">Операций пока нет</p>
                <p class="state-card__text">Запишите первый доход или расход, баланс счёта пересчитается сам</p>
                <Button label="Добавить операцию" :disabled="!hasActiveAccounts" @click="openCreateDialog" />
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
                :is-loading="isTableBusyVisible"
                :accounts="accounts"
                :categories="categories"
                :busy-operation-ids="busyOperationIds"
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
