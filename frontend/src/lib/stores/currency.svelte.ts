/**
 * currency.svelte.ts
 * Conversion y formato de moneda global (Svelte 5 runes).
 *
 * Modelo: cada gasto se guarda en su moneda nativa (ARS o USD). El sistema
 * normaliza internamente a ARS como base de calculo y convierte a la moneda
 * de visualizacion (`display`) al momento de renderizar, usando la cotizacion
 * blue en vivo. Asi nada se pierde y el toggle ARS/USD reformatea al instante
 * sin necesidad de volver a pedir datos.
 *
 * `rates` = ARS por 1 unidad de la moneda. ARS=1, USD=cotizacion blue venta.
 */

import { api } from '$lib/api/client'

export type CurrencyCode = 'ARS' | 'USD'

const STORAGE_KEY = 'al-dia-currency'

function loadDisplay(): CurrencyCode {
    if (typeof localStorage === 'undefined') return 'ARS'
    return localStorage.getItem(STORAGE_KEY) === 'USD' ? 'USD' : 'ARS'
}

let _rates = $state<Record<string, number>>({ ARS: 1 })
let _display = $state<CurrencyCode>(loadDisplay())
let _loaded = $state(false)
let _inflight: Promise<void> | null = null

export async function loadRates(): Promise<void> {
    try {
        const fx = await api.getFx()
        const rates = fx?.rates ?? {}
        // Garantizamos ARS=1 siempre presente.
        _rates = { ...rates, ARS: rates.ARS ?? 1 }
        _loaded = true
    } catch {
        // Si falla la cotizacion, todo queda en ARS (sin conversion).
        _rates = { ARS: 1 }
    }
}

/** Carga las cotizaciones una sola vez (idempotente). */
export function ensureRates(): Promise<void> {
    if (_loaded) return Promise.resolve()
    if (!_inflight) _inflight = loadRates().finally(() => { _inflight = null })
    return _inflight
}

export function setDisplayCurrency(code: CurrencyCode): void {
    _display = code
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, code)
}

export function toggleCurrency(): void {
    setDisplayCurrency(_display === 'ARS' ? 'USD' : 'ARS')
}

/** Convierte un valor en `from` a la base ARS. */
export function toArs(value: number, from: string = 'ARS'): number {
    const rate = _rates[from] ?? 1
    return Number(value ?? 0) * rate
}

/** Convierte un valor base ARS a la moneda de visualizacion actual. */
export function display(arsValue: number): number {
    const rate = _rates[_display] ?? 1
    return Number(arsValue ?? 0) / rate
}

function symbol(): string {
    return _display === 'USD' ? 'US$' : '$'
}

/** Formatea un valor base ARS en la moneda de visualizacion. */
export function formatArs(arsValue: number | null | undefined): string {
    const v = display(Number(arsValue ?? 0))
    // USD chico (< 1000) mostramos con decimales para no perder precision.
    const maxFraction = _display === 'USD' && Math.abs(v) < 1000 ? 2 : 0
    return symbol() + v.toLocaleString('es-AR', { maximumFractionDigits: maxFraction })
}

/** Formatea un valor en moneda nativa `from` (lo lleva a ARS y luego a display). */
export function formatAmount(value: number | null | undefined, from: string = 'ARS'): string {
    return formatArs(toArs(Number(value ?? 0), from))
}

export const currency = {
    get display() { return _display },
    get rates() { return _rates },
    get loaded() { return _loaded },
    get usdRate() { return _rates.USD ?? null },
}
