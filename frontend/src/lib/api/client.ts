import type { ChartSpec } from '$lib/stores/expenses'

const BASE_URL =
    import.meta.env.VITE_API_URL ??
    (typeof window !== 'undefined'
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : 'http://localhost:8000')

const WRITE_PATHS = [
    '/expenses',
    '/expenses/',
    '/payments',
    '/payments/',
    '/agent/message',
    '/agent/audio',
    '/agent/image',
    '/gastos',
    '/agente/mensaje',
    '/agente/audio',
    '/agente/imagen',
]

function esEscritura(method: string, path: string): boolean {
    const m = method.toUpperCase()
    if (m === 'GET') return false
    return WRITE_PATHS.some((p) => path.startsWith(p))
}

async function dispararRefetch() {
    try {
        const { invalidar } = await import('$lib/stores/appState.svelte')
        await invalidar()

        const dashboard = await import('$lib/stores/dashboard.svelte')
        await dashboard.loadDashboard()
    } catch {
        // El refetch no debe romper la operacion principal.
    }
}

function ddmmToIso(value?: string | null) {
    if (!value) return undefined
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) return value

    const [day, month] = value.split('/')
    if (!day || !month) return undefined

    const year = new Date().getFullYear()
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T00:00:00`
}

type StreamHandlers = {
    onToken: (text: string) => void
    onError?: (message: string) => void
    onDone?: () => void
    onThinking?: (agent: string, status: string, label: string) => void
    onChart?: (chart: ChartSpec) => void
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const method = options?.method ?? 'GET'
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    })

    if (!res.ok) {
        throw new Error(`Error ${res.status}: ${res.statusText}`)
    }

    const data = res.json() as Promise<T>

    if (esEscritura(method, path)) {
        dispararRefetch()
    }

    return data
}

async function streamRequest(path: string, options: RequestInit, handlers: StreamHandlers) {
    const res = await fetch(`${BASE_URL}${path}`, options)

    if (!res.ok) {
        throw new Error(`Error ${res.status}: ${res.statusText}`)
    }
    if (!res.body) {
        throw new Error('El navegador no soporta streaming de respuestas.')
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    function processEvent(rawEvent: string) {
        const eventLine = rawEvent.split('\n').find((line) => line.startsWith('event: '))
        const dataLine = rawEvent.split('\n').find((line) => line.startsWith('data: '))
        if (!eventLine || !dataLine) return

        const event = eventLine.slice(7).trim()
        const data = JSON.parse(dataLine.slice(6))

        if (event === 'token') handlers.onToken(data.text ?? '')
        if (event === 'error') handlers.onError?.(data.message ?? 'No pude procesar tu mensaje.')
        if (event === 'thinking') handlers.onThinking?.(data.agent, data.status, data.label)
        if (event === 'chart') handlers.onChart?.(data)
        if (event === 'done') {
            handlers.onDone?.()
            if (esEscritura(options.method ?? 'POST', path)) {
                dispararRefetch()
            }
        }
    }

    while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''
        for (const event of events) {
            processEvent(event)
        }
    }

    buffer += decoder.decode()
    if (buffer.trim()) processEvent(buffer)
}

export const api = {
    getExpenses(mes?: string) {
        const query = mes ? `?month=${mes}` : ''
        return request<any[]>(`/expenses${query}`)
    },

    createExpense(datos: {
        type: string
        category: string
        amount: number
        date: string
        due_date?: string
        paid: boolean
        notes?: string
    }) {
        return request('/expenses', {
            method: 'POST',
            body: JSON.stringify(datos),
        })
    },

    markPaid(id: string) {
        return request(`/expenses/${id}/pay`, {
            method: 'PATCH',
        })
    },

    updateExpense(
        id: string,
        datos: {
            type?: string
            category?: string
            amount?: number
            date?: string
            due_date?: string | null
            paid?: boolean
            notes?: string | null
        },
    ) {
        return request(`/payments/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                amount: datos.amount,
                payment_date: ddmmToIso(datos.date),
                due_date: ddmmToIso(datos.due_date),
                status: datos.paid === undefined ? undefined : datos.paid ? 'paid' : 'pending',
                notes: datos.type,
                metadata: datos.notes ? { notas: datos.notes } : undefined,
            }),
        })
    },

    deleteExpense(id: string) {
        return request<{ deleted: string }>(`/payments/${id}`, {
            method: 'DELETE',
        })
    },

    sendMessage(text: string) {
        return request<{ response: string }>('/agent/message', {
            method: 'POST',
            body: JSON.stringify({ text }),
        })
    },

    streamMessage(text: string, handlers: StreamHandlers) {
        return streamRequest(
            '/agent/message/stream',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            },
            handlers,
        )
    },

    async sendAudio(blob: Blob) {
        const form = new FormData()
        form.append('audio', blob, 'grabacion.wav')

        const res = await fetch(`${BASE_URL}/agent/audio`, {
            method: 'POST',
            body: form,
        })

        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.json() as Promise<{ response: string }>
    },

    streamAudio(blob: Blob, handlers: StreamHandlers) {
        const form = new FormData()
        form.append('audio', blob, 'grabacion.wav')

        return streamRequest('/agent/audio/stream', {
            method: 'POST',
            body: form,
        }, handlers)
    },

    async sendImage(file: File) {
        const form = new FormData()
        form.append('image', file)

        const res = await fetch(`${BASE_URL}/agent/image`, {
            method: 'POST',
            body: form,
        })

        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.json() as Promise<{ response: string }>
    },

    streamImage(file: File, handlers: StreamHandlers) {
        const form = new FormData()
        form.append('image', file)

        return streamRequest('/agent/image/stream', {
            method: 'POST',
            body: form,
        }, handlers)
    },

    getFinance(mes?: string) {
        const query = mes ? `?month=${mes}` : ''
        return request<{
            period: string
            salary: number | null
            budget: number | null
            currency: string
            notes: string | null
        }>(`/finance${query}`)
    },

    getSummary(mes?: string) {
        const query = mes ? `?month=${mes}` : ''
        return request<{
            total: number
            paid: number
            pending: number
            payments_count: number
            pending_count: number
        }>(`/summary${query}`)
    },
}
