/**
 * Иконки категорий. Имя приходит из БД (`category.icon`); показываем только известные
 * иконки primeicons, иначе — общая иконка, чтобы не было пустого места на месте глифа.
 */
export const FALLBACK_CATEGORY_ICON = 'pi-tag'

const KNOWN_ICONS = new Set([
  'pi-th-large',
  'pi-map',
  'pi-bolt',
  'pi-video',
  'pi-tag',
  'pi-star',
  'pi-heart',
  'pi-book',
  'pi-camera',
  'pi-car',
  'pi-globe',
  'pi-graduation-cap',
  'pi-palette',
  'pi-sun',
  'pi-moon',
  'pi-trophy',
  'pi-users',
  'pi-gift',
  'pi-compass',
  'pi-headphones',
  'pi-microphone',
  'pi-image',
  'pi-flag',
])

export function categoryIcon(icon: string | null | undefined): string {
  return icon && KNOWN_ICONS.has(icon) ? icon : FALLBACK_CATEGORY_ICON
}
