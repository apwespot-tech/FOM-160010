/** Ошибка API: HTTP-статус и машинный код из `detail.code` (или `validation_error` для 422). */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryAfter: number | undefined
  /** Поля, на которые указывает ошибка валидации (последний элемент `loc`). */
  readonly fields: string[]
  /** Номер загруженного файла, к которому относится ошибка (`detail.file`). */
  readonly file: number | undefined

  constructor(
    status: number,
    code: string,
    message: string,
    options: { retryAfter?: number; fields?: string[]; file?: number } = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfter = options.retryAfter
    this.fields = options.fields ?? []
    this.file = options.file
  }
}

export const NETWORK_ERROR = 'network_error'

interface AuthProvider {
  getAccessToken(): string | null
  /** Обновляет токены; возвращает новый access-токен или null, если сессия завершена. */
  refresh(): Promise<string | null>
}

let authProvider: AuthProvider | null = null
let refreshPromise: Promise<string | null> | null = null

export function configureAuth(provider: AuthProvider | null): void {
  authProvider = provider
  refreshPromise = null
}

/**
 * Single-flight обновление токенов: одновременные вызовы получают один и тот же промис.
 * Иначе второй запрос предъявил бы уже погашенный (ротированный) refresh-токен.
 */
export function refreshAccessToken(): Promise<string | null> {
  if (!authProvider) return Promise.resolve(null)
  if (!refreshPromise) {
    refreshPromise = authProvider.refresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  /** JSON-тело или `FormData` (multipart: границу проставляет браузер). */
  body?: unknown
  /** Добавить access-токен и обновить его при 401. */
  auth?: boolean
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await request(path, options, 'application/json')
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Файл (например, фото) с той же авторизацией и обновлением токена, что и у JSON-запросов. */
export async function apiFetchBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  const response = await request(path, options, '*/*')
  return response.blob()
}

async function request(path: string, options: RequestOptions, accept: string): Promise<Response> {
  const { method = 'GET', body, auth = false } = options
  const isForm = body instanceof FormData

  const send = async (token: string | null): Promise<Response> => {
    const headers: Record<string, string> = { Accept: accept }
    if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json'
    if (token) headers.Authorization = `Bearer ${token}`
    try {
      return await fetch(`/api${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
      })
    } catch {
      throw new ApiError(0, NETWORK_ERROR, 'Нет связи с сервером')
    }
  }

  const usedToken = auth ? (authProvider?.getAccessToken() ?? null) : null
  let response = await send(usedToken)

  if (response.status === 401 && auth && authProvider) {
    // Пока запрос шёл, токен мог уже обновить другой запрос — тогда просто повторяем
    const current = authProvider.getAccessToken()
    const nextToken = current && current !== usedToken ? current : await refreshAccessToken()
    if (nextToken) response = await send(nextToken)
  }

  if (!response.ok) throw await toApiError(response)
  return response
}

interface ErrorDetail {
  code?: string
  message?: string
  retry_after?: number
  /** Номер файла в запросе, к которому относится ошибка (фото). */
  file?: number
}

interface ValidationIssue {
  loc?: (string | number)[]
  msg?: string
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    // тело не JSON
  }
  const detail = (payload as { detail?: unknown } | null)?.detail

  if (Array.isArray(detail)) {
    const issues = detail as ValidationIssue[]
    const fields = issues
      .map((issue) => issue.loc?.[issue.loc.length - 1])
      .filter((field): field is string => typeof field === 'string')
    return new ApiError(response.status, 'validation_error', issues[0]?.msg ?? 'Ошибка валидации', {
      fields,
    })
  }

  if (detail && typeof detail === 'object') {
    const { code, message, retry_after: retryAfter, file } = detail as ErrorDetail
    const headerRetry = Number(response.headers.get('Retry-After'))
    return new ApiError(response.status, code ?? `http_${response.status}`, message ?? '', {
      retryAfter:
        retryAfter ?? (Number.isFinite(headerRetry) && headerRetry > 0 ? headerRetry : undefined),
      file: typeof file === 'number' ? file : undefined,
    })
  }

  return new ApiError(response.status, `http_${response.status}`, response.statusText)
}
