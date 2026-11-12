export type ShareResult = 'shared' | 'copied' | 'cancelled' | 'manual'

/**
 * Поделиться ссылкой: системное меню, если браузер его поддерживает; иначе — копирование
 * в буфер обмена. 'manual' — ни то ни другое недоступно, ссылку нужно показать пользователю.
 */
export async function shareLink(url: string, title: string): Promise<ShareResult> {
  if (typeof navigator.share === 'function') {
    try {
      await navigator.share({ url, title })
      return 'shared'
    } catch (error) {
      // Пользователь закрыл системное меню — это не ошибка
      if (error instanceof DOMException && error.name === 'AbortError') return 'cancelled'
    }
  }
  try {
    await navigator.clipboard.writeText(url)
    return 'copied'
  } catch {
    return 'manual'
  }
}
