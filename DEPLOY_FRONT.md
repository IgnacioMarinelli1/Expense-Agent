# Deploy Frontend — Firebase App Hosting

## Estrategia

El frontend usa streaming SSE, lo que requiere un servidor Node — `adapter-static` no sirve.  
**Firebase App Hosting** (≠ Firebase Hosting clásico) corre sobre Cloud Run, soporta SSR y streaming, y es el producto correcto.

- Proyecto GCP: `al-dia-expense-agent`
- Backend URL: `https://expense-agent-thm7giy46q-rj.a.run.app`

---

## Free Tier de Firebase App Hosting

Firebase App Hosting corre sobre Cloud Run. El free tier de Cloud Run aplica:

| Recurso | Free tier/mes |
|---|---|
| Requests | 2 millones |
| CPU | 180,000 vCPU-segundos |
| Memoria | 360,000 GB-segundos |
| Egreso (red) | 1 GB |

> Requiere plan **Blaze** (pay-as-you-go), pero con uso de hackathon/personal el costo es $0.

---

## Cambios ya aplicados al código

### `frontend/svelte.config.js`

Cambiado de `adapter-auto` a `adapter-node`:

```js
import adapter from '@sveltejs/adapter-node';

const config = {
  compilerOptions: {
    runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
  },
  kit: {
    adapter: adapter({ out: 'build' })
  }
};

export default config;
```

### `frontend/apphosting.yaml`

Variables de build y runtime:

```yaml
runConfig:
  minInstances: 0
  maxInstances: 10

env:
  - variable: VITE_API_URL
    value: https://expense-agent-thm7giy46q-rj.a.run.app
    availability:
      - BUILD
      - RUNTIME
```

> `VITE_API_URL` necesita `availability: BUILD` porque Vite lo embebe en el bundle en tiempo de compilación.

---

## Pasos de deploy (ejecutar en terminal)

### 1. Instalar Firebase CLI

```bash
npm install -g firebase-tools
```

### 2. Login a Firebase

```bash
firebase login
```

> Se abre el browser para autenticar con la cuenta de Google del proyecto.

### 3. Habilitar Blaze plan

Si el proyecto no está en Blaze, ir a:
**Firebase Console → al-dia-expense-agent → Upgrade to Blaze**

### 4. Inicializar Firebase App Hosting

```bash
# Desde la RAÍZ del proyecto
firebase init apphosting
```

Cuando pregunte:
- **Project**: seleccionar `al-dia-expense-agent`
- **App root directory**: `./frontend`
- **Backend ID**: `expense-agent-frontend` (o cualquier nombre)
- **Region**: `southamerica-east1` (más cercana a Argentina)
- **Live branch**: `main` (o la que uses)

### 5. Deploy

```bash
firebase deploy --only apphosting
```

Firebase App Hosting va a:
1. Subir el código fuente
2. Correr `pnpm build` (o `npm run build`) en Cloud Build con `VITE_API_URL` inyectado
3. Deployar el servidor Node en Cloud Run
4. Darte la URL pública

---

## CORS en el backend

Una vez deployado el front y con la URL de App Hosting, agregar esa URL al backend Python:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://expense-agent-frontend--<backend-id>-<hash>.web.app",  # URL del front
    ],
    ...
)
```

La URL exacta la da Firebase al terminar el deploy.

---

## Re-deploy

Cada vez que quieras actualizar el front:

```bash
firebase deploy --only apphosting
```

O si conectás el repositorio GitHub en Firebase Console, el re-deploy es automático en cada push a `main`.

---

## Checklist pre-deploy

- [x] `adapter-node` instalado y configurado en `svelte.config.js`
- [x] `apphosting.yaml` creado con `VITE_API_URL`
- [x] `pnpm build` corre sin errores localmente
- [ ] Firebase CLI instalado (`npm install -g firebase-tools`)
- [ ] `firebase login` ejecutado
- [ ] Proyecto en plan Blaze
- [ ] `firebase init apphosting` ejecutado
- [ ] CORS en el backend incluye la URL del frontend
