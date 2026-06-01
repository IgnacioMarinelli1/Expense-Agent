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
    _cargando = true
    _error = ''
    try {
        const [gastosData, resumenData] = await Promise.all([
            api.getGastos(mes),
            api.getResumen(mes)
        ])
        _gastos = gastosData as Gasto[]
        _resumen = resumenData
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