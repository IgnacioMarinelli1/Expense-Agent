// URL del backend — cuando Dev 2 tenga el servidor listo, cambiás esta línea
const BASE_URL = import.meta.env.VITE_API_URL ?? (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8000` : 'http://localhost:8000')

type StreamHandlers = {
    onToken: (text: string) => void
    onError?: (message: string) => void
    onDone?: () => void
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    })

    if (!res.ok) {
        throw new Error(`Error ${res.status}: ${res.statusText}`)
    }

    return res.json()
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
        const eventLine = rawEvent.split('\n').find(line => line.startsWith('event: '))
        const dataLine = rawEvent.split('\n').find(line => line.startsWith('data: '))
        if (!eventLine || !dataLine) return

        const event = eventLine.slice(7).trim()
        const data = JSON.parse(dataLine.slice(6))

        if (event === 'token') handlers.onToken(data.text ?? '')
        if (event === 'error') handlers.onError?.(data.message ?? 'No pude procesar tu mensaje.')
        if (event === 'done') handlers.onDone?.()
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

// ── Gastos ──────────────────────────────────────────

export const api = {
    // Obtener todos los gastos del mes
    getExpenses(mes?: string) {
        const query = mes ? `?mes=${mes}` : ''
        return request<any[]>(`/expenses${query}`)
    },

    // Registrar un gasto nuevo
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
            body: JSON.stringify(datos)
        })
    },

    // Marcar un gasto como pagado
    markPaid(id: string) {
        return request(`/expenses/${id}/pay`, {
            method: 'PATCH'
        })
    },

    // ── Agente ────────────────────────────────────────

    // Enviar mensaje de texto al agente
    sendMessage(text: string) {
        return request<{ response: string }>('/agent/message', {
            method: 'POST',
            body: JSON.stringify({ text })
        })
    },

    streamMessage(text: string, handlers: StreamHandlers) {
        return streamRequest('/agent/message/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        }, handlers)
    },

    // Enviar audio al agente
    async sendAudio(blob: Blob) {
        const form = new FormData()
        form.append('audio', blob, 'grabacion.wav')

        const res = await fetch(`${BASE_URL}/agent/audio`, {
            method: 'POST',
            body: form
        })

        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.json() as Promise<{ respuesta: string }>
    },

    streamAudio(blob: Blob, handlers: StreamHandlers) {
        const form = new FormData()
        form.append('audio', blob, 'grabacion.wav')

        return streamRequest('/agent/audio/stream', {
            method: 'POST',
            body: form
        }, handlers)
    },

    // Enviar imagen al agente
    async sendImage(file: File) {
        const form = new FormData()
        form.append('image', file)

        const res = await fetch(`${BASE_URL}/agent/image`, {
            method: 'POST',
            body: form
        })

        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.json() as Promise<{ response: string }>
    },

    streamImage(file: File, handlers: StreamHandlers) {
        const form = new FormData()
        form.append('image', file)

        return streamRequest('/agent/image/stream', {
            method: 'POST',
            body: form
        }, handlers)
    },

    // ── Resumen ───────────────────────────────────────

    getSummary(mes?: string) {
        const query = mes ? `?mes=${mes}` : ''
        return request<{
            total: number
            paid: number
            pending: number
            payments_count: number
            pending_count: number
        }>(`/summary${query}`)
    }
}
