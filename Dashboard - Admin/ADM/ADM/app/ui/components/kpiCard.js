// app/ui/components/kpiCard.js
export function kpiCard({ label, value, hint }) {
  const el = document.createElement("div");
  el.className = "kpi";
  el.innerHTML = `
    <div class="label">${label}</div>
    <div class="value">${value}</div>
    <div class="hint">${hint}</div>
  `;
  return el;
}
