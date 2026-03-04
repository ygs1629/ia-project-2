// api.js — Módulo de comunicación con el backend

const BASE_URL = (() => {
  if (window.SFE_API_URL) return window.SFE_API_URL.replace(/\/$/, "");
  const { hostname, port } = window.location;
  const isLocal = hostname === "localhost" || hostname === "127.0.0.1";
  return isLocal ? `http://${hostname}:8000` : "";
})();

const PERIODOS_VALIDOS = ["semana", "mes", "trimestre", "semestre", "anual"];

// fetchDashboardData — GET /api/dashboard?periodo=X

async function fetchDashboardData(periodo = "mes") {
  if (!PERIODOS_VALIDOS.includes(periodo)) {
    throw new Error(`Período inválido: "${periodo}". Usar: ${PERIODOS_VALIDOS.join(" | ")}`);
  }
  const url = `${BASE_URL}/api/dashboard?periodo=${encodeURIComponent(periodo)}`;

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// fetchObjetivo — GET /api/objetivo

async function fetchObjetivo() {
  const url = `${BASE_URL}/api/objetivo`;

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// fetchResumen — GET /api/resumen?periodo=X

async function fetchResumen(periodo) {
  if (!PERIODOS_VALIDOS.includes(periodo)) {
    throw new Error(`Período inválido: "${periodo}". Usar: ${PERIODOS_VALIDOS.join(" | ")}`);
  }

  const url = `${BASE_URL}/api/resumen?periodo=${encodeURIComponent(periodo)}`;

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// fetchTopGastos — GET /api/top-gastos?periodo=X&n=5

async function fetchTopGastos(periodo, n = 5) {
  if (!PERIODOS_VALIDOS.includes(periodo)) {
    throw new Error(`Período inválido: "${periodo}". Usar: ${PERIODOS_VALIDOS.join(" | ")}`);
  }

  const url = `${BASE_URL}/api/top-gastos?periodo=${encodeURIComponent(periodo)}&n=${n}`;

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// fetchPrediccion — GET /api/predicciones

async function fetchPrediccion() {
  const url = `${BASE_URL}/api/predicciones`;

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// enviarMensajeChat — POST /api/chat

async function enviarMensajeChat(mensaje) {
  const url    = `${BASE_URL}/api/chat`;
  const apiKey = localStorage.getItem("google_api_key");

  const respuesta = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
    },
    body: JSON.stringify({
      mensaje,
      user_id: _getUserId(),
    }),
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// genera o recupera un user_id persistente en localStorage

function _getUserId() {
  let uid = localStorage.getItem("sfe_user_id");
  if (!uid) {
    uid = "sfe_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
    localStorage.setItem("sfe_user_id", uid);
  }
  return uid;
}

// crearObjetivo — POST /api/objetivos

async function crearObjetivo(nombre, importeObjetivo, importeActual, fechaLimite) {
  const url    = `${BASE_URL}/api/objetivos`;
  const apiKey = localStorage.getItem("google_api_key");

  const respuesta = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
    },
    body: JSON.stringify({
      nombre,
      importe_objetivo: importeObjetivo,
      importe_actual:   importeActual,
      fecha_limite:     fechaLimite,
    }),
  });

  if (!respuesta.ok) {
    const err = await respuesta.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${respuesta.status}: ${respuesta.statusText}`);
  }
  return await respuesta.json();
}