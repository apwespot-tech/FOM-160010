<script setup lang="ts">
/**
 * ВРЕМЕННЫЙ КОСТЫЛЬ до подключения SMS: показывает код входа из тестовой ручки backend.
 * Если ручка выключена (404) или недоступна, не показывает ничего.
 * После подключения SMS удалить этот компонент и getTestCode.
 */
import { ref, watch } from 'vue'

import { getTestCode } from '@/api/auth'

const props = defineProps<{
  phone: string
  /** Меняется при каждом новом запросе кода — подсказка перезапрашивается */
  requestKey: number
}>()

const code = ref<string | null>(null)

watch(
  () => [props.phone, props.requestKey] as const,
  async ([phone]) => {
    code.value = null
    try {
      const result = await getTestCode(phone)
      code.value = result.code
    } catch {
      code.value = null
    }
  },
  { immediate: true },
)
</script>

<template>
  <div v-if="code" class="dev-code" role="status" data-testid="dev-code">
    <i class="pi pi-info-circle dev-code__icon" aria-hidden="true" />
    <div>
      <div class="dev-code__label">Тестовый режим: SMS не отправляются</div>
      <div>
        Ваш код: <strong class="dev-code__value" data-testid="dev-code-value">{{ code }}</strong>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dev-code {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px 14px;
  border: 1px solid var(--app-accent-border);
  border-left: 4px solid var(--app-accent);
  border-radius: 8px;
  background: var(--app-accent-soft);
  color: var(--app-accent-text);
}

.dev-code__icon {
  margin-top: 3px;
  color: var(--app-accent);
}

.dev-code__label {
  font-size: 0.875rem;
}

.dev-code__value {
  font-size: 1.125rem;
  letter-spacing: 0.15em;
}
</style>
