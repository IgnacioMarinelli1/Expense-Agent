<script lang="ts">
    import { mensajes } from '$lib/stores/gastos'
    import { api } from '$lib/api/client'
    import { Bot, Mic, Square, ArrowUp, Camera } from '@lucide/svelte'

    let inputText = $state('')
    let isRecording = $state(false)
    let isStreaming = $state(false)
    let mediaRecorder: MediaRecorder | null = null
    let chunks: Blob[] = []
    let fileInput: HTMLInputElement | undefined = $state()

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

    function addAgentStreamMessage() {
        const id = Date.now() + 1
        mensajes.update(m => [...m, { id, tipo: 'agente', texto: '', cargando: true }])
        return id
    }

    function updateAgentMessage(id: number, texto: string, cargando = false) {
        mensajes.update(m =>
            m.map(msg => msg.id === id
                ? { ...msg, texto, cargando }
                : msg
            )
        )
    }

    async function streamIntoMessage(
        id: number,
        startStream: (handlers: {
            onToken: (token: string) => void
            onError: (message: string) => void
        }) => Promise<void>,
        fallback: string
    ) {
        isStreaming = true
        let responseText = ''
        try {
            await startStream({
                onToken: token => {
                    responseText += token
                    updateAgentMessage(id, responseText, true)
                },
                onError: message => {
                    responseText = responseText ? `${responseText}\n\n${message}` : message
                    updateAgentMessage(id, responseText, false)
                }
            })
            mensajes.update(m =>
                m.map(msg => msg.id === id
                    ? { ...msg, texto: msg.texto || 'No pude procesar tu mensaje.', cargando: false }
                    : msg
                )
            )
        } catch (e) {
            console.error(e)
            updateAgentMessage(id, fallback, false)
        } finally {
            isStreaming = false
        }
    }

    async function enviarMensaje() {
        if (!inputText.trim() || isStreaming) return

        const texto = inputText
        inputText = ''

        // Agregar mensaje del usuario
        mensajes.update(m => [...m, { id: Date.now(), tipo: 'usuario', texto }])

        const idCargando = addAgentStreamMessage()
        await streamIntoMessage(
            idCargando,
            handlers => api.streamMensaje(texto, handlers),
            'Hubo un error al conectar con el agente. ¿El backend está corriendo?'
        )
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
                const idCargando = addAgentStreamMessage()
                try {
                    const grabacion = new Blob(chunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
                    const wav = await convertirAWav(grabacion)
                    await streamIntoMessage(
                        idCargando,
                        handlers => api.streamAudio(wav, handlers),
                        'No pude procesar el audio.'
                    )
                } catch (e) {
                    console.error(e)
                    updateAgentMessage(idCargando, 'No pude procesar el audio.', false)
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

    async function handleImageUpload(e: Event) {
        const input = e.target as HTMLInputElement
        if (!input.files?.length || isStreaming) return
        
        const file = input.files[0]
        input.value = '' // reset
        
        const fileUrl = URL.createObjectURL(file)
        const fileType = file.type === 'application/pdf' ? 'pdf' : 'image'
        
        mensajes.update(m => [...m, { id: Date.now(), tipo: 'usuario', texto: '', fileUrl, fileType }])
        const idCargando = addAgentStreamMessage()
        await streamIntoMessage(
            idCargando,
            handlers => api.streamImagen(file, handlers),
            'No pude procesar la imagen.'
        )
    }
</script>

<div class="mx-auto flex h-full w-full flex-col">

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
                    {#if mensaje.cargando && !mensaje.texto}
                        <span class="flex items-center gap-1 py-1" aria-label="Escribiendo">
                            <span class="size-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.3s]"></span>
                            <span class="size-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.15s]"></span>
                            <span class="size-1.5 animate-bounce rounded-full bg-current opacity-60"></span>
                        </span>
                    {:else if mensaje.fileUrl}
                        <div class="flex flex-col gap-2">
                            {#if mensaje.fileType === 'pdf'}
                                <div class="flex items-center gap-2 pb-1 border-b border-primary/20">
                                    <span class="text-xl">📄</span>
                                    <span class="font-medium">Documento PDF</span>
                                </div>
                                <embed src={mensaje.fileUrl} type="application/pdf" class="h-[300px] w-full min-w-[200px] sm:h-[400px] sm:w-[350px] rounded-md bg-white object-cover shadow-inner" />
                            {:else}
                                <img src={mensaje.fileUrl} alt="Preview" class="max-h-[300px] max-w-full sm:max-h-[400px] sm:max-w-[350px] rounded-md object-contain shadow-inner" />
                            {/if}
                            {#if mensaje.texto}
                                <span>{mensaje.texto}</span>
                            {/if}
                        </div>
                    {:else}
                        {mensaje.texto}
                    {/if}
                </div>
            </div>
        {/each}
    </div>

    <div class="flex items-end gap-2 border-t border-border bg-card p-4">
        <input 
            type="file" 
            accept="image/*,application/pdf" 
            capture="environment" 
            hidden 
            bind:this={fileInput}
            onchange={handleImageUpload}
        />
        <button
            onclick={() => fileInput?.click()}
            disabled={isStreaming}
            aria-label="Subir imagen"
            class="flex size-11 shrink-0 items-center justify-center rounded-full transition-all active:scale-95 bg-secondary text-foreground hover:bg-muted disabled:opacity-40 disabled:active:scale-100"
        >
            <Camera class="size-5" />
        </button>

        <textarea
            bind:value={inputText}
            onkeydown={handleKeydown}
            placeholder="Escribí un pago o mandá un audio..."
            rows={1}
            disabled={isStreaming}
            class="flex-1 resize-none rounded-xl border border-border bg-secondary px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
        ></textarea>

        <button
            onclick={toggleGrabacion}
            disabled={isStreaming && !isRecording}
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
            disabled={!inputText.trim() || isStreaming}
            aria-label="Enviar mensaje"
            class="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-40 disabled:active:scale-100"
        >
            <ArrowUp class="size-5" />
        </button>
    </div>
</div>