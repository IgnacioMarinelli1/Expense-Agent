<script lang="ts">
    import { messages } from "$lib/stores/expenses";
    import { api } from "$lib/api/client";
    import { Bot, Mic, Square, ArrowUp, Camera } from "@lucide/svelte";
    import { marked } from "marked";

    const tokenStartTimes = new Map<string, number>();
    const messageLastStartTime = new Map<string, number>();

    function parseAndAnimate(message: any) {
        if (!message.text) return "";
        let html = marked.parse(message.text) as string;

        const now = Date.now();

        if (!message.loading) {
            // Si el mensaje cargó pero no tenemos un registro de su inicio,
            // es un mensaje viejo del historial, lo renderizamos de una.
            if (!messageLastStartTime.has(message.id)) {
                return html;
            }
            // Si ya pasó suficiente tiempo desde que la última palabra empezó a animarse,
            // podemos devolver el HTML crudo sin los spans de animación.
            const finalTime = messageLastStartTime.get(message.id)!;
            if (now - finalTime > 800) {
                return html;
            }
            // Si el backend terminó de mandar el texto (loading=false) pero VISUALMENTE
            // la animación todavía no terminó de correr, seguimos con la lógica de tokens.
        }

        let currentOffset = 0;

        let lastStartTime = messageLastStartTime.get(message.id) || now;
        // Si llegaron chunks tarde, empezamos a animar desde AHORA, no desde el pasado.
        if (lastStartTime < now) {
            lastStartTime = now;
        }

        const parts = html.split(/(<[^>]+>)/g);
        for (let i = 0; i < parts.length; i++) {
            if (parts[i].startsWith("<")) {
                currentOffset += parts[i].length;
                continue;
            }

            const tokens = parts[i].match(/\s+|\S+/g) ?? [];
            parts[i] = tokens
                .map((part) => {
                    const isWhitespace = /^\s+$/.test(part);
                    if (isWhitespace) {
                        currentOffset += part.length;
                        return part;
                    }

                    const key = `${message.id}:${currentOffset}`;
                    currentOffset += part.length;

                    if (!tokenStartTimes.has(key)) {
                        tokenStartTimes.set(key, lastStartTime);
                        lastStartTime += 15; // 30ms de separación por cada palabra
                    }

                    const startTime = tokenStartTimes.get(key)!;
                    const timeUntilStart = startTime - now;

                    // Si la animación (800ms) ya terminó, devolvemos el texto plano
                    if (timeUntilStart <= -800) {
                        return part;
                    }

                    // Si timeUntilStart es negativo, funciona como un delay negativo en CSS,
                    // lo que adelanta la animación exactamente al punto donde debería estar,
                    // evitando el parpadeo cuando Svelte re-renderiza el HTML.
                    return `<span class="stream-token-enter" style="animation-delay: ${timeUntilStart}ms">${part}</span>`;
                })
                .join("");
        }

        messageLastStartTime.set(message.id, lastStartTime);
        return parts.join("");
    }

    let inputText = $state("");
    let isRecording = $state(false);
    let isStreaming = $state(false);
    let mediaRecorder: MediaRecorder | null = null;
    let chunks: Blob[] = [];
    let fileInput: HTMLInputElement | undefined = $state();

    function encodeWav(audioBuffer: AudioBuffer) {
        const channels = audioBuffer.numberOfChannels;
        const sampleRate = audioBuffer.sampleRate;
        const samples = audioBuffer.length;
        const bytesPerSample = 2;
        const blockAlign = channels * bytesPerSample;
        const buffer = new ArrayBuffer(44 + samples * blockAlign);
        const view = new DataView(buffer);

        writeString(view, 0, "RIFF");
        view.setUint32(4, 36 + samples * blockAlign, true);
        writeString(view, 8, "WAVE");
        writeString(view, 12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, channels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * blockAlign, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, 16, true);
        writeString(view, 36, "data");
        view.setUint32(40, samples * blockAlign, true);

        let offset = 44;
        const channelData = Array.from({ length: channels }, (_, i) =>
            audioBuffer.getChannelData(i),
        );
        for (let i = 0; i < samples; i += 1) {
            for (let channel = 0; channel < channels; channel += 1) {
                const sample = Math.max(
                    -1,
                    Math.min(1, channelData[channel][i]),
                );
                view.setInt16(
                    offset,
                    sample < 0 ? sample * 0x8000 : sample * 0x7fff,
                    true,
                );
                offset += bytesPerSample;
            }
        }

        return new Blob([view], { type: "audio/wav" });
    }

    function writeString(view: DataView, offset: number, value: string) {
        for (let i = 0; i < value.length; i += 1) {
            view.setUint8(offset + i, value.charCodeAt(i));
        }
    }

    async function convertToWav(blob: Blob) {
        const AudioContextClass =
            window.AudioContext ||
            (
                window as typeof window & {
                    webkitAudioContext?: typeof AudioContext;
                }
            ).webkitAudioContext;
        if (!AudioContextClass) {
            throw new Error(
                "AudioContext no está disponible en este navegador.",
            );
        }
        const audioContext = new AudioContextClass();
        try {
            const audioBuffer = await audioContext.decodeAudioData(
                await blob.arrayBuffer(),
            );
            return encodeWav(audioBuffer);
        } finally {
            await audioContext.close();
        }
    }

    function addAgentStreamMessage() {
        const id = Date.now() + 1;
        messages.update((m) => [
            ...m,
            { id, type: "agente", text: "", loading: true },
        ]);
        return id;
    }

    function updateAgentMessage(id: number, text: string, loading = false) {
        messages.update((m) =>
            m.map((msg) => (msg.id === id ? { ...msg, text, loading } : msg)),
        );
    }

    async function streamIntoMessage(
        id: number,
        startStream: (handlers: {
            onToken: (token: string) => void;
            onError: (message: string) => void;
        }) => Promise<void>,
        fallback: string,
    ) {
        isStreaming = true;
        let responseText = "";
        try {
            await startStream({
                onToken: (token) => {
                    responseText += token;
                    updateAgentMessage(id, responseText, true);
                },
                onError: (message) => {
                    responseText = responseText
                        ? `${responseText}\n\n${message}`
                        : message;
                    updateAgentMessage(id, responseText, false);
                },
            });
            messages.update((m) =>
                m.map((msg) =>
                    msg.id === id
                        ? {
                              ...msg,
                              text: msg.text || "No pude procesar tu mensaje.",
                              loading: false,
                          }
                        : msg,
                ),
            );
        } catch (e) {
            console.error(e);
            updateAgentMessage(id, fallback, false);
        } finally {
            isStreaming = false;
        }
    }

    async function sendMessage() {
        if (!inputText.trim() || isStreaming) return;

        const text = inputText;
        inputText = "";

        // Agregar mensaje del usuario
        messages.update((m) => [
            ...m,
            { id: Date.now(), type: "usuario", text },
        ]);

        const loadingId = addAgentStreamMessage();
        await streamIntoMessage(
            loadingId,
            (handlers) => api.streamMessage(text, handlers),
            "Hubo un error al conectar con el agente. ¿El backend está corriendo?",
        );
    }

    async function toggleRecording() {
        if (isRecording) {
            mediaRecorder?.stop();
            isRecording = false;
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true,
            });
            mediaRecorder = new MediaRecorder(stream);
            chunks = [];

            mediaRecorder.ondataavailable = (e) => chunks.push(e.data);

            mediaRecorder.onstop = async () => {
                messages.update((m) => [
                    ...m,
                    {
                        id: Date.now(),
                        type: "usuario",
                        text: "🎙️ Audio enviado",
                    },
                ]);
                const loadingId = addAgentStreamMessage();
                try {
                    const grabacion = new Blob(chunks, {
                        type: mediaRecorder?.mimeType || "audio/webm",
                    });
                    const wav = await convertToWav(grabacion);
                    await streamIntoMessage(
                        loadingId,
                        (handlers) => api.streamAudio(wav, handlers),
                        "No pude procesar el audio.",
                    );
                } catch (e) {
                    console.error(e);
                    updateAgentMessage(
                        loadingId,
                        "No pude procesar el audio.",
                        false,
                    );
                }
                stream.getTracks().forEach((t) => t.stop());
            };

            mediaRecorder.start();
            isRecording = true;
        } catch {
            alert("No se pudo acceder al micrófono.");
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }

    async function handleImageUpload(e: Event) {
        const input = e.target as HTMLInputElement;
        if (!input.files?.length || isStreaming) return;

        const file = input.files[0];
        input.value = ""; // reset

        const fileUrl = URL.createObjectURL(file);
        const fileType = file.type === "application/pdf" ? "pdf" : "image";

        messages.update((m) => [
            ...m,
            { id: Date.now(), type: "usuario", text: "", fileUrl, fileType },
        ]);
        const loadingId = addAgentStreamMessage();
        await streamIntoMessage(
            loadingId,
            (handlers) => api.streamImage(file, handlers),
            "No pude procesar la imagen.",
        );
    }
</script>

<div class="mx-auto flex h-full w-full flex-col">
    <div class="flex flex-1 flex-col overflow-y-auto px-6 pt-6 pb-28">
        {#each $messages as message (message.id)}
            {#if message.type === "usuario"}
                <article class="message user-message flex justify-end mb-7">
                    <div
                        class="query-pill max-w-[85%] px-5 py-4 border border-border bg-muted/30 text-foreground text-[15px] font-semibold rounded-[18px_18px_4px_18px]"
                    >
                        {#if message.fileUrl}
                            <div class="flex flex-col gap-3 mb-2">
                                {#if message.fileType === "pdf"}
                                    <div
                                        class="flex items-center gap-2 pb-1 border-b border-border"
                                    >
                                        <span class="text-xl">📄</span>
                                        <span class="font-medium"
                                            >Documento PDF</span
                                        >
                                    </div>
                                    <embed
                                        src={message.fileUrl}
                                        type="application/pdf"
                                        class="h-[300px] w-[250px] rounded-md bg-white object-cover"
                                    />
                                {:else}
                                    <img
                                        src={message.fileUrl}
                                        alt="Preview"
                                        class="max-h-[300px] max-w-[250px] rounded-md object-contain"
                                    />
                                {/if}
                            </div>
                        {/if}
                        {message.text}
                    </div>
                </article>
            {:else}
                <article class="message assistant-message mb-7">
                    <div
                        class="agent-label flex items-center gap-2.5 mb-3 text-muted-foreground font-mono text-[13px]"
                    >
                        <div
                            class="agent-avatar size-[30px] rounded-[7px] bg-primary text-primary-foreground flex items-center justify-center font-bold text-sm"
                        >
                            A
                        </div>
                        <strong>Agente</strong>
                    </div>

                    <div
                        class="assistant-copy relative text-[15px] leading-relaxed text-foreground/90"
                    >
                        {#if message.loading && !message.text}
                            <span
                                class="flex items-center gap-1 py-1"
                                aria-label="Escribiendo"
                            >
                                <span
                                    class="size-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.3s]"
                                ></span>
                                <span
                                    class="size-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.15s]"
                                ></span>
                                <span
                                    class="size-1.5 animate-bounce rounded-full bg-current opacity-60"
                                ></span>
                            </span>
                        {:else}
                            <div class="markdown-body">
                                {@html parseAndAnimate(message)}
                            </div>
                        {/if}
                    </div>
                </article>
            {/if}
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
            onclick={toggleRecording}
            disabled={isStreaming && !isRecording}
            aria-label={isRecording ? "Detener grabación" : "Grabar audio"}
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
            onclick={sendMessage}
            disabled={!inputText.trim() || isStreaming}
            aria-label="Enviar mensaje"
            class="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-40 disabled:active:scale-100"
        >
            <ArrowUp class="size-5" />
        </button>
    </div>
</div>

<style>
    :global(.markdown-body p) {
        margin-bottom: 0.5rem;
    }
    :global(.markdown-body p:last-child) {
        margin-bottom: 0;
    }
    :global(.markdown-body ul) {
        list-style-type: disc;
        padding-left: 1.25rem;
        margin-bottom: 0.5rem;
    }
    :global(.markdown-body ol) {
        list-style-type: decimal;
        padding-left: 1.25rem;
        margin-bottom: 0.5rem;
    }
    :global(.markdown-body li) {
        margin-top: 0.25rem;
    }
    :global(.markdown-body strong) {
        font-weight: 600;
    }
    :global(.markdown-body a) {
        text-decoration: underline;
    }

    /* Tablas */
    :global(.markdown-body table) {
        width: 100%;
        border-collapse: collapse;
        margin: 0.75rem 0;
        font-size: 0.875rem;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
    }
    :global(.markdown-body thead) {
        background: color-mix(in srgb, currentColor 8%, transparent);
    }
    :global(.markdown-body th) {
        padding: 0.6rem 1rem;
        text-align: left;
        font-weight: 600;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: color-mix(in srgb, currentColor 60%, transparent);
        border-bottom: 1px solid color-mix(in srgb, currentColor 12%, transparent);
    }
    :global(.markdown-body td) {
        padding: 0.55rem 1rem;
        border-bottom: 1px solid color-mix(in srgb, currentColor 7%, transparent);
        color: color-mix(in srgb, currentColor 90%, transparent);
    }
    :global(.markdown-body tbody tr:last-child td) {
        border-bottom: none;
    }
    :global(.markdown-body tbody tr:hover) {
        background: color-mix(in srgb, currentColor 4%, transparent);
    }

    /* Animación del stream por palabra (token-enter) */
    :global(.markdown-body .stream-token-enter) {
        display: inline-block;
        opacity: 0;
        transform: translateY(0.3em);
        /* Hacemos que dure 800ms en lugar de 340ms */
        animation: token-enter 400ms cubic-bezier(0.3, 0, 1, 1) forwards;
        animation-delay: var(--stream-token-delay, 0ms);
        will-change: opacity, transform;
    }

    @keyframes token-enter {
        0% {
            opacity: 0;
            transform: translateY(0.28em);
        }
        100% {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
