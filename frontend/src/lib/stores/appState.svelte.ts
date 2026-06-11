/**
 * appState.svelte.ts
 * Estado global reactivo (Svelte 5 runes) para gastos + resumen.
 * Todas las vistas leen de aquí; el cliente API llama a `invalidar()`
 * automáticamente tras cada escritura en la DB.
 */

import { api } from '$lib/api/client'

// ─── Tipos ────────────────────────────────────────────────────────────────────

export interface Gasto {
    id: string
    tipo: string
    categoria: string
    monto: number
    fecha: string
    vencimiento?: string
    pagado: boolean
    notas?: string
}

export interface ResumenData {
    total: number
    pagado: number
    pendiente: number
    cantidad_pagos: number
    cantidad_pendientes: number
}

// ─── Estado reactivo (Svelte 5 runes — $state en módulo) ─────────────────────

let _gastos             = $state<Gasto[]>([])
let _resumen            = $state<ResumenData>({ total: 0, pagado: 0, pendiente: 0, cantidad_pagos: 0, cantidad_pendientes: 0 })
let _cargando           = $state(false)
let _error              = $state('')
let _ultimaActualizacion = $state(0)

// ─── Función de refetch ───────────────────────────────────────────────────────

export async function invalidar(mes?: string): Promise<void> {
    // Sin mes explicito refrescamos el mes actual: si no, un refetch post-escritura
    // mezcla gastos de todos los periodos en la vista.
    const periodo = mes ?? new Date().toISOString().slice(0, 7)
    _cargando = true
    _error = ''
    try {
        const [gastosRaw, resumenRaw] = await Promise.all([
            api.getExpenses(periodo),
            api.getSummary(periodo)
        ])

        // Mapear del formato de la API (inglés) al formato interno (español)
        _gastos = (gastosRaw as any[]).map((e) => ({
            id:          e.id,
            tipo:        e.type,
            categoria:   e.category,
            monto:       e.amount,
            fecha:       e.date,
            vencimiento: e.due_date,
            pagado:      e.paid,
            notas:       e.notes,
        }))

        _resumen = {
            total:               resumenRaw.total,
            pagado:              resumenRaw.paid,
            pendiente:           resumenRaw.pending,
            cantidad_pagos:      resumenRaw.payments_count,
            cantidad_pendientes: resumenRaw.pending_count,
        }

        _ultimaActualizacion = Date.now()
    } catch (e) {
        _error = e instanceof Error ? e.message : 'Error al cargar datos'
    } finally {
        _cargando = false
    }
}

// ─── Objeto de estado exportado (proxy reactivo) ─────────────────────────────

export const appState = {
    get gastos()              { return _gastos },
    get resumen()             { return _resumen },
    get cargando()            { return _cargando },
    get error()               { return _error },
    get ultimaActualizacion() { return _ultimaActualizacion },
}