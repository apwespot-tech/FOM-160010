<script setup lang="ts">
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, reactive, ref, watch } from "vue";

import FormField from "./FormField.vue";
import { useAccountMutations } from "../composables/useAccounts";
import { useFieldErrors } from "../composables/useFieldErrors";
import { useNotifier } from "../composables/useNotifier";
import { ApiError, describeError } from "../services/apiClient";
import type { Account, AccountKind } from "../types/ledger";
import { checkRequired } from "../utils/formChecks";
import { ACCOUNT_KIND_LABELS, ACCOUNT_KIND_OPTIONS } from "../utils/ledgerLabels";
import { normalizeAmountInput } from "../utils/money";

const NAME_MAX_LENGTH = 100;
const DEFAULT_KIND: AccountKind = "card";
const DEFAULT_INITIAL_BALANCE = "0";
const NAME_INPUT_ID = "account-name";
const KIND_INPUT_ID = "account-kind";
const BALANCE_INPUT_ID = "account-initial-balance";
const ARCHIVE_INPUT_ID = "account-archived";
const KIND_HINT = "Тип после создания не меняется";
const BALANCE_HINT = "Сколько денег было на счёте до первой операции, можно с минусом";
const AMOUNT_FORMAT_TEXT = "Введите сумму числом, например 15000.50 или -250";

interface AccountForm {
    name: string;
    kind: AccountKind;
    initialBalance: string;
    isArchived: boolean;
}

const props = defineProps<{
    account: Account | null;
}>();

const isVisible = defineModel<boolean>("visible", { required: true });

const { createMutation, updateMutation } = useAccountMutations();
const { notifySuccess } = useNotifier();
const { clearFieldErrors, describeInput, fieldErrors, hasFieldErrors, replaceFieldErrors, setFieldError } = useFieldErrors();

const form = reactive<AccountForm>({
    name: "",
    kind: DEFAULT_KIND,
    initialBalance: DEFAULT_INITIAL_BALANCE,
    isArchived: false,
});

const formError = ref("");

const isEditing = computed(() => props.account !== null);
const header = computed(() => (isEditing.value ? "Изменить счёт" : "Новый счёт"));
const isSaving = computed(() => createMutation.isPending.value || updateMutation.isPending.value);
const saveLabel = computed(() => (isSaving.value ? "Сохранение…" : "Сохранить"));
const fixedFacts = computed(() => describeFixedFacts(props.account));
const nameDescription = computed(() => describeInput(NAME_INPUT_ID, "name"));
const balanceDescription = computed(() => describeInput(BALANCE_INPUT_ID, "initial_balance"));

function describeFixedFacts(account: Account | null): string {
    if (account === null) {
        return "Счёт открывается в рублях";
    }

    return `Тип: ${ACCOUNT_KIND_LABELS[account.kind]}, валюта: ${account.currency}`;
}

function resetForm(): void {
    const account = props.account;

    form.name = account?.name ?? "";
    form.kind = account?.kind ?? DEFAULT_KIND;
    form.initialBalance = account?.initialBalance ?? DEFAULT_INITIAL_BALANCE;
    form.isArchived = account?.isArchived ?? false;
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

function checkName(): void {
    const requiredError = checkRequired(form.name);

    if (requiredError !== null) {
        setFieldError("name", requiredError);

        return;
    }

    const isTooLong = form.name.trim().length > NAME_MAX_LENGTH;
    setFieldError("name", isTooLong ? `Название не длиннее ${NAME_MAX_LENGTH} знаков` : null);
}

function checkInitialBalance(): void {
    const isMalformed = normalizeAmountInput(form.initialBalance, true) === null;
    setFieldError("initial_balance", isMalformed ? AMOUNT_FORMAT_TEXT : null);
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

async function saveAccount(initialBalance: string): Promise<void> {
    const name = form.name.trim();

    if (props.account === null) {
        await createMutation.mutateAsync({ name, kind: form.kind, initialBalance });
        notifySuccess("Счёт добавлен");

        return;
    }

    const changes = { name, initialBalance, isArchived: form.isArchived };
    await updateMutation.mutateAsync({ accountId: props.account.id, changes });
    notifySuccess("Счёт сохранён");
}

async function save(): Promise<void> {
    if (isSaving.value) {
        return;
    }

    formError.value = "";
    checkName();
    checkInitialBalance();
    const initialBalance = normalizeAmountInput(form.initialBalance, true);

    if (hasFieldErrors() || initialBalance === null) {
        return;
    }

    try {
        await saveAccount(initialBalance);
        close();
    } catch (error) {
        showSaveError(error);
    }
}
</script>

<template>
    <Dialog v-model:visible="isVisible" :header="header" modal :draggable="false">
        <form class="dialog-form" novalidate @submit.prevent="save">
            <FormField label="Название" :input-id="NAME_INPUT_ID" :error="fieldErrors.name" is-required>
                <InputText
                    :id="NAME_INPUT_ID"
                    v-model="form.name"
                    v-bind="nameDescription"
                    :invalid="Boolean(fieldErrors.name)"
                    fluid
                    @blur="checkName"
                />
            </FormField>

            <FormField v-if="!isEditing" label="Тип" :input-id="KIND_INPUT_ID" :error="fieldErrors.kind" :hint="KIND_HINT" is-required>
                <Select
                    v-model="form.kind"
                    :input-id="KIND_INPUT_ID"
                    :options="ACCOUNT_KIND_OPTIONS"
                    option-label="label"
                    option-value="value"
                    :invalid="Boolean(fieldErrors.kind)"
                    fluid
                />
            </FormField>

            <p class="dialog-form__fact">{{ fixedFacts }}</p>

            <FormField
                label="Начальный остаток, ₽"
                :input-id="BALANCE_INPUT_ID"
                :error="fieldErrors.initial_balance"
                :hint="BALANCE_HINT"
                is-required
            >
                <InputText
                    :id="BALANCE_INPUT_ID"
                    v-model="form.initialBalance"
                    v-bind="balanceDescription"
                    class="money"
                    inputmode="decimal"
                    autocomplete="off"
                    :invalid="Boolean(fieldErrors.initial_balance)"
                    fluid
                    @blur="checkInitialBalance"
                />
            </FormField>

            <div v-if="isEditing" class="dialog-form__checkbox">
                <Checkbox v-model="form.isArchived" :input-id="ARCHIVE_INPUT_ID" binary />
                <label :for="ARCHIVE_INPUT_ID">Счёт в архиве: скрыт из выбора и не принимает новые операции</label>
            </div>

            <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>

            <div class="dialog-form__actions">
                <Button type="submit" :label="saveLabel" :loading="isSaving" :disabled="isSaving" />
                <Button type="button" label="Отмена" severity="secondary" outlined :disabled="isSaving" @click="close" />
            </div>
        </form>
    </Dialog>
</template>
