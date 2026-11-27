<script setup lang="ts">
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import type { SelectButtonPassThroughOptions } from "primevue/selectbutton";
import type { ToggleButtonPassThroughMethodOptions } from "primevue/togglebutton";
import { computed, reactive, ref, watch } from "vue";

import FormField from "./FormField.vue";
import { useDelayedFlag } from "../composables/useDelayedFlag";
import { useFieldErrors } from "../composables/useFieldErrors";
import { useNotifier } from "../composables/useNotifier";
import { useOperationMutations } from "../composables/useOperations";
import { ApiError, describeError } from "../services/apiClient";
import type { Account, Category, CategoryKind, Operation, OperationValues } from "../types/ledger";
import { isoDateToLocalDate, localDateToIsoDate, readTodayInTimeZone } from "../utils/dates";
import { buildCloseButtonProps } from "../utils/dialogs";
import { buildLabelId } from "../utils/formIds";
import { collectOperationChanges } from "../utils/ledgerChanges";
import { CATEGORY_KIND_LABELS, CATEGORY_KIND_OPTIONS, isCategoryKind } from "../utils/ledgerLabels";
import { isZeroAmount, normalizeAmountInput } from "../utils/money";

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
const DEFAULT_KIND: CategoryKind = "expense";
const KIND_LABEL_ID = "operation-kind-label";
const ACCOUNT_INPUT_ID = "operation-account";
const ACCOUNT_LABEL_ID = buildLabelId(ACCOUNT_INPUT_ID);
const CATEGORY_INPUT_ID = "operation-category";
const CATEGORY_LABEL_ID = buildLabelId(CATEGORY_INPUT_ID);
const AMOUNT_INPUT_ID = "operation-amount";
const DATE_INPUT_ID = "operation-date";
const NOTE_INPUT_ID = "operation-note";
const DATE_HINT = "Не позже сегодняшнего дня. Будущие платежи заводятся периодическими правилами";
const AMOUNT_FORMAT_TEXT = "Введите сумму числом, например 1250.50";
const AMOUNT_NOT_POSITIVE_TEXT = "Сумма должна быть больше нуля";
const NOTE_TOO_LONG_TEXT = `Заметка не длиннее ${NOTE_MAX_LENGTH} знаков`;

// Диалог ставит фокус на первый элемент с autofocus. У выбора вида это нажатая кнопка, иначе фокус попал бы на крестик закрытия
function markPressedKindButton(options: ToggleButtonPassThroughMethodOptions): { autofocus: boolean } {
    return { autofocus: options.props.modelValue === true };
}

const KIND_PASS_THROUGH: SelectButtonPassThroughOptions = { pcToggleButton: { root: markPressedKindButton } };

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
const todayDate = ref<Date | null>(null);

const isEditing = computed(() => props.operation !== null);
const header = computed(() => (isEditing.value ? "Изменить операцию" : "Новая операция"));
const isSaving = computed(() => createMutation.isPending.value || updateMutation.isPending.value);
const isSavingVisible = useDelayedFlag(isSaving);
const saveLabel = computed(() => (isSavingVisible.value ? "Сохранение…" : "Сохранить"));
const closeButtonProps = computed(() => buildCloseButtonProps(isSaving.value));
const kindFact = computed(() => `Вид: ${CATEGORY_KIND_LABELS[form.kind]}. Вид после создания не меняется`);
const maxDate = computed(() => todayDate.value ?? undefined);
const amountDescription = computed(() => describeInput(AMOUNT_INPUT_ID, "amount", { isRequired: true }));
const noteDescription = computed(() => describeInput(NOTE_INPUT_ID, "note"));

// Поля выбора и календарь PrimeVue передают связи с подсказкой и ошибкой своему фокусируемому элементу через pass-through.
// При правке первым идёт счёт, поэтому фокус при открытии ставится на него
const accountPassThrough = computed(() => ({
    label: { ...describeInput(ACCOUNT_INPUT_ID, "account_id", { isRequired: true }), autofocus: isEditing.value },
}));

const categoryPassThrough = computed(() => ({ label: describeInput(CATEGORY_INPUT_ID, "category_id", { isRequired: true }) }));
const datePassThrough = computed(() => ({ pcInputText: { root: describeInput(DATE_INPUT_ID, "date", { hasHint: true, isRequired: true }) } }));

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

// Части перевода в этом диалоге не правятся, поэтому вид операции здесь всегда доход или расход
function readFormKind(operation: Operation | null): CategoryKind {
    if (operation !== null && isCategoryKind(operation.kind)) {
        return operation.kind;
    }

    return DEFAULT_KIND;
}

function resetForm(): void {
    const operation = props.operation;

    // Сегодняшний день пересчитывается при каждом открытии: вкладка могла пролежать открытой с вечера
    todayDate.value = isoDateToLocalDate(readTodayInTimeZone(props.timeZone));
    form.kind = readFormKind(operation);
    form.accountId = operation?.accountId ?? chooseDefaultAccountId();
    form.categoryId = operation?.categoryId ?? null;
    form.amount = operation?.amount ?? "";
    form.date = operation === null ? todayDate.value : isoDateToLocalDate(operation.date);
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
    const normalizedAmount = normalizeAmountInput(form.amount, true);

    if (normalizedAmount === null) {
        setFieldError("amount", AMOUNT_FORMAT_TEXT);

        return;
    }

    // Сумма с минусом записана верно, но не подходит: доход от расхода отличает вид, а не знак
    const isPositive = !normalizedAmount.startsWith("-") && !isZeroAmount(normalizedAmount);

    setFieldError("amount", isPositive ? null : AMOUNT_NOT_POSITIVE_TEXT);
}

function checkDate(): void {
    setFieldError("date", form.date === null ? "Выберите дату" : null);
}

function checkNote(): void {
    const isTooLong = form.note.trim().length > NOTE_MAX_LENGTH;

    setFieldError("note", isTooLong ? NOTE_TOO_LONG_TEXT : null);
}

function checkForm(): void {
    checkAccount();
    checkCategory();
    checkAmount();
    checkDate();
    checkNote();
}

// Значения собираются из уже проверенной формы, поэтому пустых счёта, категории, суммы и даты в них не бывает
function readFormValues(): OperationValues | null {
    const { accountId, categoryId, date } = form;
    const amount = normalizeAmountInput(form.amount);
    const isIncomplete = accountId === null || categoryId === null || date === null || amount === null;

    if (isIncomplete) {
        return null;
    }

    return {
        accountId,
        categoryId,
        amount,
        date: localDateToIsoDate(date),
        note: form.note.trim(),
    };
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

async function saveOperation(values: OperationValues): Promise<void> {
    const operation = props.operation;

    if (operation === null) {
        await createMutation.mutateAsync({ kind: form.kind, ...values });
        notifySuccess("Операция добавлена");

        return;
    }

    const changes = collectOperationChanges(operation, values);
    const hasChanges = Object.keys(changes).length > 0;

    // Без изменений запрос не нужен, диалог просто закрывается
    if (!hasChanges) {
        return;
    }

    await updateMutation.mutateAsync({ operationId: operation.id, changes });
    notifySuccess("Операция сохранена");
}

async function save(): Promise<void> {
    if (isSaving.value) {
        return;
    }

    formError.value = "";
    checkForm();

    const values = readFormValues();

    if (hasFieldErrors() || values === null) {
        return;
    }

    try {
        await saveOperation(values);
        close();
    } catch (error) {
        showSaveError(error);
    }
}
</script>

<template>
    <Dialog v-model:visible="isVisible" :header="header" modal :draggable="false" :close-on-escape="!isSaving" :close-button-props="closeButtonProps">
        <form class="dialog-form" novalidate @submit.prevent="save">
            <div v-if="!isEditing" class="form-field-group" role="group" :aria-labelledby="KIND_LABEL_ID">
                <span :id="KIND_LABEL_ID" class="operation-dialog__label">Вид</span>
                <SelectButton
                    v-model="form.kind"
                    :options="CATEGORY_KIND_OPTIONS"
                    option-label="label"
                    option-value="value"
                    :allow-empty="false"
                    :aria-labelledby="KIND_LABEL_ID"
                    :pt="KIND_PASS_THROUGH"
                />
            </div>
            <p v-else class="dialog-form__fact">{{ kindFact }}</p>

            <FormField label="Счёт" :input-id="ACCOUNT_INPUT_ID" :error="fieldErrors.account_id" is-required>
                <Select
                    v-model="form.accountId"
                    :input-id="ACCOUNT_INPUT_ID"
                    :aria-labelledby="ACCOUNT_LABEL_ID"
                    :pt="accountPassThrough"
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
                    :aria-labelledby="CATEGORY_LABEL_ID"
                    :pt="categoryPassThrough"
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
                    :pt="datePassThrough"
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
                <Button type="submit" :label="saveLabel" :loading="isSavingVisible" :disabled="isSaving" />
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
