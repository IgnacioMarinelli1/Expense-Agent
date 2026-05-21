<script lang="ts">
    import { mensajes, cargando } from '$lib/stores/gastos'
    import { api } from '$lib/api/client'

    let inputText = $state('')
    let isRecording = $state(false)
    let mediaRecorder: MediaRecorder | null = null
    let chunks: Blob[] = []

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
                const blob = new Blob(chunks, { type: 'audio/webm' })
                mensajes.update(m => [...m, { id: Date.now(), tipo: 'usuario', texto: '🎙️ Audio enviado' }])
                const idCargando = Date.now() + 1
                mensajes.update(m => [...m, { id: idCargando, tipo: 'agente', texto: '...', cargando: true }])
                try {
                    const res = await api.enviarAudio(blob)
                    mensajes.update(m =>
                        m.map(msg => msg.id === idCargando
                            ? { ...msg, texto: res.respuesta, cargando: false }
                            : msg
                        )
                    )
                } catch {
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