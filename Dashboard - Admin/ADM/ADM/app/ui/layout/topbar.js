// app/ui/layout/topbar.js
import { state } from "../../core/state.js";
import { exportClaveCSV, exportSiiaiCSV, exportActivityCSV } from "../../services/export.service.js";

export function renderTopbar(){
  const el = document.createElement("div");
  el.style.display = "flex";
  el.style.alignItems = "center";
  el.style.justifyContent = "space-between";
  el.style.gap = "12px";
  el.style.marginBottom = "14px";

  el.innerHTML = `
    <div>
      <div style="font-weight:900;">Visión General</div>
      <div class="muted" style="font-size:12px;">Monitoreo ejecutivo y operación diaria. Seleccione unidad y ejecute acciones con trazabilidad.</div>
    </div>
    <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; align-items:center;">
      <span class="pill">Unidad: Consola</span>
      <button class="btn" id="btnExport">Exportar</button>
      <button class="btn primary" id="btnQuick">Acción rápida</button>
    </div>
  `;

  el.querySelector("#btnExport").addEventListener("click", () => {
    const view = state.view;

    if (view === "clave-tributaria") {
      const res = exportClaveCSV({
        query: state.filters.claveQuery || "",
        status: state.filters.claveStatus || "all",
      });
      alert(`[EXPORT] Clave Tributaria: ${res.count} registro(s).`);
      return;
    }

    if (view === "sii-ai") {
      const res = exportSiiaiCSV({
        query: state.filters.siiaiQuery || "",
        status: state.filters.siiaiStatus || "all",
        includePassword: false,
      });
      alert(`[EXPORT] SII-AI: ${res.count} registro(s).`);
      return;
    }

    const res = exportActivityCSV({ limit: 200 });
    alert(`[EXPORT] Auditoría: ${res.count} registro(s).`);
  });

  el.querySelector("#btnQuick").addEventListener("click", () => {
    if (state.view === "clave-tributaria") {
      alert("[DEMO] Acción rápida: ejecutar lote F29 para seleccionadas / pendientes.");
      return;
    }
    if (state.view === "sii-ai") {
      alert("[DEMO] Acción rápida: priorizar clientes por vencer y ejecutar upgrade/renovación.");
      return;
    }
    alert("[DEMO] Acción rápida: revisar Unidades operativas y Auditoría.");
  });

  return el;
}
