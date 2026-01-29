// app/ui/views/InicioADM/clave-tributaria.view.js
import { state } from "../../../core/state.js";
import { statusPill } from "../../components/pills.js";
import { toast } from "../../components/toast.js";
import { openEditModal } from "../../../modules/edicionesIndependientes.module.js";
import {
  getClaveListado,
  runClaveBatchGenerate,
  runClaveBatchDownload
} from "../../../modules/InicioADM/claveTributaria.module.js";

function importanceMeta(value) {
  if (value === "alta") return { label: "Alta", kind: "bad" };
  if (value === "media") return { label: "Media", kind: "warn" };
  return { label: "Baja", kind: "good" };
}

export function renderClaveTributaria() {
  const section = document.createElement("section");
  section.id = "view-clave";
  section.style.display = "block";

  // Persistencia de selección (en memoria runtime)
  state.claveSelected = state.claveSelected || new Set();

  section.innerHTML = `
    <div class="card">
      <h3>Clave Tributaria • Generación y descarga masiva F29</h3>

      <div class="toolbar">
        <div class="leftTools">
          <input id="claveSearch" placeholder="Buscar por empresa o RUT…" />
          <select id="claveFilter">
            <option value="all">Importancia: Todas</option>
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
        </div>
        <div class="leftTools">
          <button class="btn" id="btnSelectAllClave">Seleccionar todo</button>
          <button class="btn primary" id="btnGenerateF29">Generar F29 (lote)</button>
          <button class="btn" id="btnDownloadF29">Descargar masivo</button>
        </div>
      </div>

      <div style="height:12px"></div>

      <table>
        <thead>
          <tr>
            <th style="width:44px;">Sel</th>
            <th>Empresa</th>
            <th>RUT</th>
            <th>Periodo</th>
            <th>Importancia</th>
            <th style="width:180px; text-align:right;">Acciones</th>
          </tr>
        </thead>
        <tbody id="claveTableBody"></tbody>
      </table>
    </div>
  `;

  const $search = section.querySelector("#claveSearch");
  const $filter = section.querySelector("#claveFilter");
  const $tbody  = section.querySelector("#claveTableBody");

  // Inicializar desde state.filters
  $search.value = state.filters?.claveQuery || "";
  $filter.value = state.filters?.claveStatus || "all";

  function renderRows() {
    const query = ($search.value || "").trim();
    const status = $filter.value;

    // Persistir filtros globales
    state.filters.claveQuery = query;
    state.filters.claveStatus = status;

    const rows = getClaveListado({ query, status });

    $tbody.innerHTML = rows.map(e => {
      const imp = importanceMeta(e.status);
      const pill = statusPill(imp.label, imp.kind).outerHTML;

      const checked = state.claveSelected.has(e.id) ? "checked" : "";

      return `
        <tr>
          <td><input type="checkbox" class="claveSel" data-id="${e.id}" ${checked}/></td>
          <td><b>${e.name}</b></td>
          <td class="mono">${e.rut}</td>
          <td class="mono">${e.period}</td>
          <td>${pill}</td>
          <td>
            <div class="rowActions" style="justify-content:flex-end;">
              <button class="btn" data-action="preview" data-id="${e.id}">Editar</button>
              <button class="btn primary" data-action="run" data-id="${e.id}">Resumen</button>
            </div>
          </td>
        </tr>
      `;
    }).join("") || `
      <tr><td colspan="6" class="muted">Sin resultados para los filtros aplicados.</td></tr>
    `;

    // Bind checkboxes
    $tbody.querySelectorAll("input.claveSel").forEach(chk => {
      chk.addEventListener("change", () => {
        const id = chk.dataset.id;
        if (chk.checked) state.claveSelected.add(id);
        else state.claveSelected.delete(id);
      });
    });

    // Bind row actions
    $tbody.querySelectorAll("button[data-action]").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.id;
        const action = btn.dataset.action;

        if (action === "preview") {
          openEditModal({ unit: "clave", id });
          return;
        }

        if (action === "run") {
          runClaveBatchGenerate([id]);
          toast("Resumen demo generado.", "ok");
          renderRows();
          return;
        }
      });
    });
  }

  // Eventos toolbar
  $search.addEventListener("input", renderRows);
  $filter.addEventListener("change", renderRows);

  section.querySelector("#btnSelectAllClave").addEventListener("click", () => {
    const query = ($search.value || "").trim();
    const status = $filter.value;
    const rows = getClaveListado({ query, status });

    const ids = rows.map(r => r.id);
    const allSelected = ids.length > 0 && ids.every(id => state.claveSelected.has(id));

    if (allSelected) {
      ids.forEach(id => state.claveSelected.delete(id));
      renderRows();
      toast("Selección limpiada.", "info");
      return;
    }

    ids.forEach(id => state.claveSelected.add(id));
    renderRows();
    toast(`Seleccionadas: ${ids.length}`, "info");
  });

  section.querySelector("#btnGenerateF29").addEventListener("click", () => {
    const ids = Array.from(state.claveSelected);
    if (!ids.length) { toast("Seleccione al menos 1 empresa.", "warn"); return; }

    const res = runClaveBatchGenerate(ids);
    toast(`Generación demo OK. Procesadas: ${res.updated}`, "ok");
    renderRows();
  });

  section.querySelector("#btnDownloadF29").addEventListener("click", () => {
    const ids = Array.from(state.claveSelected);
    if (!ids.length) { toast("Seleccione al menos 1 empresa.", "warn"); return; }

    runClaveBatchDownload(ids);
    toast("Descarga masiva demo registrada en auditoría.", "ok");
  });

  renderRows();
  return section;
}

