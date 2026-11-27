<script setup lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, ref, watch } from "vue";

import FormField from "./FormField.vue";
import { useDelayedFlag } from "../composables/useDelayedFlag";
import { useFieldErrors } from "../composables/useFieldErrors";
import { useNotifier } from "../composables/useNotifier";
import { ApiError, describeError } from "../services/apiClient";
import { useSessionStore } from "../stores/session";
import { buildCloseButtonProps } from "../utils/dialogs";
import { buildLabelId } from "../utils/formIds";
import { listTimeZones } from "../utils/timeZones";

const TIME_ZONE_INPUT_ID = "profile-time-zone";
const TIME_ZONE_LABEL_ID = buildLabelId(TIME_ZONE_INPUT_ID);
const TIME_ZONE_HINT = "По нему считается сегодняшний день: дата новой операции и проверка дат в будущем";

const isVisible = defineModel<boolean>("visible", { required: true });

const session = useSessionStore();
const { notifySuccess } = useNotifier();
const { clearFieldErrors, describeInput, fieldErrors, replaceFieldErrors } = useFieldErrors();

const selectedTimeZone = ref("");
const formError = ref("");
const isSaving = ref(false);

const username = computed(() => session.currentUser?.username ?? "");
const currentTimeZone = computed(() => session.currentUser?.timeZone ?? "");
const timeZones = computed(() => listTimeZones(currentTimeZone.value));
const isSavingVisible = useDelayedFlag(isSaving);
const saveLabel = computed(() => (isSavingVisible.value ? "Сохранение…" : "Сохранить"));
const closeButtonProps = computed(() => buildCloseButtonProps(isSaving.value));

// Поле выбора PrimeVue — это span с ролью combobox: связь с подсказкой и начальный фокус диалога передаются ему через pass-through
const timeZonePassThrough = computed(() => ({
    label: { ...describeInput(TIME_ZONE_INPUT_ID, "time_zone", { hasHint: true }), autofocus: true },
}));

// Сразу при монтировании тоже: диалог подгружается при первом открытии и появляется уже открытым
watch(
    isVisible,
    (isOpen) => {
        if (isOpen) {
            selectedTimeZone.value = currentTimeZone.value;
            formError.value = "";
            clearFieldErrors();
        }
    },
    { immediate: true },
);

function close(): void {
    isVisible.value = false;
}

async function save(): Promise<void> {
    if (isSaving.value) {
        return;
    }

    formError.value = "";
    clearFieldErrors();
    isSaving.value = true;

    try {
        await session.updateTimeZone(selectedTimeZone.value);
        notifySuccess("Часовой пояс сохранён");
        close();
    } catch (error) {
        const hasServerFieldErrors = error instanceof ApiError && Object.keys(error.fieldErrors).length > 0;

        if (hasServerFieldErrors) {
            replaceFieldErrors(error.fieldErrors);
        } else {
            formError.value = describeError(error);
        }
    } finally {
        isSaving.value = false;
    }
}
</script>

<template>
    <Dialog
        v-model:visible="isVisible"
        header="Профиль"
        modal
        :draggable="false"
        :close-on-escape="!isSaving"
        :close-button-props="closeButtonProps"
        class="profile-dialog"
    >
        <form class="dialog-form" novalidate @submit.prevent="save">
            <dl class="profile-dialog__facts">
                <dt>Логин</dt>
                <dd>{{ username }}</dd>
            </dl>

            <FormField label="Часовой пояс" :input-id="TIME_ZONE_INPUT_ID" :error="fieldErrors.time_zone" :hint="TIME_ZONE_HINT">
                <Select
                    v-model="selectedTimeZone"
                    :input-id="TIME_ZONE_INPUT_ID"
                    :aria-labelledby="TIME_ZONE_LABEL_ID"
                    :pt="timeZonePassThrough"
                    :options="timeZones"
                    :invalid="Boolean(fieldErrors.time_zone)"
                    filter
                    filter-placeholder="Поиск пояса"
                    fluid
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
.profile-dialog__facts {
    display: flex;
    gap: 0.75rem;
}

.profile-dialog__facts dt {
    color: var(--color-text-secondary);
}

.profile-dialog__facts dd {
    font-weight: 600;
    overflow-wrap: anywhere;
}
</style>
