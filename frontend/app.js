// app.js — Capa de presentación del dashboard

const BASE_URL = "http://localhost:8000";

// período seleccionado en el filtro y mes por defecto
let PERIODO_ACTIVO = "mes";

// referencia al gráfico para poder destruirlo antes de redibujar
let graficoDonut = null;

// historial del chat 
const MAX_HISTORIAL = 10;
let historialChat = [];

// un color por categoría
const COLORES_CATEGORIAS = [
  "#0891B2", // Vivienda
  "#0D9488", // Supermercado
  "#7C3AED", // Suministros
  "#D97706", // Ocio
  "#059669", // Restaurantes
  "#DC2626", // Transporte
  "#DB2777", // Salud
  "#EA580C", // Suscripciones
];

const COLORES_HOVER = COLORES_CATEGORIAS.map((c) => c + "CC");

function formatearEuro(valor) {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(valor);
}

// rellena las tres tarjetas de resumen 
function renderizarResumen(resumen) {
  const campos = {
    ingresos: document.getElementById("resumenIngresos"),
    gastos:   document.getElementById("resumenGastos"),
    ahorro:   document.getElementById("resumenAhorro"),
  };

  for (const [clave, el] of Object.entries(campos)) {
    if (!el) { console.warn(`SFE: falta #resumen${clave}`); continue; }
    el.textContent = formatearEuro(resumen[clave]);

    if (clave === "ahorro") {
      el.classList.toggle("valor-positivo", resumen[clave] >= 0);
      el.classList.toggle("valor-negativo", resumen[clave] < 0);
    }
  }
}

// dibuja el donut y la tabla de categorías y si ya había un gráfico lo destruye primero
function renderizarGrafico(gastosPorCategoria) {
  const canvas = document.getElementById("graficoGastos");
  if (!canvas) { console.error("SFE: falta <canvas id='graficoGastos'>"); return; }

  if (graficoDonut) { graficoDonut.destroy(); graficoDonut = null; }

  const etiquetas = Object.keys(gastosPorCategoria);
  const valores   = Object.values(gastosPorCategoria);
  const cfondo    = etiquetas.map((_, i) => COLORES_CATEGORIAS[i % COLORES_CATEGORIAS.length]);
  const chover    = etiquetas.map((_, i) => COLORES_HOVER[i % COLORES_HOVER.length]);

  const total = valores.reduce((a, b) => a + b, 0);

  const labelWrap = document.querySelector(".chart-center-label");
  if (labelWrap) labelWrap.style.display = "none";

  _renderizarTablaCategoriasConBarras(etiquetas, valores, cfondo);

  const pluginCentro = {
    id: "centroDonut",
    afterDraw(chart) {
      const { ctx, chartArea: { top, bottom, left, right } } = chart;
      const cx = (left + right) / 2;
      const cy = (top + bottom) / 2;
      ctx.save();
      ctx.font = "500 15px 'DM Mono', monospace";
      ctx.fillStyle = "#E8F0F8";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(formatearEuro(total), cx, cy - 8);
      ctx.font = "400 9px 'DM Mono', monospace";
      ctx.fillStyle = "#3D5470";
      ctx.fillText("TOTAL GASTOS", cx, cy + 10);
      ctx.restore();
    },
  };

  graficoDonut = new Chart(canvas.getContext("2d"), {
    type: "doughnut",
    plugins: [pluginCentro],
    data: {
      labels: etiquetas,
      datasets: [{
        data: valores,
        backgroundColor: cfondo,
        hoverBackgroundColor: chover,
        borderWidth: 2,
        borderColor: "#1E293B",
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: "65%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            padding: 16,
            font: { size: 12, family: "'DM Mono', monospace" },
            color: "#CBD5E1",
            usePointStyle: true,
            pointStyle: "circle"
          },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${formatearEuro(ctx.parsed)}`,
          },
          backgroundColor: "#0F172A",
          titleColor: "#F1F5F9",
          bodyColor: "#CBD5E1",
          borderColor: "#334155",
          borderWidth: 1,
          padding: 12,
        },
      },
      animation: { animateRotate: true, duration: 900, easing: "easeInOutQuart" },
    },
  });
}

// tabla con barras proporcionales al gasto máximo de la categoría
function _renderizarTablaCategoriasConBarras(etiquetas, valores, colores) {
  const tbody = document.getElementById("tablaCategorias");
  if (!tbody) return;

  const maximo = Math.max(...valores);
  tbody.innerHTML = "";

  etiquetas.forEach((nombre, i) => {
    const pct = maximo > 0 ? ((valores[i] / maximo) * 100).toFixed(0) : 0;
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td>
        <div class="cat-nombre">
          <span class="categoria-dot" style="background:${colores[i]}"></span>
          ${nombre}
        </div>
      </td>
      <td>
        <span class="barra-wrap">
          <span class="barra-fill" style="width:${pct}%;background:${colores[i]}"></span>
        </span>
        ${formatearEuro(valores[i])}
      </td>
    `;
    tbody.appendChild(fila);
  });
}

// rellena la card del objetivo con los datos de get_progreso_objetivo
function renderizarObjetivo(obj) {
  const cont = document.getElementById("objetivosContainer");
  if (cont && !document.getElementById("objetivoNombre")) {
    cont.innerHTML = `
      <div class="panel-header">
        <h2 class="panel-title">Objetivo de ahorro</h2>
        <div style="display:flex;align-items:center;gap:.5rem;">
          <span class="panel-badge" id="objetivoPorcentaje">—</span>
          <button class="btn-editar-objetivo" onclick="abrirModalObjetivo()" title="Editar objetivo" aria-label="Editar objetivo de ahorro">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            Editar
          </button>
        </div>
      </div>
      <div class="objetivo-body">
        <div class="objetivo-nombre" id="objetivoNombre"></div>
        <div class="objetivo-barra-wrap" aria-label="Progreso del objetivo">
          <div class="objetivo-barra-track">
            <div class="objetivo-barra-fill" id="objetivoBarra" style="width:0%"></div>
          </div>
        </div>
        <div class="objetivo-metricas">
          <div class="objetivo-metrica">
            <span class="objetivo-metrica-label">Ahorrado</span>
            <span class="objetivo-metrica-valor color-green" id="objetivoActual">—</span>
          </div>
          <div class="objetivo-metrica">
            <span class="objetivo-metrica-label">Objetivo</span>
            <span class="objetivo-metrica-valor" id="objetivoTotal">—</span>
          </div>
          <div class="objetivo-metrica">
            <span class="objetivo-metrica-label">Falta</span>
            <span class="objetivo-metrica-valor color-amber" id="objetivoFalta">—</span>
          </div>
          <div class="objetivo-metrica">
            <span class="objetivo-metrica-label">Plazo</span>
            <span class="objetivo-metrica-valor" id="objetivoDias">—</span>
          </div>
        </div>
        <div class="objetivo-fecha">
          📅 Fecha límite: <span id="objetivoFecha">—</span>
        </div>
      </div>
    `;
  }

  const elNombre = document.getElementById("objetivoNombre");
  if (elNombre) elNombre.textContent = obj.nombre;

  const elActual = document.getElementById("objetivoActual");
  if (elActual) {
    elActual.textContent = formatearEuro(obj.importe_actual);
    elActual.dataset.raw = obj.importe_actual;
  }

  const elTotal = document.getElementById("objetivoTotal");
  if (elTotal) {
    elTotal.textContent = formatearEuro(obj.importe_objetivo);
    elTotal.dataset.raw = obj.importe_objetivo;
  }

  const elBarra = document.getElementById("objetivoBarra");
  if (elBarra) {
    elBarra.style.width = `${Math.min(obj.porcentaje, 100)}%`;
    // verde si está cerca, ámbar si va a medias, azul si queda mucho
    elBarra.style.background =
      obj.porcentaje >= 80 ? "var(--green)" :
      obj.porcentaje >= 40 ? "var(--amber)" :
      "var(--accent)";
  }

  const elPct = document.getElementById("objetivoPorcentaje");
  if (elPct) elPct.textContent = `${obj.porcentaje} %`;

  const elDias = document.getElementById("objetivoDias");
  if (elDias) elDias.textContent = `${obj.dias_restantes} días`;

  const elFalta = document.getElementById("objetivoFalta");
  if (elFalta) elFalta.textContent = formatearEuro(obj.falta);

  const elFecha = document.getElementById("objetivoFecha");
  if (elFecha) {
    elFecha.dataset.raw = obj.fecha_limite;
    elFecha.textContent = new Date(obj.fecha_limite).toLocaleDateString("es-ES", {
      day: "numeric", month: "long", year: "numeric",
    });
  }

  const card = document.getElementById("objetivosContainer");
  if (card) card.style.opacity = "1";
}

// se llama al hacer clic en los botones del filtro
async function cambiarPeriodo(nuevoPeriodo) {
  if (!PERIODOS_VALIDOS.includes(nuevoPeriodo)) {
    console.error(`SFE: período inválido "${nuevoPeriodo}"`);
    return;
  }

  if (nuevoPeriodo === PERIODO_ACTIVO) return;

  PERIODO_ACTIVO = nuevoPeriodo;

  document.querySelectorAll(".filtro-btn").forEach((btn) => {
    btn.classList.toggle("filtro-btn--activo", btn.dataset.periodo === nuevoPeriodo);
  });

  // skeletons mientras llegan los datos nuevos
  ["resumenIngresos", "resumenGastos", "resumenAhorro"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = "<span class='skeleton'></span>";
  });
  const listaTop = document.getElementById("listaTopGastos");
  if (listaTop) listaTop.innerHTML = `<li class="top-gastos-cargando"><span class="spinner"></span> Cargando…</li>`;

  try {
    const [resumen, datosDashboard, topGastos] = await Promise.all([
      fetchResumen(nuevoPeriodo),
      fetchDashboardData(nuevoPeriodo),
      fetchTopGastos(nuevoPeriodo, 5),
    ]);

    renderizarResumen(resumen);
    renderizarGrafico(datosDashboard.gastos_por_categoria);
    renderizarTopGastos(topGastos);

    const elPeriodo = document.getElementById("badgePeriodo");
    const labels = { semana: "Semana", mes: "Mes", trimestre: "Trimestre", semestre: "Semestre", anual: "Anual" };
    if (elPeriodo) elPeriodo.textContent = labels[nuevoPeriodo] || nuevoPeriodo;

  } catch (error) {
    console.error("SFE: error al cambiar período →", error.message);
    mostrarErrorGlobal(error.message);
  }
}

// lista los N gastos más altos del período 
function renderizarTopGastos(lista) {
  const contenedor = document.getElementById("listaTopGastos");
  if (!contenedor) { console.warn("SFE: falta #listaTopGastos"); return; }

  if (!lista || lista.length === 0) {
    contenedor.innerHTML = `<li class="top-gastos-vacio">No hay gastos registrados para este período.</li>`;
    return;
  }

  contenedor.innerHTML = "";

  const COLORES_CAT = {
    Vivienda:      "#0891B2",
    Supermercado:  "#0D9488",
    Suministros:   "#7C3AED",
    Ocio:          "#D97706",
    Restaurantes:  "#059669",
    Transporte:    "#DC2626",
    Salud:         "#DB2777",
    Suscripciones: "#EA580C",
    Otros:         "#6B7280",
  };

  lista.forEach((gasto, idx) => {
    const color = COLORES_CAT[gasto.categoria] || "#6B7280";
    const fechaFormateada = new Date(gasto.fecha).toLocaleDateString("es-ES", {
      day: "numeric", month: "short",
    });

    const item = document.createElement("li");
    item.classList.add("top-gastos-item");
    item.style.animationDelay = `${idx * 60}ms`;
    item.innerHTML = `
      <span class="top-gastos-rank">${idx + 1}</span>
      <span class="top-gastos-dot" style="background:${color}"></span>
      <div class="top-gastos-info">
        <span class="top-gastos-concepto">${gasto.concepto}</span>
        <span class="top-gastos-meta">
          <span class="top-gastos-cat" style="color:${color}">${gasto.categoria}</span>
          <span class="top-gastos-fecha">${fechaFormateada}</span>
        </span>
      </div>
      <span class="top-gastos-importe">${formatearEuro(gasto.importe)}</span>
    `;
    contenedor.appendChild(item);
  });
}

function _agregarBurbuja(texto, tipo) {
  const area = document.getElementById("chatMensajes");
  if (!area) return null;

  const burbuja = document.createElement("div");
  burbuja.classList.add("chat-burbuja", `chat-burbuja--${tipo}`);

  if (tipo === "agente" && texto === "") {
    // tres puntitos animados mientras espera respuesta
    burbuja.classList.add("chat-escribiendo");
    burbuja.innerHTML = "<span></span><span></span><span></span>";
  } else {
    burbuja.textContent = texto;
  }

  area.appendChild(burbuja);
  area.scrollTop = area.scrollHeight;
  return burbuja;
}

// indicador visual de qué tool está ejecutando el agente en este momento
function _agregarIndicadorTool(toolNombre) {
  const area = document.getElementById("chatMensajes");
  if (!area) return null;

  const indicador = document.createElement("div");
  indicador.classList.add("chat-tool-indicator");

  const nombres = {
    "get_gastos_periodo":             "Consultando gastos por período…",
    "get_evolucion_categoria":        "Analizando evolución de categoría…",
    "get_resumen_ingresos_vs_gastos": "Calculando balance ingresos/gastos…",
    "get_progreso_objetivo":          "Consultando progreso del objetivo…",
    "get_top_gastos":                 "Buscando tus mayores gastos…",
  };

  indicador.innerHTML = `
    <span class="tool-icon">⚙</span>
    <span class="tool-texto">${nombres[toolNombre] || "Consultando base de datos…"}</span>
  `;

  area.appendChild(indicador);
  area.scrollTop = area.scrollHeight;
  return indicador;
}

async function enviarMensaje() {
  const input     = document.getElementById("chatInput");
  const btnEnviar = document.getElementById("chatBtnEnviar");
  if (!input) return;

  const texto = input.value.trim();
  if (!texto) return;

  input.value = "";
  input.disabled = true;
  if (btnEnviar) btnEnviar.disabled = true;

  _agregarBurbuja(texto, "usuario");

  historialChat.push({ rol: "usuario", texto });
  if (historialChat.length > MAX_HISTORIAL * 2) {
    historialChat = historialChat.slice(-MAX_HISTORIAL * 2);
  }

  const burbujaEspera = _agregarBurbuja("", "agente");

  // mostramos el indicador de tool antes de saber cuál usará 
  const indicadorDB = _agregarIndicadorTool("get_gastos_periodo");
  if (indicadorDB) indicadorDB.classList.add("chat-tool-pending");

  try {
    const data = await enviarMensajeChat(texto, historialChat);

    if (indicadorDB) {
      if (data.tool_usada) {
        const textos = {
          "get_gastos_periodo":             "Consultando gastos por período…",
          "get_evolucion_categoria":        "Analizando evolución de categoría…",
          "get_resumen_ingresos_vs_gastos": "Calculando balance ingresos/gastos…",
          "get_progreso_objetivo":          "Consultando progreso del objetivo…",
          "get_top_gastos":                 "Buscando tus mayores gastos…",
        };
        const spanTexto = indicadorDB.querySelector(".tool-texto");
        if (spanTexto) spanTexto.textContent = textos[data.tool_usada] || "Consultando base de datos…";
        indicadorDB.classList.remove("chat-tool-pending");
        indicadorDB.classList.add("chat-tool-done");
        setTimeout(() => { indicadorDB.style.maxHeight = "0"; indicadorDB.style.opacity = "0"; }, 2000);
      } else {
        indicadorDB.remove();
      }
    }

    if (burbujaEspera) {
      burbujaEspera.classList.remove("chat-escribiendo");
      burbujaEspera.innerHTML = "";
      burbujaEspera.textContent = data.respuesta || "El agente no devolvió respuesta.";
    }

    historialChat.push({ rol: "agente", texto: data.respuesta });

  } catch (error) {
    console.error("SFE: error en chat →", error.message);
    if (indicadorDB) indicadorDB.remove();
    if (burbujaEspera) {
      burbujaEspera.classList.remove("chat-escribiendo");
      burbujaEspera.classList.add("chat-burbuja--error");
      burbujaEspera.textContent = `⚠ Error al contactar al agente: ${error.message}`;
    }
  } finally {
    input.disabled = false;
    if (btnEnviar) btnEnviar.disabled = false;
    input.focus();
  }
}

// comprueba si hay API key guardada; si no, muestra el modal
function verificarApiKey() {
  const clave = localStorage.getItem("google_api_key");
  if (!clave || clave.trim() === "") {
    const modal = document.getElementById("modalApiKey");
    if (modal) {
      modal.style.display = "flex";
    } else {
      const ingresada = prompt("🔑 Sentinel Finance Engine\n\nIngresá tu Google AI (Gemini) API Key.");
      if (ingresada?.trim()) {
        localStorage.setItem("google_api_key", ingresada.trim());
      }
    }
    return false;
  }
  return true;
}

// abre el modal de objetivo y rellena los campos si ya hay datos cargados
function abrirModalObjetivo() {
  const modal = document.getElementById("modalObjetivo");
  if (!modal) return;

  // pre-rellenar con los valores actuales si están visibles en la card
  const nombre  = document.getElementById("objetivoNombre")?.textContent?.trim();
  const total   = document.getElementById("objetivoTotal")?.dataset?.raw;
  const actual  = document.getElementById("objetivoActual")?.dataset?.raw;
  const fecha   = document.getElementById("objetivoFecha")?.dataset?.raw;

  if (nombre && !nombre.includes("skeleton")) {
    const inNombre = document.getElementById("inputObjetivoNombre");
    if (inNombre) inNombre.value = nombre;
  }
  if (total)  { const el = document.getElementById("inputObjetivoImporte"); if (el) el.value = total; }
  if (actual) { const el = document.getElementById("inputObjetivoActual");  if (el) el.value = actual; }
  if (fecha)  { const el = document.getElementById("inputObjetivoFecha");   if (el) el.value = fecha; }

  // fecha mínima = mañana
  const inFecha = document.getElementById("inputObjetivoFecha");
  if (inFecha && !inFecha.value) {
    const manana = new Date();
    manana.setDate(manana.getDate() + 1);
    inFecha.min = manana.toISOString().split("T")[0];
  }

  const errEl = document.getElementById("modalObjetivoError");
  if (errEl) errEl.style.display = "none";

  modal.style.display = "flex";
  document.getElementById("inputObjetivoNombre")?.focus();
}

// valida y envía el formulario del objetivo
async function guardarObjetivo() {
  const nombre  = document.getElementById("inputObjetivoNombre")?.value.trim();
  const importe = parseFloat(document.getElementById("inputObjetivoImporte")?.value);
  const actual  = parseFloat(document.getElementById("inputObjetivoActual")?.value || "0");
  const fecha   = document.getElementById("inputObjetivoFecha")?.value;
  const errEl   = document.getElementById("modalObjetivoError");
  const btn     = document.querySelector("#modalObjetivo .modal-btn");

  const mostrarError = (msg) => {
    if (errEl) { errEl.textContent = msg; errEl.style.display = "block"; }
  };

  if (!nombre)           return mostrarError("⚠ El nombre no puede estar vacío.");
  if (!importe || importe <= 0) return mostrarError("⚠ El importe debe ser mayor que 0.");
  if (isNaN(actual) || actual < 0) return mostrarError("⚠ El importe ya ahorrado no puede ser negativo.");
  if (!fecha)            return mostrarError("⚠ Seleccioná una fecha límite.");
  if (actual >= importe) return mostrarError("⚠ Lo ya ahorrado no puede superar el objetivo.");

  if (errEl) errEl.style.display = "none";
  if (btn) { btn.disabled = true; btn.textContent = "Guardando…"; }

  try {
    const obj = await crearObjetivo(nombre, importe, actual, fecha);
    document.getElementById("modalObjetivo").style.display = "none";
    renderizarObjetivo(obj);
    if (btn) { btn.disabled = false; btn.textContent = "Guardar objetivo"; }
  } catch (err) {
    mostrarError(`Error al guardar: ${err.message}`);
    if (btn) { btn.disabled = false; btn.textContent = "Guardar objetivo"; }
  }
}

// las tres peticiones principales van en paralelo para no esperar en cadena
async function inicializarDashboard() {
  verificarApiKey();

  try {
    const [datos, resumen, topGastos] = await Promise.all([
      fetchDashboardData(PERIODO_ACTIVO),
      fetchResumen(PERIODO_ACTIVO),
      fetchTopGastos(PERIODO_ACTIVO, 5),
    ]);

    if (!datos?.gastos_por_categoria) {
      throw new Error("La respuesta de /api/dashboard no cumple el contrato JSON.");
    }

    renderizarResumen(resumen);
    renderizarGrafico(datos.gastos_por_categoria);
    renderizarTopGastos(topGastos);

    document.querySelectorAll(".filtro-btn").forEach((btn) => {
      btn.classList.toggle("filtro-btn--activo", btn.dataset.periodo === PERIODO_ACTIVO);
    });

    // el objetivo va aparte para que un fallo aquí no bloquee el resto del dashboard
    fetchObjetivo()
      .then((obj) => renderizarObjetivo(obj))
      .catch((err) => {
        if (err.message.includes("404")) {
          const cont = document.getElementById("objetivosContainer");
          if (cont) {
            cont.innerHTML = `
              <div class="panel-header">
                <h2 class="panel-title">Objetivo de ahorro</h2>
              </div>
              <div style="padding:1.5rem 0;text-align:center;">
                <p style="color:var(--text-muted);font-size:.82rem;margin-bottom:1rem;">
                  Aún no tienes ningún objetivo definido.
                </p>
                <button class="modal-btn" style="width:auto;padding:.55rem 1.5rem;font-size:.82rem;" onclick="abrirModalObjetivo()">
                  + Crear objetivo
                </button>
              </div>
            `;
            cont.style.opacity = "1";
          }
        } else {
          console.warn("SFE: no se pudo cargar el objetivo →", err.message);
          const cont = document.getElementById("objetivosContainer");
          if (cont) {
            cont.innerHTML = `<p style="color:var(--text-muted);font-size:.75rem;padding:1rem 0;">No se pudo cargar el objetivo de ahorro.</p>`;
            cont.style.opacity = "1";
          }
        }
      });

    console.info(`SFE: dashboard listo (período: ${PERIODO_ACTIVO}).`);
  } catch (error) {
    console.error("SFE: error al cargar el dashboard →", error.message);
    mostrarErrorGlobal(error.message);
  }
}

// toast de error en la esquina inferior derecha y desaparece a los 8 segundos
function mostrarErrorGlobal(mensaje) {
  let el = document.getElementById("errorGlobal");
  if (!el) {
    el = document.createElement("div");
    el.id = "errorGlobal";
    el.style.cssText =
      "position:fixed;bottom:1.5rem;right:1.5rem;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.4);border-left:3px solid #EF4444;color:#FCA5A5;padding:.9rem 1.25rem;border-radius:6px;font-size:.75rem;max-width:360px;z-index:9999;";
    document.body.appendChild(el);
  }
  el.textContent = `⚠ Error SFE: ${mensaje}`;
  el.style.display = "block";
  setTimeout(() => { el.style.display = "none"; }, 8000);
}

document.addEventListener("DOMContentLoaded", () => {
  inicializarDashboard();

  const chatInput = document.getElementById("chatInput");
  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        enviarMensaje();
      }
    });
  }

  // cerrar modal objetivo con Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const modal = document.getElementById("modalObjetivo");
      if (modal && modal.style.display !== "none") {
        modal.style.display = "none";
      }
    }
  });

  // enviar formulario objetivo con Enter en el campo de fecha
  document.getElementById("inputObjetivoFecha")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") guardarObjetivo();
  });

  setTimeout(() => {
    _agregarBurbuja(
      "👋🏻 Hola, soy tu asistente financiero. Puedo consultar tus gastos, analizar categorías, revisar tu objetivo de ahorro y mostrarte tus mayores gastos. ¿En qué te puedo ayudar?",
      "agente"
    );
  }, 1200);
});