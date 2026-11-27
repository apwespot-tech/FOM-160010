<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import type { DataTablePageEvent, DataTableSortEvent } from "primevue/datatable";
import { computed } from "vue";

import type { Account, Category, Operation, OperationSort } from "../types/ledger";
import { formatOperationAmount, isDecreasingKind, OPERATION_KIND_LABELS } from "../utils/ledgerLabels";

const DEFAULT_CURRENCY = "RUB";
const DATE_FIELD = "date";
const ASCENDING_ORDER = 1;
const DESCENDING_ORDER = -1;
const ROWS_PER_PAGE_OPTIONS = [20, 50, 100];
const TRANSFER_NOTE = "Часть перевода, меняется вместе с переводом";
const MISSING_NAME = "нет данных";

const props = defineProps<{
    operations: Operation[];
    totalCount: number;
    firstRowIndex: number;
    rowsPerPage: number;
    sort: OperationSort;
    isLoading: boolean;
    accounts: Account[];
    categories: Category[];
}>();

const emit = defineEmits<{
    page: [page: number, rowsPerPage: number];
    sort: [sort: OperationSort];
    edit: [operation: Operation];
    remove: [operation: Operation];
}>();

const accountsById = computed(() => new Map(props.accounts.map((account) => [account.id, account])));
const categoriesById = computed(() => new Map(props.categories.map((category) => [category.id, category])));
const sortOrder = computed(() => (props.sort === "date" ? ASCENDING_ORDER : DESCENDING_ORDER));

function readAccountName(operation: Operation): string {
    return accountsById.value.get(operation.accountId)?.name ?? MISSING_NAME;
}

function readCategoryName(operation: Operation): string {
    if (operation.categoryId === null) {
        return OPERATION_KIND_LABELS[operation.kind];
    }

    return categoriesById.value.get(operation.categoryId)?.name ?? MISSING_NAME;
}

function readAmountText(operation: Operation): string {
    const currencyCode = accountsById.value.get(operation.accountId)?.currency ?? DEFAULT_CURRENCY;

    return formatOperationAmount(operation.kind, operation.amount, currencyCode);
}

function readAmountClass(operation: Operation): string {
    if (isDecreasingKind(operation.kind)) {
        return "operations-table__amount";
    }

    return "operations-table__amount operations-table__amount--income";
}

function isTransferPart(operation: Operation): boolean {
    return operation.transferId !== null;
}

function describeOperation(operation: Operation): string {
    return `${readCategoryName(operation)} от ${operation.date} на ${readAmountText(operation)}`;
}

function readEditLabel(operation: Operation): string {
    return `Изменить операцию: ${describeOperation(operation)}`;
}

function readRemovalLabel(operation: Operation): string {
    return `Удалить операцию: ${describeOperation(operation)}`;
}

function changePage(event: DataTablePageEvent): void {
    emit("page", event.page + 1, event.rows);
}

function changeSort(event: DataTableSortEvent): void {
    emit("sort", event.sortOrder === ASCENDING_ORDER ? "date" : "-date");
}

function requestEdit(operation: Operation): void {
    emit("edit", operation);
}

function requestRemoval(operation: Operation): void {
    emit("remove", operation);
}
</script>

<template>
    <DataTable
        class="operations-table"
        :value="operations"
        data-key="id"
        lazy
        paginator
        :rows="rowsPerPage"
        :rows-per-page-options="ROWS_PER_PAGE_OPTIONS"
        :first="firstRowIndex"
        :total-records="totalCount"
        :loading="isLoading"
        :sort-field="DATE_FIELD"
        :sort-order="sortOrder"
        :always-show-paginator="false"
        :removable-sort="false"
        @page="changePage"
        @sort="changeSort"
    >
        <Column
            :field="DATE_FIELD"
            header="Дата"
            sortable
            header-class="operations-table__date operations-table__wide"
            body-class="operations-table__date operations-table__wide money"
        />

        <Column header="Категория">
            <template #body="{ data }">
                <div class="operations-table__category">
                    <span>{{ readCategoryName(data) }}</span>
                    <span class="operations-table__details money">{{ data.date }}</span>
                    <span class="operations-table__details">{{ readAccountName(data) }}</span>
                    <span v-if="data.note" class="operations-table__details operations-table__note-line" :title="data.note">{{ data.note }}</span>
                </div>
            </template>
        </Column>

        <Column header="Счёт" header-class="operations-table__wide" body-class="operations-table__wide">
            <template #body="{ data }">{{ readAccountName(data) }}</template>
        </Column>

        <Column header="Заметка" header-class="operations-table__wide" body-class="operations-table__wide operations-table__note">
            <template #body="{ data }">
                <span :title="data.note">{{ data.note }}</span>
            </template>
        </Column>

        <Column header="Сумма" header-class="operations-table__amount-header" body-class="operations-table__amount-cell">
            <template #body="{ data }">
                <span :class="readAmountClass(data)">{{ readAmountText(data) }}</span>
            </template>
        </Column>

        <Column header-class="operations-table__actions-header">
            <template #header>
                <span class="visually-hidden">Действия</span>
            </template>
            <template #body="{ data }">
                <div v-if="isTransferPart(data)" class="operations-table__transfer" :title="TRANSFER_NOTE">Перевод</div>
                <div v-else class="operations-table__actions">
                    <Button
                        severity="secondary"
                        text
                        rounded
                        size="small"
                        :aria-label="readEditLabel(data)"
                        title="Изменить"
                        @click="requestEdit(data)"
                    >
                        <template #icon>
                            <svg class="operations-table__icon" viewBox="0 0 16 16" aria-hidden="true">
                                <path d="M10.5 2.5l3 3L6 13H3v-3z" />
                            </svg>
                        </template>
                    </Button>
                    <Button
                        severity="danger"
                        text
                        rounded
                        size="small"
                        :aria-label="readRemovalLabel(data)"
                        title="Удалить"
                        @click="requestRemoval(data)"
                    >
                        <template #icon>
                            <svg class="operations-table__icon" viewBox="0 0 16 16" aria-hidden="true">
                                <path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.75 8.5h5.5l.75-8.5" />
                            </svg>
                        </template>
                    </Button>
                </div>
            </template>
        </Column>
    </DataTable>
</template>

<style scoped>
/* Без min-width: 0 таблица растянула бы сетку страницы шире экрана, а широкие строки прокручиваются внутри таблицы */
.operations-table {
    min-width: 0;
}

.operations-table :deep(.p-datatable-table-container) {
    overflow-x: auto;
}

.operations-table :deep(td) {
    vertical-align: middle;
}

.operations-table :deep(.operations-table__date) {
    width: 8rem;
    white-space: nowrap;
}

.operations-table__category {
    display: grid;
    gap: 0.125rem;
    min-width: 0;
}

.operations-table__details {
    display: none;
    color: var(--color-text-secondary);
    font-size: 0.8125rem;
}

.operations-table :deep(.operations-table__note) {
    max-width: 16rem;
}

.operations-table :deep(.operations-table__note) span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.operations-table__note-line {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.operations-table :deep(.operations-table__amount-header) .p-datatable-column-header-content {
    justify-content: flex-end;
}

.operations-table :deep(.operations-table__amount-cell) {
    text-align: right;
}

.operations-table__amount {
    font-feature-settings: "tnum";
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    white-space: nowrap;
}

.operations-table__amount--income {
    color: var(--color-success);
}

.operations-table :deep(.operations-table__actions-header) {
    width: 5.5rem;
}

.operations-table__actions {
    display: flex;
    gap: 0.25rem;
}

.operations-table__transfer {
    color: var(--color-text-secondary);
    font-size: 0.8125rem;
}

.operations-table__icon {
    width: 1rem;
    height: 1rem;
    flex-shrink: 0;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
    stroke-linecap: round;
    stroke-linejoin: round;
}

@media (max-width: 40rem) {
    .operations-table :deep(.operations-table__wide) {
        display: none;
    }

    .operations-table__details {
        display: block;
    }

    .operations-table :deep(.operations-table__date) {
        width: auto;
    }

    .operations-table :deep(.p-datatable-tbody > tr > td),
    .operations-table :deep(.p-datatable-thead > tr > th) {
        padding: 0.625rem 0.25rem;
    }

    .operations-table__note-line {
        max-width: 8rem;
    }

    .operations-table__amount {
        font-size: 0.9375rem;
    }

    .operations-table__actions {
        gap: 0;
    }

    .operations-table :deep(.operations-table__actions-header) {
        width: auto;
    }
}
</style>
