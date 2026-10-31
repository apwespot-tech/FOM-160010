<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import type { TokenPair } from '@/api/auth'
import CodeStep from '@/components/CodeStep.vue'
import PhoneStep from '@/components/PhoneStep.vue'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()

const step = ref<'phone' | 'code'>('phone')
const phone = ref('')
const resendDeadline = ref(0)
/** Растёт при каждом запросе кода — по нему перезапрашивается тестовый код */
const requestKey = ref(0)

function onRequested(value: string, deadline: number) {
  phone.value = value
  resendDeadline.value = deadline
  requestKey.value += 1
  step.value = 'code'
}

function onResent(deadline: number) {
  resendDeadline.value = deadline
  requestKey.value += 1
}

async function onVerified(tokens: TokenPair) {
  await session.login(tokens)
  await router.replace(session.isProfileCompleted ? '/profile' : '/onboarding')
}
</script>

<template>
  <main class="app-page">
    <section class="app-card">
      <h1 class="app-title">{{ step === 'phone' ? 'Вход' : 'Введите код' }}</h1>
      <p class="app-subtitle">
        {{
          step === 'phone'
            ? 'Войдите или зарегистрируйтесь по номеру телефона'
            : 'Мы отправили код подтверждения'
        }}
      </p>

      <PhoneStep v-if="step === 'phone'" :initial-phone="phone" @requested="onRequested" />
      <CodeStep
        v-else
        :phone="phone"
        :resend-deadline="resendDeadline"
        :request-key="requestKey"
        @verified="onVerified"
        @resent="onResent"
        @change-phone="step = 'phone'"
      />
    </section>
  </main>
</template>
