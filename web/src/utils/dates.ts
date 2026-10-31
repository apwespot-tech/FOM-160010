export const MIN_BIRTH_DATE = new Date(1900, 0, 1)

const pad = (value: number) => String(value).padStart(2, '0')

/**
 * Date -> 'YYYY-MM-DD' по локальным компонентам.
 * toISOString() не подходит: в поясах восточнее UTC он сдвигает дату на день назад.
 */
export function toIsoDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** 'YYYY-MM-DD' -> Date на локальную полночь. */
export function fromIsoDate(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1)
}

/** 'YYYY-MM-DD' -> 'ДД.ММ.ГГГГ'. */
export function formatRuDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

/** Сегодня, локальная полночь. */
export function startOfToday(now: Date = new Date()): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

/** Локальная полночь дня date. */
export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

export function addDays(date: Date, days: number): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
}

/**
 * Локальное время с явным смещением: 2026-11-01T19:00:00+03:00.
 * Сервер требует часовой пояс, а toISOString() перевёл бы время в UTC.
 */
export function toOffsetIso(date: Date): string {
  const offset = -date.getTimezoneOffset()
  const sign = offset >= 0 ? '+' : '-'
  const abs = Math.abs(offset)
  return (
    `${toIsoDate(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` +
    `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  )
}

/** Date -> значение для <input type="datetime-local">: 2026-11-01T19:00. */
export function toLocalInputValue(date: Date): string {
  return `${toIsoDate(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** Значение <input type="datetime-local"> -> Date в часовом поясе браузера. */
export function fromLocalInputValue(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value)
  if (!match) return null
  const [, year, month, day, hours, minutes] = match.map(Number)
  return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1, hours ?? 0, minutes ?? 0)
}

const weekdayFormat = new Intl.DateTimeFormat('ru', { weekday: 'short' })
const dayMonthFormat = new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'long' })

/** «сб, 1 ноября, 19:00»; год — если он не текущий: «пт, 1 января 2027, 10:00». */
export function formatEventDate(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  const year = date.getFullYear() === now.getFullYear() ? '' : ` ${date.getFullYear()}`
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  return `${weekdayFormat.format(date)}, ${dayMonthFormat.format(date)}${year}, ${time}`
}

/** 90 -> «1 ч 30 мин», 120 -> «2 ч», 45 -> «45 мин». */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return [hours ? `${hours} ч` : '', rest ? `${rest} мин` : ''].filter(Boolean).join(' ')
}

/**
 * Диапазон дат фильтра (локальные дни, конечный включительно) -> параметры API:
 * from — начало первого дня, to — начало дня после последнего.
 */
export function dateRangeToParams(
  from: Date | null,
  to: Date | null,
): { from?: string; to?: string } {
  return {
    from: from ? toOffsetIso(startOfDay(from)) : undefined,
    to: to ? toOffsetIso(addDays(to, 1)) : undefined,
  }
}

const dayMonthYearFormat = new Intl.DateTimeFormat('ru', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

/** «сегодня в 18:40», «вчера в 18:40», «12 ноября в 18:40», «12 ноября 2025 г. в 18:40». */
export function formatCreatedAt(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  const day = startOfDay(date).getTime()
  if (day === startOfDay(now).getTime()) return `сегодня в ${time}`
  if (day === addDays(now, -1).getTime()) return `вчера в ${time}`
  const label =
    date.getFullYear() === now.getFullYear()
      ? dayMonthFormat.format(date)
      : dayMonthYearFormat.format(date)
  return `${label} в ${time}`
}

/** День для плитки «Когда»: «вс, 1 ноября» (год — если не текущий) и время «19:00». */
export function formatEventDay(iso: string, now: Date = new Date()): { day: string; time: string } {
  // formatEventDate: «вс, 1 ноября, 19:00» — день недели, дата, время
  const [weekday = '', date = '', time = ''] = formatEventDate(iso, now).split(', ')
  return { day: `${weekday}, ${date}`, time }
}
