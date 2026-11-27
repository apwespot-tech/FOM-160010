<script setup lang="ts">
import Button from "primevue/button";
import { computed } from "vue";

import type { Account } from "../types/ledger";
import { ACCOUNT_KIND_LABELS } from "../utils/ledgerLabels";
import { formatMoney } from "../utils/money";

const props = defineProps<{
    account: Account;
}>();

const emit = defineEmits<{
    edit: [account: Account];
    remove: [account: Account];
}>();

const kindLabel = computed(() => ACCOUNT_KIND_LABELS[props.account.kind]);
const balanceText = computed(() => formatMoney(props.account.balance, props.account.currency));
const initialBalanceText = computed(() => formatMoney(props.account.initialBalance, props.account.currency));
const editLabel = computed(() => `Изменить счёт «${props.account.name}»`);
const removeLabel = computed(() => `Удалить счёт «${props.account.name}»`);
const cardClasses = computed(() => ({ "account-card--archived": props.account.isArchived }));

function requestEdit(): void {
    emit("edit", props.account);
}

function requestRemoval(): void {
    emit("remove", props.account);
}
</script>

<template>
    <article class="account-card" :class="cardClasses">
        <header class="account-card__header">
            <h3 class="account-card__name" :title="account.name">{{ account.name }}</h3>
            <span class="account-card__kind">{{ kindLabel }}</span>
        </header>

        <p class="account-card__balance money">{{ balanceText }}</p>
        <p class="account-card__meta">
            <span>Начальный остаток</span>
            <span class="money">{{ initialBalanceText }}</span>
        </p>

        <footer class="account-card__actions">
            <Button label="Изменить" size="small" severity="secondary" outlined :aria-label="editLabel" @click="requestEdit" />
            <Button label="Удалить" size="small" severity="danger" text :aria-label="removeLabel" @click="requestRemoval" />
        </footer>
    </article>
</template>

<style scoped>
.account-card {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
    padding: 1.125rem 1.25rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-large);
    background: var(--color-surface);
}

.account-card--archived {
    border-style: dashed;
}

.account-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
}

.account-card__name {
    overflow: hidden;
    font-size: 1.0625rem;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.account-card__kind {
    flex-shrink: 0;
    padding: 0.1875rem 0.625rem;
    border-radius: 999px;
    background: var(--color-surface-raised);
    color: var(--color-text-secondary);
    font-size: 0.8125rem;
    font-weight: 600;
}

.account-card__balance {
    font-size: 1.375rem;
    font-weight: 700;
    line-height: 1.2;
}

.account-card__meta {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0.25rem 0.75rem;
    color: var(--color-text-secondary);
    font-size: 0.875rem;
}

.account-card__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: auto;
    padding-top: 0.25rem;
}
</style>
