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
