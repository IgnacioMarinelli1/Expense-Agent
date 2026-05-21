<script lang="ts">
    let inputText = ''
    let isRecording = false

    // Por ahora solo loguea — la lógica real va en Sprint 2
    function enviarMensaje() {
        if (!inputText.trim()) return
        console.log('Enviando:', inputText)
        inputText = ''
    }

    function toggleGrabacion() {
        isRecording = !isRecording
        console.log(isRecording ? 'Grabando...' : 'Grabación detenida')
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            enviarMensaje()
        }
    }
</script>

<div class="flex flex-col h-full" style="height: calc(100vh - 120px)">

    <!-- Área de mensajes -->
    <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3">

        <!-- Mensaje de bienvenida -->
        <div class="flex gap-3 items-start">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0"
                 style="background: hsl(var(--primary)); color: hsl(var(--primary-foreground))">
                AI
            </div>
            <div class="rounded-2xl rounded-tl-none px-4 py-3 max-w-xs text-sm"
                 style="background: hsl(var(--secondary))">
                ¡Hola! Soy tu asistente de pagos. Podés decirme cosas como:
                <ul class="mt-2 flex flex-col gap-1" style="color: hsl(var(--muted-foreground))">
                    <li>• "Pagué la luz $18.500"</li>
                    <li>• "¿Cuánto gasté este mes?"</li>
                    <li>• "Se vence el ABL el 30"</li>
                </ul>
            </div>
        </div>

    </div>

    <!-- Input -->
    <div class="p-4 border-t flex gap-2 items-end"
         style="background: hsl(var(--card))">

    <textarea
            bind:value={inputText}
            onkeydown={handleKeydown}
            placeholder="Escribí un pago o mandá un audio..."
            rows="1"
            class="flex-1 resize-none rounded-xl px-4 py-3 text-sm outline-none border transition-colors"
            style="background: hsl(var(--secondary)); border-color: hsl(var(--border))"
    />

        <!-- Botón grabar -->
        <button
                onclick={toggleGrabacion}
                class="w-11 h-11 rounded-full flex items-center justify-center transition-colors flex-shrink-0"
                style="background: {isRecording ? 'hsl(var(--cat-luz))' : 'hsl(var(--secondary))'}">
            {isRecording ? '⏹' : '🎙️'}
        </button>

        <!-- Botón enviar -->
        <button
                onclick={enviarMensaje}
                disabled={!inputText.trim()}
                class="w-11 h-11 rounded-full flex items-center justify-center transition-opacity flex-shrink-0"
                style="background: hsl(var(--primary)); color: hsl(var(--primary-foreground));
             opacity: {inputText.trim() ? '1' : '0.4'}">
            ↑
        </button>

    </div>
</div>