import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { useCountdown } from '@/composables/useCountdown'
import { formatRuDate, fromIsoDate, toIsoDate } from '@/utils/dates'
import { formatAge, formatPhone, initials } from '@/utils/format'

describe('даты', () => {
  const originalTz = process.env.TZ
  afterEach(() => {
    process.env.TZ = originalTz
  })

  it('toIsoDate не сдвигает дату в поясе UTC+10', () => {
    process.env.TZ = 'Asia/Vladivostok'
    const date = new Date(2000, 0, 15)

    expect(toIsoDate(date)).toBe('2000-01-15')
    // toISOString дал бы предыдущий день — поэтому он и не используется
    expect(date.toISOString().slice(0, 10)).toBe('2000-01-14')
  })

  it('fromIsoDate и formatRuDate', () => {
    const date = fromIsoDate('1995-05-20')
    expect([date.getFullYear(), date.getMonth(), date.getDate()]).toEqual([1995, 4, 20])
    expect(toIsoDate(date)).toBe('1995-05-20')
    expect(formatRuDate('1995-05-20')).toBe('20.05.1995')
  })
})

describe('форматирование', () => {
  it.each([
    ['Анна Иванова', 'АИ'],
    ['анна', 'А'],
    ['  Анна   Мария Иванова ', 'АМ'],
    [null, ''],
  ])('initials(%s) = %s', (name, expected) => {
    expect(initials(name)).toBe(expected)
  })

  it.each([
    [1, '1 год'],
    [3, '3 года'],
    [11, '11 лет'],
    [21, '21 год'],
    [25, '25 лет'],
    [104, '104 года'],
  ])('formatAge(%i) = %s', (age, expected) => {
    expect(formatAge(age)).toBe(expected)
  })

  it('formatPhone', () => {
    expect(formatPhone('+79991234567')).toBe('+7 999 123-45-67')
    expect(formatPhone('+12025550123')).toBe('+12025550123')
  })
})

describe('useCountdown', () => {
  it('граница 59/60 секунд', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    const start = Date.now()
    const deadline = ref(start + 60_000)
    let countdown: ReturnType<typeof useCountdown> | undefined
    const Probe = defineComponent({
      setup() {
        countdown = useCountdown(deadline)
        return () => h('span', countdown?.remaining.value)
      },
    })
    mount(Probe)
    const remaining = () => countdown?.remaining.value

    expect(remaining()).toBe(60)
    vi.advanceTimersByTime(59_000)
    expect(remaining()).toBe(1)
    vi.advanceTimersByTime(1_000)
    expect(remaining()).toBe(0)
    vi.useRealTimers()
  })
})
