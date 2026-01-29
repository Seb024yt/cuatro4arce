// app/ui/components/table.js
/**
 * Table helper: construye tabla con headers y rows (ya sanitizados).
 * headers: string[]
 * rows: Array<Array<string | HTMLElement>>
 */
export function buildTable({ headers = [], rows = [] }) {
  const table = document.createElement("table");

  const thead = document.createElement("thead");
  const trh = document.createElement("tr");
  headers.forEach(h => {
    const th = document.createElement("th");
    th.textContent = h;
    trh.appendChild(th);
  });
  thead.appendChild(trh);

  const tbody = document.createElement("tbody");
  rows.forEach(r => {
    const tr = document.createElement("tr");
    r.forEach(cell => {
      const td = document.createElement("td");
      if (cell instanceof HTMLElement) td.appendChild(cell);
      else td.textContent = String(cell ?? "");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  return table;
}
