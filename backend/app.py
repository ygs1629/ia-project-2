"""
app.py — Punto de entrada de la API del asistente financiero.
Despliegue:
    Local:              uvicorn app:app --reload --port 8000
    Hugging Face:       uvicorn app:app --host 0.0.0.0 --port 7860
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(
    title="Asistente Financiero Virtual",
    description=(
        "API del asistente financiero. "
        "La API Key del usuario se pasa en cada petición y nunca se almacena."
    ),
    version="1.0.0",
)

# CORS: permite cualquier origen (necesario para GitHub Pages y Hugging Face)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,        
    allow_methods=["GET", "POST"],
    allow_headers=["*"],            
)

app.include_router(router)

@app.get("/", tags=["health"])
def health_check():
    """Comprueba que la API está en marcha."""
    return {"status": "ok", "mensaje": "Asistente Financiero API activa."}
