<script setup lang="ts">
import Button from "primevue/button";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";
import { useConfirm } from "primevue/useconfirm";
import { computed, ref } from "vue";

import AccountCard from "../components/AccountCard.vue";
import AccountDialog from "../components/AccountDialog.vue";
import { useAccountMutations, useAccountsQuery } from "../composables/useAccounts";
import { useDelayedFlag } from "../composables/useDelayedFlag";
import { useNotifier } from "../composables/useNotifier";
import { ApiError, describeError } from "../services/apiClient";
import type { Account } from "../types/ledger";
import { formatMoney } from "../utils/money";

const SKELETON_CARD_COUNT = 3;
// Общий баланс API отдаёт в рублях
const TOTAL_CURRENCY = "RUB";
const CANCEL_BUTTON = { label: "Отмена", severity: "secondary", outlined: true };

const { data, error, isError, isPending, refetch } = useAccountsQuery();
const { deleteMutation, updateMutation } = useAccountMutations();
const confirm = useConfirm();
const { notifyError, notifySuccess } = useNotifier();

const isDialogOpen = ref(false);
const editedAccount = ref<Account | null>(null);

const isLoadingVisible = useDelayedFlag(isPending);
const accounts = computed(() => data.value?.items ?? []);
const activeAccounts = computed(() => accounts.value.filter((account) => !account.isArchived));
const archivedAccounts = computed(() => accounts.value.filter((account) => account.isArchived));
const hasAccounts = computed(() => accounts.value.length > 0);
const totalBalanceText = computed(() => formatMoney(data.value?.totalBalance ?? "0.00", TOTAL_CURRENCY));
const loadErrorText = computed(() => describeError(error.value));

function openCreateDialog(): void {
    editedAccount.value = null;
    isDialogOpen.value = true;
}

function openEditDialog(account: Account): void {
    editedAccount.value = account;
    isDialogOpen.value = true;
}

function retryLoading(): void {
    void refetch();
}

async function archiveAccount(account: Account): Promise<void> {
    try {
        await updateMutation.mutateAsync({ accountId: account.id, changes: { isArchived: true } });
        notifySuccess("Счёт перенесён в архив");
    } catch (archiveError) {
        notifyError(archiveError);
    }
}

function offerArchive(account: Account, reason: string): void {
    confirm.require({
        header: "Счёт нельзя удалить",
        message: reason,
        acceptProps: { label: "Перенести в архив" },
        rejectProps: CANCEL_BUTTON,
        defaultFocus: "reject",
        accept: () => void archiveAccount(account),
    });
}

async function removeAccount(account: Account): Promise<void> {
    try {
        await deleteMutation.mutateAsync(account.id);
        notifySuccess("Счёт удалён");
    } catch (removalError) {
        const isAccountInUse = removalError instanceof ApiError && removalError.code === "account_in_use";

        if (isAccountInUse) {
            offerArchive(account, removalError.message);

            return;
        }

        notifyError(removalError);
    }
}

function confirmRemoval(account: Account): void {
    confirm.require({
        header: "Удалить счёт?",
        message: `Счёт «${account.name}» будет удалён без возможности восстановления`,
        acceptProps: { label: "Удалить счёт", severity: "danger" },
        rejectProps: CANCEL_BUTTON,
        defaultFocus: "reject",
        accept: () => void removeAccount(account),
    });
}
</script>

<template>
    <div class="accounts-page">
        <header class="page-heading">
            <h1 class="page-heading__title">Счета</h1>
            <Button label="Добавить счёт" @click="openCreateDialog" />
        </header>

        <div v-if="isPending" class="accounts-grid" :aria-busy="true" aria-label="Загрузка счетов">
            <template v-if="isLoadingVisible">
                <Skeleton v-for="index in SKELETON_CARD_COUNT" :key="index" height="10rem" border-radius="0.875rem" />
            </template>
        </div>

        <div v-else-if="isError" class="state-card">
            <Message severity="error" :closable="false">{{ loadErrorText }}</Message>
            <div>
                <Button label="Повторить" severity="secondary" outlined @click="retryLoading" />
            </div>
        </div>

        <div v-else-if="!hasAccounts" class="state-card">
            <p class="state-card__title">Счетов пока нет</p>
            <p class="state-card__text">Добавьте первый счёт: карту, наличные или накопительный</p>
            <div>
                <Button label="Добавить счёт" @click="openCreateDialog" />
            </div>
        </div>

        <template v-else>
            <section class="total-card" aria-label="Общий баланс">
                <p class="total-card__label">Общий баланс</p>
                <p class="total-card__amount money">{{ totalBalanceText }}</p>
                <p v-if="archivedAccounts.length > 0" class="total-card__hint">С учётом счетов в архиве</p>
            </section>

            <section v-if="activeAccounts.length > 0" aria-labelledby="active-accounts-title">
                <h2 id="active-accounts-title" class="section-title">Действующие</h2>
                <div class="accounts-grid">
                    <AccountCard
                        v-for="account in activeAccounts"
                        :key="account.id"
                        :account="account"
                        @edit="openEditDialog"
                        @remove="confirmRemoval"
                    />
                </div>
            </section>

            <section v-if="archivedAccounts.length > 0" aria-labelledby="archived-accounts-title">
                <h2 id="archived-accounts-title" class="section-title">Архив</h2>
                <div class="accounts-grid">
                    <AccountCard
                        v-for="account in archivedAccounts"
                        :key="account.id"
                        :account="account"
                        @edit="openEditDialog"
                        @remove="confirmRemoval"
                    />
                </div>
            </section>
        </template>

        <AccountDialog v-model:visible="isDialogOpen" :account="editedAccount" />
    </div>
</template>

<style scoped>
.accounts-page {
    display: grid;
    gap: 1.75rem;
}

.accounts-page .page-heading {
    margin-bottom: 0;
}

.accounts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
    gap: 1rem;
}

.total-card {
    display: grid;
    gap: 0.25rem;
    padding: 1.25rem 1.375rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-large);
    background: var(--color-surface);
}

.total-card__label {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    font-weight: 600;
}

.total-card__amount {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
}

.total-card__hint {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
}

@media (max-width: 40rem) {
    .total-card__amount {
        font-size: 1.625rem;
    }
}
</style>
