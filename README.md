# 💰 Asistente Financiero Virtual con IA

---

## 🏗️ Arquitectura

| Capa | Tecnología | Despliegue |
|------|-----------|------------|
| Frontend | HTML / CSS / JS vanilla | GitHub Pages |
| Backend + Agente | FastAPI + LangGraph | Hugging Face Spaces |
| Base de datos | SQLite | Incluida en el repo del backend |
| LLM | OpenAI (API Key del usuario) | — |

---

## ✨ Funcionalidades

- **Categorización automática** — El LLM clasifica los conceptos bancarios en categorías cerradas (Vivienda, Supermercado, Restaurantes, Ocio, Transporte, Suministros, Salud, Suscripciones, Ingresos, Otros)
- **Chat conversacional** — Agente LangGraph con acceso a la base de datos para responder preguntas como "¿cuánto he gastado en ocio este mes?"
- **Predicciones** — Cálculo matemático del gasto previsto el próximo mes
- **Objetivos financieros** — El usuario define objetivos con importe y fecha límite
- **Sistema de alertas** — Cruza predicciones con objetivos y usa el LLM para redactar alertas personalizadas

---

## 📁 Estructura del proyecto

```
/backend                          → Hugging Face Spaces
  app.py                          # Punto de entrada FastAPI
  requirements.txt
  /data
    transacciones_sucias.csv      # Histórico generado (script de uso único)
    finanzas.db                   # SQLite con datos categorizados + objetivos
  /scripts
    generar_datos.py              # Genera el CSV de datos ficticios
    categorizar.py                # Llama al LLM y puebla la DB (uso único)
  /core
    state.py                      # TypedDict del estado de LangGraph
    tools.py                      # Herramientas SQL del agente
    graph.py                      # Grafo LangGraph (nodos + edges)
  /api
    routes.py                     # Endpoints: /dashboard, /chat, /objetivos

/frontend                         → GitHub Pages
  index.html
  style.css
  app.js                          # Lógica de UI (vistas, eventos)
  api.js                          # Llamadas fetch al backend
  /assets/icons
```

---

## 🚀 Plan de desarrollo 

### Semana 1 — Backend funcional

| Día | Fase | Descripción |
|-----|------|-------------|
| 1-2 | Datos sucios | `generar_datos.py` — CSV con 18 meses de transacciones ficticias |
| 3 | Categorización | `categorizar.py` — LLM clasifica el CSV y puebla `finanzas.db` |
| 4 | LangGraph | `tools.py` + `graph.py` — Agente con acceso SQL, testeable desde terminal |
| 5 | Predicciones | Función Python de medias móviles + generación de alertas con LLM |

### Semana 2 — Frontend y despliegue

| Día | Fase | Descripción |
|-----|------|-------------|
| 6-7 | FastAPI | `routes.py` — Endpoints `/dashboard`, `/chat`, `/objetivos` con CORS |
| 8-9 | Frontend | Dashboard (Chart.js), chat con burbujas, modal de API Key |
| 10 | Objetivos | Formulario de alta de objetivos + tarjetas de progreso |
| 11-12 | Despliegue | Dockerfile para HF Spaces + GitHub Pages |
| 13-14 | Buffer | Bugs, pulido y preparación de la demo |

---

## 🔑 Gestión de la API Key

El usuario introduce su propia API Key en el frontend. El flujo es:

1. Al entrar a la app, un modal solicita la API Key si no existe en `localStorage`
2. Cada petición al backend incluye la key en el header: `Authorization: Bearer <key>`
3. El backend instancia el LLM con esa key y la descarta — **nunca se almacena en el servidor**

---

## 🔌 Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/dashboard` | Resumen del mes actual: gastos por categoría + alerta |
| `POST` | `/api/chat` | Mensaje al agente LangGraph (API Key en header) |
| `POST` | `/api/objetivos` | Crear o actualizar un objetivo financiero |

---

## ⚙️ Instalación local (backend)

```bash
git clone <repo-backend>
cd backend
pip install -r requirements.txt

# Paso 1: Generar datos ficticios
python scripts/generar_datos.py

# Paso 2: Categorizar con el LLM (requiere OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
python scripts/categorizar.py

# Paso 3: Lanzar la API
uvicorn app:app --reload
```

---

## ⚠️ Notas importantes

- El almacenamiento en Hugging Face Spaces (versión gratuita) es **efímero**. La `finanzas.db` y el CSV deben estar commiteados en el repositorio para que se restauren al despertar el Space.
- Para desarrollo local del frontend, cambiar la `BASE_URL` en `api.js` a `http://localhost:8000`.
