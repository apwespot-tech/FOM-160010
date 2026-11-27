<script setup lang="ts">
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import Select from "primevue/select";
import { computed, ref } from "vue";

import type { Account, Category, OperationFilters } from "../types/ledger";
import { isoDateToLocalDate, localDateToIsoDate } from "../utils/dates";
import { CATEGORY_KIND_LABELS, OPERATION_KIND_OPTIONS } from "../utils/ledgerLabels";

interface OptionGroup {
    label: string;
    items: Array<{ value: number; label: string }>;
}

const DATE_FROM_INPUT_ID = "filter-date-from";
const DATE_TO_INPUT_ID = "filter-date-to";
const ACCOUNT_INPUT_ID = "filter-account";
const CATEGORY_INPUT_ID = "filter-category";
const KIND_INPUT_ID = "filter-kind";

const props = defineProps<{
    accounts: Account[];
    categories: Category[];
    hasActiveFilters: boolean;
}>();

const filters = defineModel<OperationFilters>("filters", { required: true });

const emit = defineEmits<{
    reset: [];
}>();

// На узком экране панель свёрнута, чтобы таблица не уходила далеко вниз
const isExpanded = ref(false);
const panelClasses = computed(() => ({ "operation-filters--expanded": isExpanded.value }));
const toggleLabel = computed(() => (props.hasActiveFilters ? "Фильтры: заданы" : "Фильтры"));

function toggleFilters(): void {
    isExpanded.value = !isExpanded.value;
}

const accountOptions = computed(() => props.accounts.map((account) => ({ value: account.id, label: account.name })));

// Категории сгруппированы по виду: у дохода и расхода могут быть одинаковые названия
const categoryGroups = computed<OptionGroup[]>(() => {
    const expenseItems = props.categories.filter((category) => category.kind === "expense");
    const incomeItems = props.categories.filter((category) => category.kind === "income");

    return [
        { label: CATEGORY_KIND_LABELS.expense, items: expenseItems.map((category) => ({ value: category.id, label: category.name })) },
        { label: CATEGORY_KIND_LABELS.income, items: incomeItems.map((category) => ({ value: category.id, label: category.name })) },
    ];
});

function toLocalDate(isoDate: string | null): Date | null {
    if (isoDate === null) {
        return null;
    }

    return isoDateToLocalDate(isoDate);
}

function toIsoDate(localDate: Date | null | undefined): string | null {
    if (localDate === null || localDate === undefined) {
        return null;
    }

    return localDateToIsoDate(localDate);
}

function updateFilters(changes: Partial<OperationFilters>): void {
    filters.value = { ...filters.value, ...changes };
}

const dateFrom = computed<Date | null>({
    get() {
        return toLocalDate(filters.value.dateFrom);
    },
    set(value) {
        updateFilters({ dateFrom: toIsoDate(value) });
    },
});

const dateTo = computed<Date | null>({
    get() {
        return toLocalDate(filters.value.dateTo);
    },
    set(value) {
        updateFilters({ dateTo: toIsoDate(value) });
    },
});

const accountId = computed<number | null>({
    get() {
        return filters.value.accountId;
    },
    set(value) {
        updateFilters({ accountId: value ?? null });
    },
});

const categoryId = computed<number | null>({
    get() {
        return filters.value.categoryId;
    },
    set(value) {
        updateFilters({ categoryId: value ?? null });
    },
});

const kind = computed<OperationFilters["kind"]>({
    get() {
        return filters.value.kind;
    },
    set(value) {
        updateFilters({ kind: value ?? null });
    },
});

function requestReset(): void {
    emit("reset");
}
</script>

<template>
    <section class="operation-filters" :class="panelClasses" aria-label="Фильтры операций">
        <button
            class="operation-filters__toggle"
            type="button"
            aria-controls="operation-filter-fields"
            :aria-expanded="isExpanded"
            @click="toggleFilters"
        >
            {{ toggleLabel }}
        </button>

        <div id="operation-filter-fields" class="operation-filters__fields">
            <div class="operation-filters__field">
                <label :for="DATE_FROM_INPUT_ID">С даты</label>
                <DatePicker
                    v-model="dateFrom"
                    :input-id="DATE_FROM_INPUT_ID"
                    date-format="yy-mm-dd"
                    :max-date="dateTo ?? undefined"
                    show-button-bar
                    fluid
                />
            </div>

            <div class="operation-filters__field">
                <label :for="DATE_TO_INPUT_ID">По дату</label>
                <DatePicker
                    v-model="dateTo"
                    :input-id="DATE_TO_INPUT_ID"
                    date-format="yy-mm-dd"
                    :min-date="dateFrom ?? undefined"
                    show-button-bar
                    fluid
                />
            </div>

            <div class="operation-filters__field">
                <label :for="ACCOUNT_INPUT_ID">Счёт</label>
                <Select
                    v-model="accountId"
                    :input-id="ACCOUNT_INPUT_ID"
                    :options="accountOptions"
                    option-label="label"
                    option-value="value"
                    placeholder="Все счета"
                    show-clear
                    fluid
                />
            </div>

            <div class="operation-filters__field">
                <label :for="CATEGORY_INPUT_ID">Категория</label>
                <Select
                    v-model="categoryId"
                    :input-id="CATEGORY_INPUT_ID"
                    :options="categoryGroups"
                    option-label="label"
                    option-value="value"
                    option-group-label="label"
                    option-group-children="items"
                    placeholder="Все категории"
                    filter
                    filter-placeholder="Поиск категории"
                    show-clear
                    fluid
                />
            </div>

            <div class="operation-filters__field">
                <label :for="KIND_INPUT_ID">Вид</label>
                <Select
                    v-model="kind"
                    :input-id="KIND_INPUT_ID"
                    :options="OPERATION_KIND_OPTIONS"
                    option-label="label"
                    option-value="value"
                    placeholder="Все виды"
                    show-clear
                    fluid
                />
            </div>

            <div class="operation-filters__actions">
                <Button label="Сбросить" severity="secondary" outlined :disabled="!hasActiveFilters" @click="requestReset" />
            </div>
        </div>
    </section>
</template>

<style scoped>
.operation-filters {
    min-width: 0;
    padding: 1rem 1.125rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-large);
    background: var(--color-surface);
}

.operation-filters__fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    align-items: end;
    gap: 0.875rem 1rem;
}

.operation-filters__toggle {
    display: none;
}

.operation-filters__field {
    display: grid;
    gap: 0.375rem;
    min-width: 0;
}

.operation-filters__field label {
    font-size: 0.875rem;
    font-weight: 600;
}

.operation-filters__actions {
    display: flex;
}

@media (max-width: 40rem) {
    .operation-filters__toggle {
        display: flex;
        align-items: center;
        width: 100%;
        min-height: 2.5rem;
        padding: 0;
        border: 0;
        background: transparent;
        color: var(--color-text);
        font: inherit;
        font-weight: 600;
        cursor: pointer;
    }

    .operation-filters__toggle:focus-visible {
        outline: none;
        border-radius: var(--radius-medium);
        box-shadow: var(--focus-ring);
    }

    .operation-filters__fields {
        display: none;
        margin-top: 0.75rem;
    }

    .operation-filters--expanded .operation-filters__fields {
        display: grid;
    }
}
</style>
