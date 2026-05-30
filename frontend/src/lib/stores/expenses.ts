import { writable } from 'svelte/store'

export type Expense = {
    id: string
    type: string
    category: string
    amount: number
    date: string
    due_date?: string
    paid: boolean
    notes?: string
}

export type TraceStatus = 'running' | 'done' | 'error'

export type TraceStep = {
    agent: string
    label: string
    status: TraceStatus
}

export type ChartSpec = {
    id: string
    title: string
    subtitle?: string
    mode: '2d' | '3d'
    chartType: string
    option: Record<string, unknown>
    insights: string[]
    source: Record<string, unknown>
    generatedAt: string
}

export type Message = {
    id: number
    type: 'usuario' | 'agente'
    text: string
    loading?: boolean
    fileUrl?: string
    fileType?: 'image' | 'pdf'
    traces?: TraceStep[]
    charts?: ChartSpec[]
}

// Store de gastos
export const expenses = writable<Expense[]>([])

// Store del chat
export const messages = writable<Message[]>([
    {
        id: 1,
        type: 'agente',
        text: '¡Hola! Soy tu asistente de pagos. Podés decirme cosas como "Pagué la luz $18.500" o "¿Cuánto gasté este mes?"'
    }
])

// Store de estado de carga
export const loading = writable(false)
