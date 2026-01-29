// app/ui/views/InicioADM/vision-general.view.js
import { statusPill } from "../../components/pills.js";
import { buildTable } from "../../components/table.js";
import {
  getVisionGeneralKPIs,
  getChecklistOperacional,
  getActividadReciente
} from "../../../modules/InicioADM/visionGeneral.module.js";

export function renderVisionGeneral() {
  const section = document.createElement("section");
  section.id = "view-dashboard";
  section.style.display = "block";

  section.innerHTML = `
    <div class="grid">
      <div class="card">
        <h3>Indicadores clave</h3>
        <div class="kpis">
          <div class="kpi">
            <div class="label">Clave Tributaria • empresas</div>
            <div class="value" id="kpiClaveEmpresas">—</div>
            <div class="hint">Cartera total administrada</div>
          </div>
          <div class="kpi">
            <div class="label">Importancia alta</div>
            <div class="value" id="kpiF29Pendientes">—</div>
            <div class="hint">Empresas prioritarias</div>
          </div>
          <div class="kpi">
            <div class="label">SII-AI • suscripciones</div>
            <div class="value" id="kpiSiiaiClientes">—</div>
            <div class="hint">Clientes activos</div>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Checklist operacional</h3>
        <div class="hintBox" id="checklistBox"></div>
      </div>
    </div>

    <div class="card">
      <h3>Actividad reciente (demo)</h3>
      <div id="activityWrap"></div>
    </div>
  `;

  // KPIs
  const k = getVisionGeneralKPIs();
  section.querySelector("#kpiClaveEmpresas").textContent = String(k.claveTotal);
  section.querySelector("#kpiF29Pendientes").textContent = String(k.clavePend);
  section.querySelector("#kpiSiiaiClientes").textContent = String(k.siiaiActive);

  // Checklist
  const checklist = getChecklistOperacional();
  section.querySelector("#checklistBox").innerHTML = `
    ${checklist.map(line => `${line}`).join("<br/>")}
  `;

  // Actividad
  const acts = getActividadReciente(50);
  const headers = ["Fecha", "Unidad", "Acción", "Resultado"];
  const rows = acts.map(a => {
    const kind = a.result === "OK" ? "good" : (a.result === "ALERTA" ? "warn" : "bad");
    return [a.date, a.unit, a.action, statusPill(a.result, kind)];
  });

  const table = buildTable({ headers, rows });
  section.querySelector("#activityWrap").appendChild(table);

  return section;
}
