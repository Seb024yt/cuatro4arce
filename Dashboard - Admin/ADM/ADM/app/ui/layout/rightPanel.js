// app/ui/layout/rightPanel.js
import { state } from "../../core/state.js";
import { store } from "../../data/store.js";
import { openEditModal } from "../../modules/edicionesIndependientes.module.js";
import { getSiiaiStatus } from "../../services/siiai.service.js";
import { statusPill } from "../components/pills.js";

function importanceMeta(value) {
  if (value === "alta") return { label: "Alta", kind: "bad" };
  if (value === "media") return { label: "Media", kind: "warn" };
  return { label: "Baja", kind: "good" };
}

export function renderRightPanel(mount){
  const isClave = state.unit === "clave";
  const segClaveClass = isClave ? "active" : "";
  const segSiiaiClass = !isClave ? "active" : "";

  mount.innerHTML = `
    <div>
      <h3 style="margin:6px 2px 10px; font-size:13px;">Unidades operativas</h3>
      <div class="segmented" role="tablist" aria-label="Selector de unidad">
        <button id="segClave" class="${segClaveClass}" data-unit="clave" role="tab">Clave Tributaria</button>
        <button id="segSiiai" class="${segSiiaiClass}" data-unit="siiai" role="tab">SII-AI</button>
      </div>
    </div>

    <div class="card">
      <h3 id="rightTitle"></h3>
      <div class="hintBox" id="rightHint" style="margin-top:8px;"></div>
    </div>

    <div class="list" id="rightList"></div>
  `;

  const segClave = mount.querySelector("#segClave");
  const segSiiai = mount.querySelector("#segSiiai");

  segClave.addEventListener("click", () => {
    if (state.unit !== "clave") {
      state.unit = "clave";
      window.ADM.refresh();
    }
  });
  segSiiai.addEventListener("click", () => {
    if (state.unit !== "siiai") {
      state.unit = "siiai";
      window.ADM.refresh();
    }
  });

  const title = mount.querySelector("#rightTitle");
  const hint = mount.querySelector("#rightHint");
  const list = mount.querySelector("#rightList");

  if (isClave) {
    title.textContent = "Clave Tributaria • Empresas";
    hint.textContent = "Contexto: empresas con importancia operativa para priorización y seguimiento.";

    list.innerHTML = store.claveEmpresas.map(e => {
      const imp = importanceMeta(e.status);
      const pill = statusPill(imp.label, imp.kind);

      return `
        <div class="item">
          <div class="info">
            <div class="name">${e.name}</div>
            <div class="sub">
              <span class="mono">${e.rut}</span>
              <span class="mono">Periodo ${e.period}</span>
            </div>
            <div>${pill.outerHTML}</div>
          </div>
          <button class="btn" data-id="${e.id}">Editar</button>
        </div>
      `;
    }).join("");

    list.querySelectorAll("button[data-id]").forEach(btn => {
      btn.addEventListener("click", () => {
        openEditModal({ unit: "clave", id: btn.dataset.id });
      });
    });

    return;
  }

  title.textContent = "SII-AI • Empresas (clientes)";
  hint.textContent = "Contexto: clientes con credenciales, plan contratado, fechas y opción de upgrade (empresas/tiempo).";

  list.innerHTML = store.siiaiClientes.map(c => {
    const st = getSiiaiStatus(c);
    return `
      <div class="item">
        <div class="info">
          <div class="name">${c.name}</div>
          <div class="sub">
            <span class="mono">${c.rut}</span>
            <span class="pill">${c.plan}</span>
          </div>
          <div>${statusPill(st.label, st.kind)}</div>
        </div>
        <button class="btn primary" data-id="${c.id}">Editar</button>
      </div>
    `;
  }).join("");

  list.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", () => {
      openEditModal({ unit: "siiai", id: btn.dataset.id });
    });
  });
}
