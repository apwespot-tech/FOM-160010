<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { computed, ref, toRef } from 'vue'

import { requestCode, RESEND_INTERVAL_MS, verifyCode, type TokenPair } from '@/api/auth'
import { ApiError } from '@/api/client'
import DevCodeHint from '@/components/DevCodeHint.vue'
import { useCountdown } from '@/composables/useCountdown'

const props = defineProps<{
  phone: string
  resendDeadline: number
  requestKey: number
}>()
const emit = defineEmits<{
  verified: [tokens: TokenPair]
  changePhone: []
  resent: [resendDeadline: number]
}>()

const code = ref('')
const loading = ref(false)
const resending = ref(false)
const error = ref<string | null>(null)

const { remaining, tick } = useCountdown(toRef(props, 'resendDeadline'))

const canSubmit = computed(() => /^\d{6}$/.test(code.value) && !loading.value)

function onInput(value: string | undefined) {
  // Только цифры, не больше 6
  code.value = (value ?? '').replace(/\D/g, '').slice(0, 6)
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = null
  try {
    emit('verified', await verifyCode(props.phone, code.value))
  } catch (err) {
    code.value = ''
    error.value =
      err instanceof ApiError && (err.status === 400 || err.status === 422)
        ? 'Неверный или просроченный код'
        : 'Не удалось проверить код. Попробуйте ещё раз'
  } finally {
    loading.value = false
  }
}

async function resend() {
  if (remaining.value > 0 || resending.value) return
  resending.value = true
  error.value = null
  try {
    await requestCode(props.phone)
    emit('resent', Date.now() + RESEND_INTERVAL_MS)
  } catch (err) {
    if (err instanceof ApiError && err.status === 429) {
      emit('resent', Date.now() + (err.retryAfter ?? RESEND_INTERVAL_MS / 1000) * 1000)
    } else {
      error.value = 'Не удалось отправить код. Попробуйте ещё раз'
    }
  } finally {
    resending.value = false
    tick()
  }
}
</script>

<template>
  <form class="app-form" novalidate @submit.prevent="submit">
    <p class="code-step__sent">
      Код отправлен на <strong class="app-break" data-testid="code-phone">{{ phone }}</strong>
    </p>

    <DevCodeHint :phone="phone" :request-key="requestKey" />

    <div class="app-field">
      <label for="code">Код из SMS</label>
      <InputText
        id="code"
        :model-value="code"
        inputmode="numeric"
        autocomplete="one-time-code"
        maxlength="6"
        placeholder="000000"
        :invalid="error !== null"
        data-testid="code-input"
        @update:model-value="onInput"
      />
      <small v-if="error" class="app-field-error" data-testid="code-error">{{ error }}</small>
    </div>

    <div class="app-actions">
      <Button
        type="submit"
        label="Войти"
        :loading="loading"
        :disabled="!canSubmit"
        data-testid="code-submit"
      />
      <Button
        type="button"
        severity="secondary"
        outlined
        :label="
          remaining > 0 ? `Отправить код повторно (${remaining} с)` : 'Отправить код повторно'
        "
        :disabled="remaining > 0 || resending"
        :loading="resending"
        data-testid="code-resend"
        @click="resend"
      />
      <Button
        type="button"
        text
        icon="pi pi-arrow-left"
        label="Изменить номер"
        data-testid="code-change-phone"
        @click="emit('changePhone')"
      />
    </div>
  </form>
</template>

<style scoped>
.code-step__sent {
  margin: 0;
  color: var(--app-text-muted);
}

.code-step__sent strong {
  color: var(--app-text);
}
</style>
