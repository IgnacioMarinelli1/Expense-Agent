/**
 * gastos.ts — Re-exporta tipos y el store de mensajes del chat.
 * Los datos de gastos y resumen ahora viven en appState.svelte.ts
 */
import { writable } from 'svelte/store'

// Re-exporta Gasto desde el store centralizado para compatibilidad
export type { Gasto } from './appState.svelte.ts'

export type Mensaje = {
    id: number
    tipo: 'usuario' | 'agente'
    texto: string
    cargando?: boolean
    fileUrl?: string
    fileType?: 'image' | 'pdf'
}

// Store de chat (sigue siendo writable de Svelte — es solo UI local)
export const mensajes = writable<Mensaje[]>([
    {
        id: 1,
        tipo: 'agente',
        texto: '¡Hola! Soy tu asistente de pagos. Podés decirme cosas como "Pagué la luz $18.500" o "¿Cuánto gasté este mes?"'
    }
])

// Store de estado de carga del chat
export const cargando = writable(false)