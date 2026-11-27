<script setup lang="ts">
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import { computed, reactive, ref, watch } from "vue";

import FormField from "./FormField.vue";
import { useFieldErrors } from "../composables/useFieldErrors";
import { useNotifier } from "../composables/useNotifier";
import { useOperationMutations } from "../composables/useOperations";
import { ApiError, describeError } from "../services/apiClient";
import type { Account, Category, CategoryKind, Operation } from "../types/ledger";
import { isoDateToLocalDate, localDateToIsoDate, readTodayInTimeZone } from "../utils/dates";
import { CATEGORY_KIND_LABELS } from "../utils/ledgerLabels";
import { normalizeAmountInput } from "../utils/money";

interface OperationForm {
    kind: CategoryKind;
    accountId: number | null;
    categoryId: number | null;
    amount: string;
    date: Date | null;
    note: string;
}

interface SelectOption {
    value: number;
    label: string;
}

const NOTE_MAX_LENGTH = 255;
const ZERO_AMOUNT = "0.00";
const DEFAULT_KIND: CategoryKind = "expense";

const KIND_OPTIONS = [
    { value: "expense", label: "Расход" },
    { value: "income", label: "Доход" },
];

const ACCOUNT_INPUT_ID = "operation-account";
const CATEGORY_INPUT_ID = "operation-category";
const AMOUNT_INPUT_ID = "operation-amount";
const DATE_INPUT_ID = "operation-date";
const NOTE_INPUT_ID = "operation-note";
const DATE_HINT = "Не позже сегодняшнего дня. Будущие платежи заводятся периодическими правилами";

const props = defineProps<{
    operation: Operation | null;
    accounts: Account[];
    categories: Category[];
    timeZone: string;
}>();

const isVisible = defineModel<boolean>("visible", { required: true });

const { createMutation, updateMutation } = useOperationMutations();
const { notifySuccess } = useNotifier();
const { clearFieldErrors, describeInput, fieldErrors, hasFieldErrors, replaceFieldErrors, setFieldError } = useFieldErrors();

const form = reactive<OperationForm>({
    kind: DEFAULT_KIND,
    accountId: null,
    categoryId: null,
    amount: "",
    date: null,
    note: "",
});

const formError = ref("");

const isEditing = computed(() => props.operation !== null);
const header = computed(() => (isEditing.value ? "Изменить операцию" : "Новая операция"));
const isSaving = computed(() => createMutation.isPending.value || updateMutation.isPending.value);
const saveLabel = computed(() => (isSaving.value ? "Сохранение…" : "Сохранить"));
const kindFact = computed(() => `Вид: ${CATEGORY_KIND_LABELS[form.kind]}. Вид после создания не меняется`);
const maxDate = computed(() => isoDateToLocalDate(readTodayInTimeZone(props.timeZone)) ?? undefined);
const amountDescription = computed(() => describeInput(AMOUNT_INPUT_ID, "amount"));
const noteDescription = computed(() => describeInput(NOTE_INPUT_ID, "note"));

// Архивный счёт нельзя выбрать заново, но уже записанная на нём операция остаётся на нём
const accountOptions = computed<SelectOption[]>(() => {
    const currentAccountId = props.operation?.accountId ?? null;
    const selectableAccounts = props.accounts.filter((account) => !account.isArchived || account.id === currentAccountId);

    return selectableAccounts.map((account) => ({ value: account.id, label: describeAccount(account) }));
});

const categoryOptions = computed<SelectOption[]>(() => {
    const suitableCategories = props.categories.filter((category) => category.kind === form.kind);

    return suitableCategories.map((category) => ({ value: category.id, label: category.name }));
});

function describeAccount(account: Account): string {
    if (account.isArchived) {
        return `${account.name} (в архиве)`;
    }

    return account.name;
}

function chooseDefaultAccountId(): number | null {
    const activeAccounts = props.accounts.filter((account) => !account.isArchived);

    // Единственный счёт подставляется сам, из нескольких пользователь выбирает явно
    if (activeAccounts.length === 1) {
        return activeAccounts[0].id;
    }

    return null;
}

function resetForm(): void {
    const operation = props.operation;
    const todayDate = isoDateToLocalDate(readTodayInTimeZone(props.timeZone));

    form.kind = operation === null ? DEFAULT_KIND : (operation.kind as CategoryKind);
    form.accountId = operation?.accountId ?? chooseDefaultAccountId();
    form.categoryId = operation?.categoryId ?? null;
    form.amount = operation?.amount ?? "";
    form.date = operation === null ? todayDate : isoDateToLocalDate(operation.date);
    form.note = operation?.note ?? "";
    formError.value = "";
    clearFieldErrors();
}

watch(
    isVisible,
    (isOpen) => {
        if (isOpen) {
            resetForm();
        }
    },
    { immediate: true },
);

// Категория другого вида к операции не подходит, поэтому при смене вида выбор сбрасывается
watch(
    () => form.kind,
    () => {
        const isCategorySuitable = categoryOptions.value.some((option) => option.value === form.categoryId);

        if (!isCategorySuitable) {
            form.categoryId = null;
        }
    },
);

function checkAccount(): void {
    setFieldError("account_id", form.accountId === null ? "Выберите счёт" : null);
}

function checkCategory(): void {
    setFieldError("category_id", form.categoryId === null ? "Выберите категорию" : null);
}

function checkAmount(): void {
    const normalizedAmount = normalizeAmountInput(form.amount);

    if (normalizedAmount === null) {
        setFieldError("amount", "Введите сумму числом, например 1250.50");

        return;
    }

    setFieldError("amount", normalizedAmount === ZERO_AMOUNT ? "Сумма должна быть больше нуля" : null);
}

function checkDate(): void {
    setFieldError("date", form.date === null ? "Выберите дату" : null);
}

function checkNote(): void {
    const isTooLong = form.note.trim().length > NOTE_MAX_LENGTH;
    setFieldError("note", isTooLong ? `Заметка не длиннее ${NOTE_MAX_LENGTH} знаков` : null);
}

function checkForm(): boolean {
    checkAccount();
    checkCategory();
    checkAmount();
    checkDate();
    checkNote();

    return !hasFieldErrors();
}

function close(): void {
    isVisible.value = false;
}

function showSaveError(error: unknown): void {
    const hasServerFieldErrors = error instanceof ApiError && Object.keys(error.fieldErrors).length > 0;

    if (hasServerFieldErrors) {
        replaceFieldErrors(error.fieldErrors);

        return;
    }

    formError.value = describeError(error);
}

async function saveOperation(): Promise<void> {
    const values = {
        accountId: form.accountId as number,
        categoryId: form.categoryId as number,
        amount: normalizeAmountInput(form.amount) as string,
        date: localDateToIsoDate(form.date as Date),
        note: form.note.trim(),
    };

    if (props.operation === null) {
        await createMutation.mutateAsync({ kind: form.kind, ...values });
        notifySuccess("Операция добавлена");

        return;
    }

    await updateMutation.mutateAsync({ operationId: props.operation.id, changes: values });
    notifySuccess("Операция сохранена");
}

async function save(): Promise<void> {
    if (isSaving.value) {
        return;
    }

    formError.value = "";

    if (!checkForm()) {
        return;
    }

    try {
        await saveOperation();
        close();
    } catch (error) {
        showSaveError(error);
    }
}
</script>

<template>
    <Dialog v-model:visible="isVisible" :header="header" modal :draggable="false">
        <form class="dialog-form" novalidate @submit.prevent="save">
            <div v-if="!isEditing" class="form-field-group" role="group" aria-labelledby="operation-kind-label">
                <span id="operation-kind-label" class="operation-dialog__label">Вид</span>
                <SelectButton
                    v-model="form.kind"
                    :options="KIND_OPTIONS"
                    option-label="label"
                    option-value="value"
                    :allow-empty="false"
                    aria-labelledby="operation-kind-label"
                />
            </div>
            <p v-else class="dialog-form__fact">{{ kindFact }}</p>

            <FormField label="Счёт" :input-id="ACCOUNT_INPUT_ID" :error="fieldErrors.account_id" is-required>
                <Select
                    v-model="form.accountId"
                    :input-id="ACCOUNT_INPUT_ID"
                    :options="accountOptions"
                    option-label="label"
                    option-value="value"
                    placeholder="Выберите счёт"
                    :invalid="Boolean(fieldErrors.account_id)"
                    fluid
                    @change="checkAccount"
                />
            </FormField>

            <FormField label="Категория" :input-id="CATEGORY_INPUT_ID" :error="fieldErrors.category_id" is-required>
                <Select
                    v-model="form.categoryId"
                    :input-id="CATEGORY_INPUT_ID"
                    :options="categoryOptions"
                    option-label="label"
                    option-value="value"
                    placeholder="Выберите категорию"
                    :invalid="Boolean(fieldErrors.category_id)"
                    filter
                    filter-placeholder="Поиск категории"
                    fluid
                    @change="checkCategory"
                />
            </FormField>

            <FormField label="Сумма, ₽" :input-id="AMOUNT_INPUT_ID" :error="fieldErrors.amount" is-required>
                <InputText
                    :id="AMOUNT_INPUT_ID"
                    v-model="form.amount"
                    v-bind="amountDescription"
                    class="money"
                    inputmode="decimal"
                    autocomplete="off"
                    :invalid="Boolean(fieldErrors.amount)"
                    fluid
                    @blur="checkAmount"
                />
            </FormField>

            <FormField label="Дата" :input-id="DATE_INPUT_ID" :error="fieldErrors.date" :hint="DATE_HINT" is-required>
                <DatePicker
                    v-model="form.date"
                    :input-id="DATE_INPUT_ID"
                    date-format="yy-mm-dd"
                    :max-date="maxDate"
                    :invalid="Boolean(fieldErrors.date)"
                    show-icon
                    fluid
                    @date-select="checkDate"
                />
            </FormField>

            <FormField label="Заметка" :input-id="NOTE_INPUT_ID" :error="fieldErrors.note">
                <InputText
                    :id="NOTE_INPUT_ID"
                    v-model="form.note"
                    v-bind="noteDescription"
                    :maxlength="NOTE_MAX_LENGTH"
                    :invalid="Boolean(fieldErrors.note)"
                    fluid
                    @blur="checkNote"
                />
            </FormField>

            <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>

            <div class="dialog-form__actions">
                <Button type="submit" :label="saveLabel" :loading="isSaving" :disabled="isSaving" />
                <Button type="button" label="Отмена" severity="secondary" outlined :disabled="isSaving" @click="close" />
            </div>
        </form>
    </Dialog>
</template>

<style scoped>
.form-field-group {
    display: grid;
    gap: 0.375rem;
}

.operation-dialog__label {
    font-size: 0.875rem;
    font-weight: 600;
}
</style>
