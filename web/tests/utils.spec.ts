import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { ApiError } from '@/api/client'
import { useCountdown } from '@/composables/useCountdown'
import {
  dateRangeToParams,
  formatCreatedAt,
  formatDuration,
  formatEventDate,
  formatRuDate,
  fromIsoDate,
  fromLocalInputValue,
  toIsoDate,
  toLocalInputValue,
  toOffsetIso,
} from '@/utils/dates'
import {
  formatAge,
  formatFreePlaces,
  formatMinAge,
  formatPhone,
  formatPlaces,
  initials,
  telegramUrl,
} from '@/utils/format'
import {
  buildPhotoPayload,
  draftKeyForFileError,
  overflowMessage,
  photoErrorMessage,
  photosChanged,
  savedDrafts,
  validatePhotoFiles,
  type PhotoDraft,
} from '@/utils/photos'

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

describe('дата и время мероприятия (UTC+3)', () => {
  const now = new Date(2026, 9, 31, 12, 0)

  it('показывает время в часовом поясе браузера', () => {
    expect(formatEventDate('2026-11-01T16:00:00Z', now)).toBe('вс, 1 ноября, 19:00')
  })

  it('добавляет год, если он не текущий', () => {
    expect(formatEventDate('2027-01-01T07:00:00Z', now)).toBe('пт, 1 января 2027, 10:00')
  })

  it('toOffsetIso сохраняет локальное время со смещением', () => {
    expect(toOffsetIso(new Date(2026, 10, 1, 19, 0))).toBe('2026-11-01T19:00:00+03:00')
  })

  it('datetime-local туда и обратно', () => {
    const date = fromLocalInputValue('2026-11-01T19:30')
    expect(date && toLocalInputValue(date)).toBe('2026-11-01T19:30')
    expect(fromLocalInputValue('')).toBeNull()
  })

  it.each([
    [90, '1 ч 30 мин'],
    [120, '2 ч'],
    [45, '45 мин'],
  ])('длительность %i -> %s', (minutes, text) => {
    expect(formatDuration(minutes)).toBe(text)
  })

  it('диапазон 1–2 декабря -> from начало 1-го, to начало 3-го', () => {
    expect(dateRangeToParams(new Date(2026, 11, 1), new Date(2026, 11, 2))).toEqual({
      from: '2026-12-01T00:00:00+03:00',
      to: '2026-12-03T00:00:00+03:00',
    })
    expect(dateRangeToParams(null, null)).toEqual({ from: undefined, to: undefined })
  })
})

describe('места и возраст', () => {
  it.each([
    [3, 10, 'Осталось 3 из 10 мест'],
    [1, 21, 'Осталось 1 из 21 места'],
    [0, 5, 'Мест нет'],
  ])('formatPlaces(%i, %i)', (free, max, text) => {
    expect(formatPlaces(free, max)).toBe(text)
  })

  it('formatMinAge', () => {
    expect(formatMinAge(18)).toBe('18+')
  })
})

describe('создание мероприятия и контакты (UTC+3)', () => {
  const now = new Date(2026, 9, 31, 12, 0)

  it.each([
    ['2026-10-31T06:15:00Z', 'сегодня в 09:15'],
    ['2026-10-30T15:40:00Z', 'вчера в 18:40'],
    ['2026-10-12T15:40:00Z', '12 октября в 18:40'],
    ['2025-11-12T15:40:00Z', '12 ноября 2025 г. в 18:40'],
  ])('formatCreatedAt(%s) -> %s', (iso, text) => {
    expect(formatCreatedAt(iso, now)).toBe(text)
  })

  it('telegramUrl убирает @', () => {
    expect(telegramUrl('@boris_k')).toBe('https://t.me/boris_k')
  })

  it.each([
    [1, 'остался 1 свободное место'],
    [3, 'осталось 3 свободных места'],
    [7, 'осталось 7 свободных мест'],
    [0, 'свободных мест нет'],
  ])('formatFreePlaces(%i)', (free, text) => {
    expect(formatFreePlaces(free)).toBe(text)
  })
})

describe('фото: проверка и тело запроса', () => {
  const MB = 1024 * 1024
  const file = (name: string, type = 'image/jpeg', size = 1000) =>
    new File([new Uint8Array(size)], name, { type })

  it('граница 2 МБ', () => {
    const exact = file('exact.jpg', 'image/jpeg', 2 * MB)
    const over = file('over.jpg', 'image/jpeg', 2 * MB + 1)

    const result = validatePhotoFiles(0, [exact, over])

    expect(result.accepted).toEqual([exact])
    expect(result.rejected).toEqual([{ name: 'over.jpg', reason: 'Файл больше 2 МБ' }])
  })

  it('HEIC и GIF отклоняются', () => {
    const result = validatePhotoFiles(0, [file('a.heic', 'image/heic'), file('b.gif', 'image/gif')])

    expect(result.accepted).toEqual([])
    expect(result.rejected.map((r) => r.reason)).toEqual([
      'Поддерживаются JPEG, PNG и WebP',
      'Поддерживаются JPEG, PNG и WebP',
    ])
  })

  it('8 + 4 файла: добавляются первые 2', () => {
    const files = [
      file('1.jpg'),
      file('2.png', 'image/png'),
      file('3.webp', 'image/webp'),
      file('4.jpg'),
    ]

    const result = validatePhotoFiles(8, files)

    expect(result.accepted.map((f) => f.name)).toEqual(['1.jpg', '2.png'])
    expect(result.overflow).toBe(2)
    expect(overflowMessage(result.overflow)).toBe('Не больше 10 фото — 2 файла не добавлены')
    expect(overflowMessage(1)).toBe('Не больше 10 фото — 1 файл не добавлен')
  })

  it('order ссылается на новые файлы по порядку', () => {
    const beach = file('beach.jpg')
    const map = file('map.png', 'image/png')
    const drafts: PhotoDraft[] = [
      { kind: 'new', key: 'n1', file: beach, previewUrl: 'blob:1' },
      { kind: 'saved', key: 'saved:a1', id: 'a1' },
      { kind: 'saved', key: 'saved:c3', id: 'c3' },
      { kind: 'new', key: 'n2', file: map, previewUrl: 'blob:2' },
    ]

    expect(buildPhotoPayload(drafts)).toEqual({
      order: [{ file: 0 }, { id: 'a1' }, { id: 'c3' }, { file: 1 }],
      files: [beach, map],
    })
  })

  it('изменения набора и ошибка конкретного файла', () => {
    const saved = [{ id: 'a' }, { id: 'b' }]
    const same = savedDrafts(saved)
    const drafts: PhotoDraft[] = [
      ...same,
      { kind: 'new', key: 'n1', file: file('x.jpg'), previewUrl: 'blob:1' },
      { kind: 'new', key: 'n2', file: file('y.jpg'), previewUrl: 'blob:2' },
    ]

    expect(photosChanged(same, saved)).toBe(false)
    expect(photosChanged([...same].reverse(), saved)).toBe(true)
    expect(photosChanged(drafts, saved)).toBe(true)
    const error = new ApiError(422, 'photo_invalid', 'bad', { file: 1 })
    expect(draftKeyForFileError(drafts, error)).toBe('n2')
    expect(photoErrorMessage(error)).toBe('Поддерживаются JPEG, PNG и WebP')
  })
})
