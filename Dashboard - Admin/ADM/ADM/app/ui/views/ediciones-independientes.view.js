// app/ui/views/ediciones-independientes.view.js
export function renderEdicionesIndependientes() {
  const section = document.createElement("section");
  section.id = "view-ediciones-independientes";
  section.style.display = "block";

  section.innerHTML = `
    <div class="card">
      <h3>Ediciones independientes</h3>
      <div class="hintBox">
        Este espacio consolida acciones de edición desacopladas por unidad (misma UI de modal, distinta lógica por tipo).
        En el sistema actual, se gestiona vía <span class="mono">modules/edicionesIndependientes.module.js</span>.
      </div>
    </div>
  `;

  return section;
}
