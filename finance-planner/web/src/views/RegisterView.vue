<script setup lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { computed, reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import AuthCard from "../components/AuthCard.vue";
import FormField from "../components/FormField.vue";
import PasswordField from "../components/PasswordField.vue";
import { useDelayedFlag } from "../composables/useDelayedFlag";
import { useFieldErrors } from "../composables/useFieldErrors";
import { ApiError, describeError } from "../services/apiClient";
import { useSessionStore } from "../stores/session";
import { checkNewPassword, checkNewUsername, checkPasswordConfirmation, PASSWORD_MIN_LENGTH } from "../utils/formChecks";
import { buildReturnQuery, readReturnPath } from "../utils/returnPath";
import { readBrowserTimeZone } from "../utils/timeZones";

const USERNAME_INPUT_ID = "register-username";
const PASSWORD_INPUT_ID = "register-password";
const CONFIRMATION_INPUT_ID = "register-password-confirmation";
const USERNAME_HINT = "Буквы, цифры и знаки @ . + - _, от 3 до 150 знаков";
const PASSWORD_HINT = `Не короче ${PASSWORD_MIN_LENGTH} знаков, не только цифры и не похож на логин`;

const session = useSessionStore();
const route = useRoute();
const router = useRouter();
const { describeInput, fieldErrors, hasFieldErrors, replaceFieldErrors, setFieldError } = useFieldErrors();

const form = reactive({ username: "", password: "", passwordConfirmation: "" });
const formError = ref("");
const isSubmitting = ref(false);

const isSubmittingVisible = useDelayedFlag(isSubmitting);
const submitLabel = computed(() => (isSubmittingVisible.value ? "Регистрация…" : "Зарегистрироваться"));
const usernameDescription = computed(() => describeInput(USERNAME_INPUT_ID, "username", { hasHint: true, isRequired: true }));
const passwordDescription = computed(() => describeInput(PASSWORD_INPUT_ID, "password", { hasHint: true, isRequired: true }));
const confirmationDescription = computed(() => describeInput(CONFIRMATION_INPUT_ID, "passwordConfirmation", { isRequired: true }));
const loginRoute = computed(() => ({ name: "login", query: buildReturnQuery(route.query.next) }));

function checkUsername(): void {
    setFieldError("username", checkNewUsername(form.username));
}

function checkPassword(): void {
    setFieldError("password", checkNewPassword(form.password));
}

function checkConfirmation(): void {
    setFieldError("passwordConfirmation", checkPasswordConfirmation(form.password, form.passwordConfirmation));
}

function showSubmitError(error: unknown): void {
    const hasServerFieldErrors = error instanceof ApiError && Object.keys(error.fieldErrors).length > 0;

    if (hasServerFieldErrors) {
        replaceFieldErrors(error.fieldErrors);

        return;
    }

    formError.value = describeError(error);
}

async function submit(): Promise<void> {
    if (isSubmitting.value) {
        return;
    }

    formError.value = "";
    checkUsername();
    checkPassword();
    checkConfirmation();

    if (hasFieldErrors()) {
        return;
    }

    isSubmitting.value = true;

    try {
        await session.register(form.username, form.password, readBrowserTimeZone());
        await router.replace(readReturnPath(route.query.next));
    } catch (error) {
        showSubmitError(error);
    } finally {
        isSubmitting.value = false;
    }
}
</script>

<template>
    <AuthCard title="Регистрация">
        <form class="auth-form" novalidate @submit.prevent="submit">
            <FormField label="Логин" :input-id="USERNAME_INPUT_ID" :error="fieldErrors.username" :hint="USERNAME_HINT" is-required>
                <InputText
                    :id="USERNAME_INPUT_ID"
                    v-model="form.username"
                    v-bind="usernameDescription"
                    autocomplete="username"
                    autocapitalize="none"
                    spellcheck="false"
                    :invalid="Boolean(fieldErrors.username)"
                    fluid
                    @blur="checkUsername"
                />
            </FormField>

            <FormField label="Пароль" :input-id="PASSWORD_INPUT_ID" :error="fieldErrors.password" :hint="PASSWORD_HINT" is-required>
                <PasswordField
                    v-model="form.password"
                    :input-id="PASSWORD_INPUT_ID"
                    autocomplete="new-password"
                    :description="passwordDescription"
                    :is-invalid="Boolean(fieldErrors.password)"
                    @blur="checkPassword"
                />
            </FormField>

            <FormField label="Пароль ещё раз" :input-id="CONFIRMATION_INPUT_ID" :error="fieldErrors.passwordConfirmation" is-required>
                <PasswordField
                    v-model="form.passwordConfirmation"
                    :input-id="CONFIRMATION_INPUT_ID"
                    autocomplete="new-password"
                    :description="confirmationDescription"
                    :is-invalid="Boolean(fieldErrors.passwordConfirmation)"
                    @blur="checkConfirmation"
                />
            </FormField>

            <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>

            <Button type="submit" :label="submitLabel" :loading="isSubmittingVisible" :disabled="isSubmitting" fluid />
        </form>

        <p class="auth-links">
            <span>Уже есть аккаунт?</span>
            <RouterLink :to="loginRoute">Войти</RouterLink>
        </p>
    </AuthCard>
</template>
