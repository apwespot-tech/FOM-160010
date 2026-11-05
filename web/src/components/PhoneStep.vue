<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { computed, ref } from 'vue'

import { requestCode, RESEND_INTERVAL_MS } from '@/api/auth'
import { ApiError } from '@/api/client'

const props = defineProps<{ initialPhone?: string }>()
const emit = defineEmits<{
  /** Код запрошен (или сервер сообщил, что повторить можно позже): телефон и дедлайн повтора */
  requested: [phone: string, resendDeadline: number]
}>()

const phone = ref(props.initialPhone ?? '')
const loading = ref(false)
const fieldError = ref<string | null>(null)
const generalError = ref<string | null>(null)

const canSubmit = computed(() => phone.value.trim().length > 0 && !loading.value)

async function submit() {
  if (!canSubmit.value) return
  const value = phone.value.trim()
  loading.value = true
  fieldError.value = null
  generalError.value = null
  try {
    await requestCode(value)
    emit('requested', value, Date.now() + RESEND_INTERVAL_MS)
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      fieldError.value = 'Некорректный номер телефона'
    } else if (error instanceof ApiError && error.status === 429) {
      const seconds = error.retryAfter ?? RESEND_INTERVAL_MS / 1000
      emit('requested', value, Date.now() + seconds * 1000)
    } else {
      generalError.value = 'Не удалось отправить код. Попробуйте ещё раз'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="app-form" novalidate @submit.prevent="submit">
    <div class="app-field">
      <label for="phone">Номер телефона</label>
      <InputText
        id="phone"
        v-model="phone"
        type="tel"
        inputmode="tel"
        autocomplete="tel"
        placeholder="+7 999 123-45-67"
        :invalid="fieldError !== null"
        :aria-describedby="fieldError ? 'phone-error' : undefined"
        data-testid="phone-input"
      />
      <small v-if="fieldError" id="phone-error" class="app-field-error" data-testid="phone-error">
        {{ fieldError }}
      </small>
    </div>

    <Message v-if="generalError" severity="error" :closable="false">{{ generalError }}</Message>

    <div class="app-actions">
      <Button
        type="submit"
        label="Получить код"
        :loading="loading"
        :disabled="!canSubmit"
        data-testid="phone-submit"
      />
    </div>
  </form>
</template>
