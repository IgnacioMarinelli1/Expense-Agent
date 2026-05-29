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
    getGastos(mes?: string) {
        const query = mes ? `?mes=${mes}` : ''
        return request<any[]>(`/gastos${query}`)
    },

    // Registrar un gasto nuevo
    crearGasto(datos: {
        tipo: string
        categoria: string
        monto: number
        fecha: string
        vencimiento?: string
        pagado: boolean
        notas?: string
    }) {
        return request('/gastos', {
            method: 'POST',
            body: JSON.stringify(datos)
        })
    },

    // Marcar un gasto como pagado
    marcarPagado(id: string) {
        return request(`/gastos/${id}/pagar`, {
            method: 'PATCH'
        })
    },

    // ── Agente ────────────────────────────────────────

    // Enviar mensaje de texto al agente
    enviarMensaje(texto: string) {
        return request<{ respuesta: string }>('/agente/mensaje', {
            method: 'POST',
            body: JSON.stringify({ texto })
        })
    },

    streamMensaje(texto: string, handlers: StreamHandlers) {
        return streamRequest('/agente/mensaje/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto })
        }, handlers)
    },

    // Enviar audio al agente
    async enviarAudio(blob: Blob) {
        const form = new FormData()
        form.append('audio', blob, 'grabacion.wav')

        const res = await fetch(`${BASE_URL}/agente/audio`, {
            method: 'POST',
            body: form
        })

        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.json() as Promise<{ respuesta: string }>
    },

    streamAudio(blob: Blob, handlers: StreamHandlers) {
        const form = new FormData()
        form.append('audio', blob, 'grabacion.wav')

        return streamRequest('/agente/audio/stream', {
            method: 'POST',
            body: form
        }, handlers)
    },

    // Enviar imagen al agente
    async enviarImagen(file: File) {
        const form = new FormData()
        form.append('imagen', file)

        const res = await fetch(`${BASE_URL}/agente/imagen`, {
            method: 'POST',
            body: form
        })

        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.json() as Promise<{ respuesta: string }>
    },

    streamImagen(file: File, handlers: StreamHandlers) {
        const form = new FormData()
        form.append('imagen', file)

        return streamRequest('/agente/imagen/stream', {
            method: 'POST',
            body: form
        }, handlers)
    },

    // ── Resumen ───────────────────────────────────────

    getResumen(mes?: string) {
        const query = mes ? `?mes=${mes}` : ''
        return request<{
            total: number
            pagado: number
            pendiente: number
            cantidad_pagos: number
            cantidad_pendientes: number
        }>(`/resumen${query}`)
    }
}
