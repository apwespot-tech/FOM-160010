/** Инициалы: первые буквы двух первых слов имени. */
export function initials(name: string | null): string {
  if (!name) return ''
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join('')
}

/** Русское склонение: plural(25, ['год', 'года', 'лет']) -> 'лет'. */
export function plural(count: number, forms: [string, string, string]): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return forms[0]
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1]
  return forms[2]
}

export function formatAge(age: number): string {
  return `${age} ${plural(age, ['год', 'года', 'лет'])}`
}

/** +79991234567 -> +7 999 123-45-67; прочие номера без изменений. */
export function formatPhone(phone: string): string {
  const match = /^\+7(\d{3})(\d{3})(\d{2})(\d{2})$/.exec(phone)
  if (!match) return phone
  return `+7 ${match[1]} ${match[2]}-${match[3]}-${match[4]}`
}

/** «Осталось 3 из 10 мест» или «Мест нет». */
export function formatPlaces(free: number, max: number): string {
  if (free <= 0) return 'Мест нет'
  return `Осталось ${free} из ${max} ${plural(max, ['места', 'мест', 'мест'])}`
}

/** 18 -> «18+». */
export function formatMinAge(age: number): string {
  return `${age}+`
}

/** 4.8 -> «4,8», 5 -> «5,0». */
export function formatRating(value: number): string {
  return value.toFixed(1).replace('.', ',')
}

/** «1 отзыв», «3 отзыва», «12 отзывов». */
export function pluralReviews(count: number): string {
  return `${count} ${plural(count, ['отзыв', 'отзыва', 'отзывов'])}`
}

/** «@boris_k» -> https://t.me/boris_k */
export function telegramUrl(telegram: string): string {
  return `https://t.me/${telegram.replace(/^@/, '')}`
}

/** «осталось 7 свободных мест» */
export function formatFreePlaces(free: number): string {
  if (free <= 0) return 'свободных мест нет'
  const left = plural(free, ['остался', 'осталось', 'осталось'])
  const places = plural(free, ['свободное место', 'свободных места', 'свободных мест'])
  return `${left} ${free} ${places}`
}
