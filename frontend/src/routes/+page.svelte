<script lang="ts">
    import { mensajes, cargando } from '$lib/stores/gastos'
    import { api } from '$lib/api/client'

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

<div style="display: flex; flex-direction: column; height: calc(100vh - 120px);">

    <div style="
    flex: 1; overflow-y: auto;
    padding: 1rem;
    display: flex; flex-direction: column; gap: 0.75rem;
  ">
        {#each $mensajes as mensaje (mensaje.id)}
            <div style="
        display: flex;
        justify-content: {mensaje.tipo === 'usuario' ? 'flex-end' : 'flex-start'};
        align-items: flex-end; gap: 0.5rem;
      ">
                {#if mensaje.tipo === 'agente'}
                    <div style="
            width: 2rem; height: 2rem; border-radius: 50%;
            background: var(--primary); color: var(--primary-foreground);
            display: flex; align-items: center; justify-content: center;
            font-size: 0.75rem; font-weight: 600; flex-shrink: 0;
          ">AI</div>
                {/if}
                <div style="
          max-width: 75%; padding: 0.75rem 1rem;
          border-radius: {mensaje.tipo === 'usuario' ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem'};
          background: {mensaje.tipo === 'usuario' ? 'var(--primary)' : 'var(--secondary)'};
          color: {mensaje.tipo === 'usuario' ? 'var(--primary-foreground)' : 'var(--foreground)'};
          font-size: 0.875rem; line-height: 1.5;
          opacity: {mensaje.cargando ? '0.6' : '1'};
        ">
                    {mensaje.texto}
                </div>
            </div>
        {/each}
    </div>

    <div style="
    padding: 1rem; border-top: 1px solid var(--border);
    background: var(--card); display: flex; gap: 0.5rem; align-items: flex-end;
  ">
    <textarea
            bind:value={inputText}
            onkeydown={handleKeydown}
            placeholder="Escribí un pago o mandá un audio..."
            rows={1}
            style="
        flex: 1; resize: none; border-radius: 0.75rem;
        padding: 0.75rem 1rem; font-size: 0.875rem;
        border: 1px solid var(--border); background: var(--secondary);
        color: var(--foreground); outline: none; font-family: inherit;
      "
    ></textarea>

        <button
                onclick={toggleGrabacion}
                style="
        width: 2.75rem; height: 2.75rem; border-radius: 50%;
        border: none; cursor: pointer; font-size: 1.1rem; flex-shrink: 0;
        background: {isRecording ? '#ef4444' : 'var(--secondary)'};
      "
        >{isRecording ? '⏹' : '🎙️'}</button>

        <button
                onclick={enviarMensaje}
                disabled={!inputText.trim()}
                style="
        width: 2.75rem; height: 2.75rem; border-radius: 50%;
        border: none; cursor: pointer; font-size: 1.1rem;
        background: var(--primary); color: var(--primary-foreground); flex-shrink: 0;
        opacity: {inputText.trim() ? '1' : '0.4'};
      "
        >↑</button>
    </div>
</div>
