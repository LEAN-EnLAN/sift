# Sift — buscador inteligente de repositorios

Prototipo CLI para el ejercicio técnico: recibe una necesidad en lenguaje natural y uno o más lenguajes de programación, consulta la GitHub Search API y devuelve los **top 5 repositorios recomendados** con explicación y comparación.

La idea central no es ordenar por stars, sino por una mezcla defendible de **relevancia + mantenimiento + actividad + comunidad + documentación**.

## Requisitos

- Python 3.10+
- Una GitHub OAuth App (opcional, solo si querés usar tu propio client_id).
  Si no configurás nada, el tool usa un client_id público. Para equipos recomendamos
  registrar tu propia app en 2 minutos (ver abajo).

## Instalación

### Via pipx (recomendado)

```bash
pipx install sift
```

### Desde el repo

```bash
git clone <url-del-repo>
cd sift
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Login rápido con OAuth (recomendado)

Nada de tokens manuales. El device flow de GitHub abre el navegador, autorizás
en un click y el token se guarda solo:

\`\`\`bash
sift --login
\`\`\`

Te va a mostrar:

\`\`\`
→ Solicitando código de dispositivo a GitHub...

   🔗  Abrí https://github.com/login/device
   🔢  Ingresá el código: XXXX-XXXX

   (el navegador debería haberse abierto solo)
   ⏳  Esperando que autorices en GitHub...

✅  ¡Login exitoso! El token quedó guardado en:
   /home/tu-user/.config/sift/config.json
\`\`\`

El token se guarda con permisos 600 en `~/.config/sift/config.json`.
Para cerrar sesión:

```bash
sift --logout
```

### Modo TUI (Textual)

Cuando ejecutás `sift` en una terminal (TTY) sin flags, arranca la interfaz TUI:

1. Escribís un solo pedido natural, por ejemplo: `necesito autenticación JWT en python rápido`
2. La TUI detecta automáticamente consulta, lenguaje y velocidad
3. Te muestra un preview editable antes de buscar
4. Ves progreso visible mientras consulta GitHub y enriquece resultados
5. Navegás resultados con el teclado y abrís el detalle

Si no detecta bien el lenguaje, lo corregís manualmente en el preview. Si detecta un lenguaje nuevo (`zig`, `elixir`, etc.), intenta inferirlo y te deja editarlo antes de buscar.

Atajos de teclado en TUI:

| Tecla | Acción |
|-------|--------|
| `q` / `Esc` | Salir / Volver |
| `Ctrl+D` | Ver detalle del resultado seleccionado |
| `r` | Refrescar búsqueda |

Para deshabilitar la TUI (útil en CI/scripts):

```bash
SIFT_HEADLESS=1 sift --query "jwt auth" --language Python
```

O con el flag `--no-interactive`:

```bash
sift --no-interactive --query "jwt auth" --language Python
```

### Alternativa: token manual

Si preferís crear un token a mano (GitHub → Settings → Developer settings →
Personal access tokens → Generate new token (classic), sin scopes especiales):

```bash
export GITHUB_TOKEN=ghp_xxx
```

### Registrar tu propia GitHub OAuth App (2 min, opcional)

Para equipos recomendamos tener tu propio client_id así no compartís rate limit:

1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2. Application name: `Repo Scout (equipo)`
3. Homepage URL: `http://127.0.0.1:8000`
4. Authorization callback URL: `http://127.0.0.1:8000/callback`
5. Copiá el **Client ID** y configuralo:
   ```bash
   export GITHUB_CLIENT_ID=Ov23li...
   ```

### Buscar

```bash
sift \
  --query "autenticación con JWT" \
  --language Python \
  --top 5
```

Salida JSON:

```bash
sift -q "procesar PDFs" -l Python --format json
```

Búsqueda multi-lenguaje:

```bash
sift -q "auth con JWT" -l Python,JavaScript
```

Filtros bonus:

```bash
sift \
  -q "boilerplate de FastAPI" \
  -l Python \
  --min-stars 100 \
  --pushed-after 2024-01-01 \
  --license mit
```


## Modos de ejecución

### Modo TUI (TTY default)

Cuando ejecutás `sift` sin `--query` y sin `--language`, entra en modo TUI (Textual):
interfaz conversacional con inputs, búsqueda asincrónica y vista de detalle.

Para volver al modo interactivo original (Rich):

```bash
sift --force-interactive
```

### Modo agente (--agent / --ai)

Para integración con scripts, CI y agentes de IA. Salida JSON con `_meta`:

```bash
sift --agent --query "autenticación con JWT" --language Python
```

Ver `AGENTS.md` para la referencia completa del contrato de salida.

### Speed tiers (--speed)

Controla la velocidad y profundidad de la búsqueda:

```bash
sift --speed fast --query "procesar PDFs" -l Python
```

| Tier | Uso típico | Queries | Candidatos |
|------|------------|---------|------------|
| `fast` | Pruebas rápidas, primer tanteo | 4 | 8 |
| `balanced` (default) | Uso general | 7 | 35 |
| `thorough` | Búsqueda exhaustiva | 8 | 50 |

## Cómo construyo el query para GitHub

GitHub Search usa términos libres como `AND`. Si mando demasiados sinónimos juntos, pierdo recall. Por eso genero varias queries pequeñas y después hago re-ranking local.

Para `"autenticación con JWT"` + `Python`, por ejemplo:

```text
jwt authentication language:Python fork:false archived:false
jwt authentication in:name,description,readme language:Python fork:false archived:false
jwt language:Python fork:false archived:false
authentication language:Python fork:false archived:false
topic:jwt language:Python fork:false archived:false
```

Además:

- Elimino stopwords en español (`con`, `de`, `para`, etc.).
- Expando términos frecuentes español → inglés: `autenticación → authentication/auth/login`, `procesar → processing/parse/extract`, `plantilla → template/starter/boilerplate`.
- Priorizo términos técnicos literales del usuario (`JWT`, `PDF`, `FastAPI`) para que no queden tapados por sinónimos genéricos.
- Excluyo por defecto forks y archivados: `fork:false archived:false`.

## Señales de calidad y scoring

Cada candidato se enriquece con:

- Último commit real del default branch: `GET /repos/{owner}/{repo}/commits?per_page=1`.
- README: `GET /repos/{owner}/{repo}/readme`.
- Metadata de Search API: stars, forks, issues, licencia, topics, `pushed_at`, archivado/fork.

Fórmula base:

```text
score_base =
  35% relevancia
+ 25% actividad
+ 20% comunidad
+ 10% documentación
+ 10% mantenimiento
```

Luego aplico un **relevance gate**:

```text
score_final = score_base * (0.65 + 0.35 * relevancia)
```

Esto evita que un repo enorme gane sólo por popularidad si no resuelve exactamente la necesidad.

### 1. Relevancia — 35%

Mide coincidencias de keywords en:

- nombre del repo,
- descripción,
- topics,
- README,
- aparición en rankings de GitHub Search para varias queries.

El nombre/descripción pesan más que el README porque indican intención del proyecto, no sólo una mención casual.

### 2. Actividad — 25%

Usa fecha de último commit:

- ≤ 30 días: 1.0
- ≤ 90 días: 0.85
- ≤ 180 días: 0.70
- ≤ 365 días: 0.50
- ≤ 2 años: 0.25
- > 2 años: 0.05

Un repo de 50k stars sin commits hace 3 años queda penalizado.

### 3. Comunidad — 20%

Usa stars y forks con escala logarítmica:

```text
community = 78% log(stars) + 22% log(forks)
```

La escala log evita que 50k stars aplasten automáticamente a un repo de 200 stars muy activo y específico.

### 4. Documentación — 10%

Evalúa README:

- longitud suficiente,
- secciones como install, usage, quickstart, examples, docs,
- bloques de código o comandos de instalación.

### 5. Mantenimiento — 10%

Combina:

- no archivado,
- recencia,
- licencia clara,
- presión de issues (`open_issues / stars`),
- penalización si es fork.

## Rate limit y caching

- Usa `GITHUB_TOKEN` si está disponible.
- Cache local en `.cache/sift` con TTL configurable (`--cache-ttl`, default 1 hora).
- Reduce requests repetidas durante demos y ajustes de scoring.
- Sin token baja automáticamente el máximo de candidatos enriquecidos para no quemar el límite core de 60 req/h.
- Hace throttling simple:
  - Search API sin token: pausas más largas porque GitHub permite pocas búsquedas por minuto.
  - Con token: pausas menores.
- Ante secondary rate limit, espera y reintenta una vez.

Para escalarlo a 100+ devs usaría:

1. Backend compartido con token de GitHub App, no tokens personales.
2. Cache distribuido por query normalizada y por repo (`Redis`/`DynamoDB`) con TTLs separados.
3. Cola de enriquecimiento async para commits/README.
4. Índice propio incremental de repos ya evaluados.
5. Feedback explícito de devs (`útil/no útil`) para ajustar pesos o entrenar un ranker.
6. Observabilidad de rate limit, latencia, cache hit ratio y queries sin buenos resultados.

## Ejemplos de output

> Salidas abreviadas de corridas reales del CLI. Los valores pueden cambiar porque GitHub es dinámico.

### Ejemplo 1 — `autenticación con JWT` / `Python`

Comando:

```bash
sift -q "autenticación con JWT" -l Python --top 5
```

| # | Repo | Último commit | Stars | Score | Por qué |
|---:|---|---|---:|---:|---|
| 1 | [iMerica/dj-rest-auth](https://github.com/iMerica/dj-rest-auth) | 2026-04-25 | 1855 | 70.98 | Auth para Django REST, activo, MIT, buen README. |
| 2 | [jazzband/djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt) | 2026-05-11 | 4317 | 62.87 | Plugin JWT específico para DRF, comunidad fuerte, muy activo. |
| 3 | [jpadilla/pyjwt](https://github.com/jpadilla/pyjwt) | 2026-03-31 | 5656 | 58.31 | Implementación Python de JWT, madura y mantenida. |
| 4 | [ticarpi/jwt_tool](https://github.com/ticarpi/jwt_tool) | 2025-05-01 | 6529 | 43.93 | Toolkit JWT con docs fuertes; más orientado a testing/seguridad. |
| 5 | [flavors/django-graphql-jwt](https://github.com/flavors/django-graphql-jwt) | 2023-08-04 | 825 | 41.46 | Relevante para GraphQL + Django, pero menos activo. |

### Ejemplo 2 — `boilerplate de FastAPI` / `Python`

Comando:

```bash
sift -q "boilerplate de FastAPI" -l Python --top 5
```

| # | Repo | Último commit | Stars | Score | Por qué |
|---:|---|---|---:|---:|---|
| 1 | [benavlabs/FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate) | 2026-02-05 | 1903 | 66.45 | Boilerplate específico, stack moderno, MIT, docs sólidas. |
| 2 | [fastapi/fastapi](https://github.com/fastapi/fastapi) | 2026-05-11 | 98098 | 60.07 | Framework base muy mantenido; útil como referencia, no boilerplate puro. |
| 3 | [ChristianLempa/boilerplates](https://github.com/ChristianLempa/boilerplates) | 2026-05-04 | 7724 | 57.45 | Colección activa de templates, buena comunidad. |
| 4 | [teamhide/fastapi-boilerplate](https://github.com/teamhide/fastapi-boilerplate) | 2025-06-13 | 1487 | 52.37 | Boilerplate productivo y relevante, aunque con menor score de docs/licencia. |
| 5 | [ycd/manage-fastapi](https://github.com/ycd/manage-fastapi) | 2023-08-01 | 1902 | 33.68 | Generador de proyectos FastAPI; penalizado por actividad baja. |

### Ejemplo 3 — `procesar PDFs` / `Python`

Comando:

```bash
sift -q "procesar PDFs" -l Python --top 5
```

| # | Repo | Último commit | Stars | Score | Por qué |
|---:|---|---|---:|---:|---|
| 1 | [oomol-lab/pdf-craft](https://github.com/oomol-lab/pdf-craft) | 2026-04-30 | 5624 | 67.61 | Procesamiento/conversión de PDFs, activo, docs fuertes, MIT. |
| 2 | [PDFMathTranslate/PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate) | 2026-04-06 | 33671 | 64.35 | Muy activo y documentado; foco en PDFs científicos/traducción. |
| 3 | [WZBSocialScienceCenter/pdftabextract](https://github.com/WZBSocialScienceCenter/pdftabextract) | 2022-06-24 | 2257 | 50.08 | Excelente para extraer tablas; penalizado por baja actividad reciente. |
| 4 | [WZMIAOMIAO/deep-learning-for-image-processing](https://github.com/WZMIAOMIAO/deep-learning-for-image-processing) | 2026-01-01 | 26230 | 42.29 | Aparece por procesamiento, pero relevancia baja para PDFs; el gate lo penaliza. |
| 5 | [fighting41love/funNLP](https://github.com/fighting41love/funNLP) | 2023-08-24 | 80579 | 35.30 | Mención lateral a PDFs; popular pero no específico, por eso queda abajo. |

## Qué pasa si no hay resultados decentes

- La CLI devuelve menos de 5 si no hay suficientes candidatos enriquecidos.
- El output avisa que no encontró repos con señales suficientes.
- Recomendación práctica: relajar `--min-stars`, ampliar lenguajes o usar términos técnicos más concretos.

## Estructura

```text
src/sift/
  cli.py       # argparse, orquestación y salida
  github.py    # cliente GitHub API, cache, rate limit
  query.py     # normalización y generación de queries
  scoring.py   # fórmula de scoring y razones
  render.py    # Markdown / JSON / agent JSON
  models.py    # dataclasses
```
