// app/ui/views/auditoria.view.js
import { store } from "../../data/store.js";
import { statusPill } from "../components/pills.js";
import { buildTable } from "../components/table.js";

export function renderAuditoria() {
  const section = document.createElement("section");
  section.id = "view-auditoria";
  section.style.display = "block";

  section.innerHTML = `
    <div class="card">
      <h3>Auditoría</h3>
      <div class="hintBox">
        Visor de logs (demo). Para producción: filtros por usuario/rol, unidad, acción, rango de fechas y exportación CSV/JSON.
      </div>
      <div style="height:12px"></div>
      <div id="auditTable"></div>
    </div>
  `;

  const acts = (store.activity || []).slice(0, 200);
  const headers = ["Fecha", "Unidad", "Acción", "Resultado"];
  const rows = acts.map(a => {
    const kind = a.result === "OK" ? "good" : (a.result === "ALERTA" ? "warn" : "bad");
    return [a.date, a.unit, a.action, statusPill(a.result, kind)];
  });

  section.querySelector("#auditTable").appendChild(buildTable({ headers, rows }));
  return section;
}
