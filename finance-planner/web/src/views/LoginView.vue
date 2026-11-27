<script setup lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import { computed, reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import AuthCard from "../components/AuthCard.vue";
import FormField from "../components/FormField.vue";
import { useFieldErrors } from "../composables/useFieldErrors";
import { readReturnPath } from "../router";
import { ApiError, describeError } from "../services/apiClient";
import { useSessionStore } from "../stores/session";
import { checkRequired } from "../utils/formChecks";

const REGISTER_ROUTE = { name: "register" };
const STATUS_ROUTE = { name: "status" };
const USERNAME_INPUT_ID = "login-username";
const PASSWORD_INPUT_ID = "login-password";
const INVALID_CREDENTIALS_TEXT = "Неверный логин или пароль";

const session = useSessionStore();
const route = useRoute();
const router = useRouter();
const { describeInput, fieldErrors, hasFieldErrors, replaceFieldErrors, setFieldError } = useFieldErrors();

const form = reactive({ username: "", password: "" });
const formError = ref("");
const isSubmitting = ref(false);

const submitLabel = computed(() => (isSubmitting.value ? "Вход…" : "Войти"));
const usernameDescription = computed(() => describeInput(USERNAME_INPUT_ID, "username"));
const passwordInputProps = computed(() => ({ ...describeInput(PASSWORD_INPUT_ID, "password"), autocomplete: "current-password" }));

function checkUsername(): void {
    setFieldError("username", checkRequired(form.username));
}

function checkPassword(): void {
    setFieldError("password", checkRequired(form.password));
}

function showSubmitError(error: unknown): void {
    if (error instanceof ApiError && error.code === "invalid_credentials") {
        formError.value = INVALID_CREDENTIALS_TEXT;

        return;
    }

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

    if (hasFieldErrors()) {
        return;
    }

    isSubmitting.value = true;

    try {
        await session.logIn(form.username, form.password);
        await router.replace(readReturnPath(route));
    } catch (error) {
        showSubmitError(error);
    } finally {
        isSubmitting.value = false;
    }
}
</script>

<template>
    <AuthCard title="Вход">
        <form class="auth-form" novalidate @submit.prevent="submit">
            <FormField label="Логин" :input-id="USERNAME_INPUT_ID" :error="fieldErrors.username" is-required>
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

            <FormField label="Пароль" :input-id="PASSWORD_INPUT_ID" :error="fieldErrors.password" is-required>
                <Password
                    v-model="form.password"
                    :input-id="PASSWORD_INPUT_ID"
                    :input-props="passwordInputProps"
                    :feedback="false"
                    :invalid="Boolean(fieldErrors.password)"
                    toggle-mask
                    fluid
                    @blur="checkPassword"
                />
            </FormField>

            <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>

            <Button type="submit" :label="submitLabel" :loading="isSubmitting" :disabled="isSubmitting" fluid />
        </form>

        <p class="auth-links">
            <span>Нет аккаунта?</span>
            <RouterLink :to="REGISTER_ROUTE">Зарегистрироваться</RouterLink>
        </p>
        <p class="auth-links">
            <RouterLink :to="STATUS_ROUTE">Состояние сервисов</RouterLink>
        </p>
    </AuthCard>
</template>
