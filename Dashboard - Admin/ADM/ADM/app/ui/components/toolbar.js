// app/ui/components/toolbar.js
/**
 * Toolbar helper: retorna un contenedor .toolbar con dos áreas.
 * leftNodes/rightNodes: HTMLElement[]
 */
export function toolbar({ leftNodes = [], rightNodes = [] } = {}) {
  const el = document.createElement("div");
  el.className = "toolbar";

  const left = document.createElement("div");
  left.className = "leftTools";

  const right = document.createElement("div");
  right.className = "leftTools";

  leftNodes.forEach(n => left.appendChild(n));
  rightNodes.forEach(n => right.appendChild(n));

  el.appendChild(left);
  el.appendChild(right);
  return el;
}
