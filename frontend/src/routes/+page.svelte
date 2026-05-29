<script lang="ts">
    import { mensajes, cargando } from '$lib/stores/gastos'
    import { api } from '$lib/api/client'
    import { Bot, Mic, Square, ArrowUp } from '@lucide/svelte'

    let inputText = $state('')
    let isRecording = $state(false)
    let mediaRecorder: MediaRecorder | null = null
    let chunks: Blob[] = []

    function encodeWav(audioBuffer: AudioBuffer) {
        const channels = audioBuffer.numberOfChannels
        const sampleRate = audioBuffer.sampleRate
        const samples = audioBuffer.length
        const bytesPerSample = 2
        const blockAlign = channels * bytesPerSample
        const buffer = new ArrayBuffer(44 + samples * blockAlign)
        const view = new DataView(buffer)

        writeString(view, 0, 'RIFF')
        view.setUint32(4, 36 + samples * blockAlign, true)
        writeString(view, 8, 'WAVE')
        writeString(view, 12, 'fmt ')
        view.setUint32(16, 16, true)
        view.setUint16(20, 1, true)
        view.setUint16(22, channels, true)
        view.setUint32(24, sampleRate, true)
        view.setUint32(28, sampleRate * blockAlign, true)
        view.setUint16(32, blockAlign, true)
        view.setUint16(34, 16, true)
        writeString(view, 36, 'data')
        view.setUint32(40, samples * blockAlign, true)

        let offset = 44
        const channelData = Array.from({ length: channels }, (_, i) => audioBuffer.getChannelData(i))
        for (let i = 0; i < samples; i += 1) {
            for (let channel = 0; channel < channels; channel += 1) {
                const sample = Math.max(-1, Math.min(1, channelData[channel][i]))
                view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
                offset += bytesPerSample
            }
        }

        return new Blob([view], { type: 'audio/wav' })
    }

    function writeString(view: DataView, offset: number, value: string) {
        for (let i = 0; i < value.length; i += 1) {
            view.setUint8(offset + i, value.charCodeAt(i))
        }
    }

    async function convertirAWav(blob: Blob) {
        const AudioContextClass =
            window.AudioContext ||
            (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
        if (!AudioContextClass) {
            throw new Error('AudioContext no está disponible en este navegador.')
        }
        const audioContext = new AudioContextClass()
        try {
            const audioBuffer = await audioContext.decodeAudioData(await blob.arrayBuffer())
            return encodeWav(audioBuffer)
        } finally {
            await audioContext.close()
        }
    }

    async function enviarMensaje() {
        if (!inputText.trim()) return

        const texto = inputText
        inputText = ''

        // Agregar mensaje del usuario
        mensajes.update(m => [...m, { id: Date.now(), tipo: 'usuario', texto }])

        // Agregar burbuja de "escribiendo..."
        const idCargando = Date.now() + 1
        mensajes.update(m => [...m, { id: idCargando, tipo: 'agente', texto: '...', cargando: true }])

        try {
            const res = await api.enviarMensaje(texto)
            mensajes.update(m =>
                m.map(msg => msg.id === idCargando
                    ? { ...msg, texto: res.respuesta, cargando: false }
                    : msg
                )
            )
        } catch {
            mensajes.update(m =>
                m.map(msg => msg.id === idCargando
                    ? { ...msg, texto: 'Hubo un error al conectar con el agente. ¿El backend está corriendo?', cargando: false }
                    : msg
                )
            )
        }
    }

    async function toggleGrabacion() {
        if (isRecording) {
            mediaRecorder?.stop()
            isRecording = false
            return
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            mediaRecorder = new MediaRecorder(stream)
            chunks = []

            mediaRecorder.ondataavailable = e => chunks.push(e.data)

            mediaRecorder.onstop = async () => {
                mensajes.update(m => [...m, { id: Date.now(), tipo: 'usuario', texto: '🎙️ Audio enviado' }])
                const idCargando = Date.now() + 1
                mensajes.update(m => [...m, { id: idCargando, tipo: 'agente', texto: '...', cargando: true }])
                try {
                    const grabacion = new Blob(chunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
                    const wav = await convertirAWav(grabacion)
                    const res = await api.enviarAudio(wav)
                    mensajes.update(m =>
                        m.map(msg => msg.id === idCargando
                            ? { ...msg, texto: res.respuesta, cargando: false }
                            : msg
                        )
                    )
                } catch (e) {
                    console.error(e)
                    mensajes.update(m =>
                        m.map(msg => msg.id === idCargando
                            ? { ...msg, texto: 'No pude procesar el audio.', cargando: false }
                            : msg
                        )
                    )
                }
                stream.getTracks().forEach(t => t.stop())
            }

            mediaRecorder.start()
            isRecording = true
        } catch {
            alert('No se pudo acceder al micrófono.')
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            enviarMensaje()
        }
    }
</script>

<div class="flex h-[calc(100vh-120px)] flex-col">

    <div class="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
        {#each $mensajes as mensaje (mensaje.id)}
            <div
                class="flex items-end gap-2 {mensaje.tipo === 'usuario'
                    ? 'justify-end'
                    : 'justify-start'}"
            >
                {#if mensaje.tipo === 'agente'}
                    <div
                        class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
                    >
                        <Bot class="size-4" />
                    </div>
                {/if}
                <div
                    class="max-w-[80%] px-4 py-2.5 text-sm leading-relaxed shadow-sm {mensaje.tipo === 'usuario'
                        ? 'rounded-2xl rounded-br-sm bg-primary text-primary-foreground'
                        : 'rounded-2xl rounded-bl-sm bg-secondary text-foreground'}"
                >
                    {#if mensaje.cargando}
                        <span class="flex items-center gap-1 py-1" aria-label="Escribiendo">
                            <span class="size-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.3s]"></span>
                            <span class="size-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.15s]"></span>
                            <span class="size-1.5 animate-bounce rounded-full bg-current opacity-60"></span>
                        </span>
                    {:else}
                        {mensaje.texto}
                    {/if}
                </div>
            </div>
        {/each}
    </div>

    <div class="flex items-end gap-2 border-t border-border bg-card p-4">
        <textarea
            bind:value={inputText}
            onkeydown={handleKeydown}
            placeholder="Escribí un pago o mandá un audio..."
            rows={1}
            class="flex-1 resize-none rounded-xl border border-border bg-secondary px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
        ></textarea>

        <button
            onclick={toggleGrabacion}
            aria-label={isRecording ? 'Detener grabación' : 'Grabar audio'}
            class="flex size-11 shrink-0 items-center justify-center rounded-full transition-all active:scale-95 {isRecording
                ? 'bg-destructive text-destructive-foreground animate-pulse'
                : 'bg-secondary text-foreground hover:bg-muted'}"
        >
            {#if isRecording}
                <Square class="size-5" />
            {:else}
                <Mic class="size-5" />
            {/if}
        </button>

        <button
            onclick={enviarMensaje}
            disabled={!inputText.trim()}
            aria-label="Enviar mensaje"
            class="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-40 disabled:active:scale-100"
        >
            <ArrowUp class="size-5" />
        </button>
    </div>
</div>
