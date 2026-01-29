// app/ui/views/unidades-operativas.view.js
import { store } from "../../data/store.js";

export function renderUnidadesOperativas() {
  const section = document.createElement("section");
  section.id = "view-unidades-operativas";
  section.style.display = "block";

  const claveAlta = store.claveEmpresas.filter(e => e.status === "alta").length;

  section.innerHTML = `
    <div class="card">
      <h3>Unidades operativas</h3>
      <div class="hintBox">
        Este módulo consolida la operación diaria por unidad (colas, prioridades, SLA, y evidencias).
        Recomendado: definir un <span class="mono">job_id</span> por corrida nocturna y asociar outputs (CSV/XLM/PDF) por empresa/período.
      </div>
    </div>

    <div class="card" style="margin-top:12px;">
      <h3>Resumen operativo (demo)</h3>
      <table>
        <thead>
          <tr>
            <th>Unidad</th>
            <th>Indicador</th>
            <th>Detalle</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><b>Clave Tributaria</b></td>
            <td>Empresas importancia alta</td>
            <td class="mono">${claveAlta}</td>
          </tr>
          <tr>
            <td><b>SII-AI</b></td>
            <td>Gestión planes</td>
            <td class="mono">Renovaciones / upgrades / vencimientos</td>
          </tr>
        </tbody>
      </table>
    </div>
  `;

  return section;
}
