import { writable } from 'svelte/store'

export type Gasto = {
    id: string
    tipo: string
    categoria: string
    monto: number
    fecha: string
    vencimiento?: string
    pagado: boolean
    notas?: string
}

export type Mensaje = {
    id: number
    tipo: 'usuario' | 'agente'
    texto: string
    cargando?: boolean
}

// Store de gastos
export const gastos = writable<Gasto[]>([])

// Store del chat
export const mensajes = writable<Mensaje[]>([
    {
        id: 1,
        tipo: 'agente',
        texto: '¡Hola! Soy tu asistente de pagos. Podés decirme cosas como "Pagué la luz $18.500" o "¿Cuánto gasté este mes?"'
    }
])

// Store de estado de carga
export const cargando = writable(false)