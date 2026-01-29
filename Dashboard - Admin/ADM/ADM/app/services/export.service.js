// app/services/export.service.js
import { store } from "../data/store.js";
import { auditLog } from "./audit.service.js";

function escapeCSV(value) {
  if (value === null || value === undefined) return "";
  const str = String(value);
  const needsQuotes = /[",\n;]/.test(str);
  const escaped = str.replace(/"/g, '""');
  return needsQuotes ? `"${escaped}"` : escaped;
}

function toCSV(headers, rows) {
  const sep = ";"; // recomendado para Excel (config regional frecuente)
  const head = headers.map(escapeCSV).join(sep);
  const body = rows.map(r => r.map(escapeCSV).join(sep)).join("\n");
  return `${head}\n${body}\n`;
}

function downloadTextFile(filename, content, mime = "text/csv;charset=utf-8") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
}

function fileStamp() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}${mm}${dd}_${hh}${mi}`;
}

/**
 * Exporta Clave Tributaria a CSV (aplica filtros por importancia)
 */
export function exportClaveCSV({ query = "", status = "all" } = {}) {
  const q = (query || "").toLowerCase().trim();

  const filtered = store.claveEmpresas.filter(e => {
    const matchesQ = !q || e.name.toLowerCase().includes(q) || e.rut.toLowerCase().includes(q);
    const matchesS = status === "all" || e.status === status;
    return matchesQ && matchesS;
  });

  const headers = ["id", "empresa", "rut", "periodo", "importancia"];
  const rows = filtered.map(e => [e.id, e.name, e.rut, e.period, e.status]);

  const csv = toCSV(headers, rows);
  const name = `clave_tributaria_${fileStamp()}.csv`;

  downloadTextFile(name, csv);

  auditLog({
    unit: "Consola",
    action: `Export CSV (Clave Tributaria): ${filtered.length} registro(s) [importancia=${status}]`,
    result: "OK",
  });

  return { ok: true, count: filtered.length };
}

/**
 * Exporta SII-AI a CSV (aplica filtros)
 * Nota: includePassword por defecto false (no exportar secretos).
 */
export function exportSiiaiCSV({ query = "", status = "all", includePassword = false } = {}) {
  const q = (query || "").toLowerCase().trim();

  // demo estable; en producciÃ³n: new Date()
  const today = new Date("2026-01-26");

  function statusKey(c) {
    const end = new Date(c.end);
    const days = Math.round((end - today) / (1000 * 60 * 60 * 24));
    if (days < 0) return "expired";
    if (days <= 14) return "expiring";
    return "active";
  }

  const filtered = store.siiaiClientes.filter(c => {
    const matchesQ = !q || c.name.toLowerCase().includes(q) || c.rut.toLowerCase().includes(q);
    const st = statusKey(c);
    const matchesS = status === "all" || status === st;
    return matchesQ && matchesS;
  });

  const headers = [
    "id",
    "empresa",
    "rut",
    ...(includePassword ? ["password"] : []),
    "plan",
    "fecha_incorporacion",
    "fecha_finalizacion",
    "max_empresas",
    "estado"
  ];

  const rows = filtered.map(c => ([
    c.id,
    c.name,
    c.rut,
    ...(includePassword ? [c.password || ""] : []),
    c.plan,
    c.start,
    c.end,
    c.maxCompanies,
    statusKey(c)
  ]));

  const csv = toCSV(headers, rows);
  const name = `sii_ai_${fileStamp()}.csv`;

  downloadTextFile(name, csv);

  auditLog({
    unit: "Consola",
    action: `Export CSV (SII-AI): ${filtered.length} registro(s) [status=${status}]`,
    result: "OK",
  });

  return { ok: true, count: filtered.length };
}

/**
 * Exporta auditorÃ­a/actividad a CSV
 */
export function exportActivityCSV({ limit = 200 } = {}) {
  const headers = ["fecha", "unidad", "accion", "resultado"];
  const rows = (store.activity || []).slice(0, limit).map(a => [
    a.date, a.unit, a.action, a.result
  ]);

  const csv = toCSV(headers, rows);
  const name = `auditoria_${fileStamp()}.csv`;

  downloadTextFile(name, csv);

  auditLog({
    unit: "Consola",
    action: `Export CSV (AuditorÃ­a): ${rows.length} registro(s)`,
    result: "OK",
  });

  return { ok: true, count: rows.length };
}

