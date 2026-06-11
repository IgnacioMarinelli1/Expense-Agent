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

export type DownloadSpec = {
    url: string
    filename: string
    label: string
}

export type Message = {
    id: number
    type: 'usuario' | 'agente'
    text: string
    loading?: boolean
    fileUrl?: string
    fileType?: 'image' | 'pdf' | 'file'
    fileName?: string
    traces?: TraceStep[]
    charts?: ChartSpec[]
    downloads?: DownloadSpec[]
}

// Store de gastos
export const expenses = writable<Expense[]>([])

const CHAT_STORAGE_KEY = 'al-dia-chat'

const mensajeInicial: Message[] = [
    {
        id: 1,
        type: 'agente',
        text: '¡Hola! Soy tu asistente de pagos. Podés decirme cosas como "Pagué la luz $18.500" o "¿Cuánto gasté este mes?"'
    }
]

function cargarChatGuardado(): Message[] {
    if (typeof localStorage === 'undefined') return mensajeInicial
    try {
        const raw = localStorage.getItem(CHAT_STORAGE_KEY)
        if (!raw) return mensajeInicial
        const parsed = JSON.parse(raw) as Message[]
        if (!Array.isArray(parsed) || parsed.length === 0) return mensajeInicial
        return parsed.map((m) => ({ ...m, loading: false }))
    } catch {
        return mensajeInicial
    }
}

// Store del chat: persiste en localStorage para sobrevivir recargas de página.
export const messages = writable<Message[]>(cargarChatGuardado())

if (typeof localStorage !== 'undefined') {
    messages.subscribe((value) => {
        try {
            const persistibles = value
                .filter((m) => !m.loading)
                .map(({ fileUrl, ...rest }) =>
                    // Los blob: URLs mueren al recargar; degradamos a chip de archivo.
                    fileUrl && rest.fileType !== 'file'
                        ? { ...rest, fileType: 'file' as const, fileName: rest.fileName ?? 'archivo adjunto' }
                        : rest,
                )
            localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(persistibles))
        } catch {
            // Si el storage está lleno o bloqueado, el chat sigue funcionando en memoria.
        }
    })
}

// Store de estado de carga
export const loading = writable(false)
