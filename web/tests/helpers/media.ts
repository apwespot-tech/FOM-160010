/**
 * Эмуляция matchMedia для jsdom (в нём нет вёрстки и media queries).
 * Поддерживает (min-width: Npx) и (max-width: Npx) и уведомляет слушателей при смене ширины.
 */
type Listener = (event: MediaQueryListEvent) => void

let width = 1280
const lists = new Set<{ query: string; listeners: Set<Listener>; last: boolean }>()

function evaluate(query: string): boolean {
  const min = /\(min-width:\s*(\d+)px\)/.exec(query)
  const max = /\(max-width:\s*(\d+)px\)/.exec(query)
  if (min && width < Number(min[1])) return false
  if (max && width > Number(max[1])) return false
  return Boolean(min || max)
}

export function installMatchMedia(): void {
  lists.clear()
  window.matchMedia = (query: string) => {
    const entry = { query, listeners: new Set<Listener>(), last: evaluate(query) }
    lists.add(entry)
    return {
      get matches() {
        return evaluate(query)
      },
      media: query,
      onchange: null,
      addEventListener: (_type: string, listener: Listener) => entry.listeners.add(listener),
      removeEventListener: (_type: string, listener: Listener) => entry.listeners.delete(listener),
      addListener: (listener: Listener) => entry.listeners.add(listener),
      removeListener: (listener: Listener) => entry.listeners.delete(listener),
      dispatchEvent: () => true,
    } as unknown as MediaQueryList
  }
}

export function setViewportWidth(value: number): void {
  width = value
  for (const entry of lists) {
    const matches = evaluate(entry.query)
    if (matches !== entry.last) {
      entry.last = matches
      for (const listener of entry.listeners) {
        listener({ matches, media: entry.query } as MediaQueryListEvent)
      }
    }
  }
}
