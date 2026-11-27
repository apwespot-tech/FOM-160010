<script setup lang="ts">
import { RouterLink } from "vue-router";

import AuthCard from "../components/AuthCard.vue";

const LOGIN_ROUTE = { name: "login" };
</script>

<template>
    <AuthCard title="Регистрация">
        <p class="auth-note">Форма регистрации в разработке</p>
        <p class="auth-links">
            <RouterLink :to="LOGIN_ROUTE">Вход</RouterLink>
        </p>
    </AuthCard>
</template>
