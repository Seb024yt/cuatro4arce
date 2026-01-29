// app/ui/views/InicioADM/sii-ai.view.js
import { state } from "../../../core/state.js";
import { maskPassword } from "../../../core/utils.js";
import { statusPill } from "../../components/pills.js";
import { toast } from "../../components/toast.js";
import { openEditModal } from "../../../modules/edicionesIndependientes.module.js";
import { getSiiaiStatus } from "../../../services/siiai.service.js";
import {
  getSiiaiListado,
  createSiiaiClient
} from "../../../modules/InicioADM/siiAi.module.js";

export function renderSiiAI() {
  const section = document.createElement("section");
  section.id = "view-siiai";
  section.style.display = "block";

  section.innerHTML = `
    <div class="card">
      <h3>SII-AI • Clientes, cuentas y control de planes</h3>

      <div class="toolbar">
        <div class="leftTools">
          <input id="siiaiSearch" placeholder="Buscar por empresa o RUT…" />
          <select id="siiaiStatus">
            <option value="all">Estado: Todos</option>
            <option value="active">Activo</option>
            <option value="expiring">Por vencer</option>
            <option value="expired">Vencido</option>
          </select>
        </div>
        <div class="leftTools">
          <button class="btn" id="btnAddClient">Agregar cliente</button>
          <button class="btn primary" id="btnBulkUpgrade">Upgrade masivo</button>
        </div>
      </div>

      <div style="height:12px"></div>

      <table>
        <thead>
          <tr>
            <th>Empresa</th>
            <th>RUT</th>
            <th>Contraseña</th>
            <th>Plan</th>
            <th>Incorporación</th>
            <th>Finalización</th>
            <th>Estado</th>
            <th style="width:170px; text-align:right;">Acciones</th>
          </tr>
        </thead>
        <tbody id="siiaiTableBody"></tbody>
      </table>
    </div>
  `;

  const $search = section.querySelector("#siiaiSearch");
  const $status = section.querySelector("#siiaiStatus");
  const $tbody  = section.querySelector("#siiaiTableBody");

  $search.value = state.filters?.siiaiQuery || "";
  $status.value = state.filters?.siiaiStatus || "all";

  function renderRows() {
    const query = ($search.value || "").trim();
    const status = $status.value;

    state.filters.siiaiQuery = query;
    state.filters.siiaiStatus = status;

    const rows = getSiiaiListado({ query, status });

    $tbody.innerHTML = rows.map(c => {
      const st = getSiiaiStatus(c);
      const pill = statusPill(st.label, st.kind).outerHTML;

      return `
        <tr>
          <td><b>${c.name}</b> <span class="muted">• máx ${c.maxCompanies} emp.</span></td>
          <td class="mono">${c.rut}</td>
          <td class="mono">${maskPassword(c.password)}</td>
          <td><span class="pill">${c.plan}</span></td>
          <td class="mono">${c.start}</td>
          <td class="mono">${c.end}</td>
          <td>${pill}</td>
          <td>
            <div class="rowActions" style="justify-content:flex-end;">
              <button class="btn" data-action="edit" data-id="${c.id}">Editar</button>
              <button class="btn" data-action="upgrade" data-id="${c.id}">Upgrade</button>
            </div>
          </td>
        </tr>
      `;
    }).join("") || `
      <tr><td colspan="8" class="muted">Sin resultados para los filtros aplicados.</td></tr>
    `;

    $tbody.querySelectorAll("button[data-action]").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.id;
        const action = btn.dataset.action;

        if (action === "edit" || action === "upgrade") {
          openEditModal({ unit: "siiai", id });
          return;
        }
      });
    });
  }

  $search.addEventListener("input", renderRows);
  $status.addEventListener("change", renderRows);

  section.querySelector("#btnAddClient").addEventListener("click", () => {
    const c = createSiiaiClient();
    toast(`Cliente agregado (demo): ${c.name}`, "ok");
    renderRows();
  });

  section.querySelector("#btnBulkUpgrade").addEventListener("click", () => {
    toast("Upgrade masivo (demo): defina reglas de segmentación y aplique en backend.", "warn");
  });

  renderRows();
  return section;
}
