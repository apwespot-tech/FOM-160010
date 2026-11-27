<script setup lang="ts">
import { RouterLink } from "vue-router";

import AuthCard from "../components/AuthCard.vue";

const REGISTER_ROUTE = { name: "register" };
const STATUS_ROUTE = { name: "status" };
</script>

<template>
    <AuthCard title="Вход">
        <p class="auth-note">Форма входа в разработке</p>
        <p class="auth-links">
            <RouterLink :to="REGISTER_ROUTE">Регистрация</RouterLink>
            <RouterLink :to="STATUS_ROUTE">Состояние сервисов</RouterLink>
        </p>
    </AuthCard>
</template>
