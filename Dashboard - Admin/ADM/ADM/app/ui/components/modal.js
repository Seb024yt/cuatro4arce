// app/ui/components/modal.js
import { $ } from "../../core/dom.js";

let mounted = false;

function ensureMounted() {
  if (mounted) return;

  const root = $("#modalRoot");
  root.innerHTML = `
    <div class="modalBackdrop" id="admModalBackdrop" aria-hidden="true">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modalHeader">
          <div>
            <h4 id="admModalTitle">Editar</h4>
            <p id="admModalSubtitle">Actualice atributos y aplique cambios con trazabilidad.</p>
          </div>
          <button class="btn" id="admModalClose">Cerrar</button>
        </div>

        <div class="modalBody" id="admModalBody"></div>

        <div class="modalFooter">
          <button class="btn" id="admModalDelete" style="display:none;">Eliminar</button>
          <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <button class="btn" id="admModalCancel">Cancelar</button>
            <button class="btn primary" id="admModalSave">Guardar cambios</button>
          </div>
        </div>
      </div>
    </div>
  `;

  const backdrop = $("#admModalBackdrop");
  const close = () => closeModal();

  $("#admModalClose").addEventListener("click", close);
  $("#admModalCancel").addEventListener("click", close);

  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });

  mounted = true;
}

let current = { schema: null, values: {}, onSave: null, onDelete: null };

export function openModal({ title, subtitle, schema, initialValues, onSave, onDelete }) {
  ensureMounted();

  current = {
    schema,
    values: structuredClone(initialValues || {}),
    onSave,
    onDelete,
  };

  $("#admModalTitle").textContent = title || "Editar";
  $("#admModalSubtitle").textContent = subtitle || "";

  const body = $("#admModalBody");
  body.innerHTML = "";

  (schema.fields || []).forEach(f => {
    const field = document.createElement("div");
    field.className = "field";

    const label = document.createElement("label");
    label.textContent = f.label || f.key;

    let input;
    if (f.type === "select") {
      input = document.createElement("select");
      (f.options || []).forEach(opt => {
        const o = document.createElement("option");
        if (typeof opt === "string") {
          o.value = opt;
          o.textContent = opt;
        } else {
          o.value = opt.value;
          o.textContent = opt.label;
        }
        input.appendChild(o);
      });
    } else {
      input = document.createElement("input");
      input.type = f.type || "text";
      if (f.placeholder) input.placeholder = f.placeholder;
      if (f.min !== undefined) input.min = String(f.min);
    }

    input.value = (current.values[f.key] ?? "");
    if (f.disabled) input.disabled = true;

    input.addEventListener("input", () => {
      current.values[f.key] = input.value;
    });

    field.appendChild(label);
    field.appendChild(input);
    if (f.fullRow) field.style.gridColumn = "1 / -1";
    body.appendChild(field);
  });

  if (schema.hint) {
    const hint = document.createElement("div");
    hint.className = "field";
    hint.style.gridColumn = "1 / -1";
    hint.innerHTML = `<div class="hintBox">${schema.hint}</div>`;
    body.appendChild(hint);
  }

  const delBtn = $("#admModalDelete");
  if (typeof onDelete === "function") {
    delBtn.style.display = "inline-flex";
    delBtn.onclick = () => { onDelete(); closeModal(); };
  } else {
    delBtn.style.display = "none";
    delBtn.onclick = null;
  }

  $("#admModalSave").onclick = () => {
    if (typeof onSave === "function") onSave(current.values);
    closeModal();
  };

  const bd = $("#admModalBackdrop");
  bd.style.display = "flex";
  bd.setAttribute("aria-hidden", "false");
}

export function closeModal() {
  if (!mounted) return;
  const bd = $("#admModalBackdrop");
  bd.style.display = "none";
  bd.setAttribute("aria-hidden", "true");
}
