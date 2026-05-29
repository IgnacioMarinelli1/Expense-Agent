// URL del backend — cuando Dev 2 tenga el servidor listo, cambiás esta línea
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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
