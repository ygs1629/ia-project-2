// api.js — Módulo de comunicación con el backend 
//
// Funciones disponibles:
//    fetchDashboardData()            → GET  /api/dashboard
//    fetchResumen(periodo)           → GET  /api/resumen?periodo=X
//    fetchTopGastos(periodo, n)      → GET  /api/top-gastos?periodo=X&n=5
//    fetchObjetivo()                 → GET  /api/objetivo
//    enviarMensajeChat(msg, hist)    → POST /api/chat
//
// La API Key se lee de localStorage("google_api_key") en cada llamada
// y se envía en el header Authorization: Bearer <key>.

const PERIODOS_VALIDOS = ["semana", "mes", "trimestre", "semestre", "anual"];

// fetchDashboardData — GET /api/dashboard

async function fetchDashboardData() {
  const url    = `${BASE_URL}/api/dashboard`;
  const apiKey = localStorage.getItem("google_api_key");

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
    },
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// fetchObjetivo — GET /api/objetivo

async function fetchObjetivo() {
  const url    = `${BASE_URL}/api/objetivo`;
  const apiKey = localStorage.getItem("google_api_key");

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
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

  const url    = `${BASE_URL}/api/resumen?periodo=${encodeURIComponent(periodo)}`;
  const apiKey = localStorage.getItem("google_api_key");

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
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

  const url    = `${BASE_URL}/api/top-gastos?periodo=${encodeURIComponent(periodo)}&n=${n}`;
  const apiKey = localStorage.getItem("google_api_key");

  const respuesta = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
    },
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// enviarMensajeChat — POST /api/chat

async function enviarMensajeChat(mensaje, historial = []) {
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
      user_id:   _getUserId(),
      historial: historial.slice(-10), // últimos 10 turnos para no saturar el contexto
    }),
  });

  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${respuesta.statusText} — ${url}`);
  }
  return await respuesta.json();
}

// Genera o recupera un user_id persistente en localStorage
function _getUserId() {
  let uid = localStorage.getItem("sfe_user_id");
  if (!uid) {
    uid = "sfe_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
    localStorage.setItem("sfe_user_id", uid);
  }
  return uid;
}