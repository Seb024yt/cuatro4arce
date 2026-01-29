// app/services/siiai.service.js
import { store } from "../data/store.js";
import { auditLog } from "./audit.service.js";

// Demo estable (para que los estados no cambien al pasar los días)
const DEMO_TODAY = new Date("2026-01-26");

/**
 * Estado de suscripción (active/expiring/expired)
 */
export function getSiiaiStatus(client, today = DEMO_TODAY) {
  const end = new Date(client.end);
  const days = Math.round((end - today) / (1000 * 60 * 60 * 24));

  if (days < 0) return { key: "expired", label: "Vencido", kind: "bad", days };
  if (days <= 14) return { key: "expiring", label: `Por vencer (${days}d)`, kind: "warn", days };
  return { key: "active", label: "Activo", kind: "good", days };
}

/**
 * Lista clientes SII-AI aplicando filtros.
 */
export function listSiiaiClients({ query = "", status = "all" } = {}) {
  const q = (query || "").toLowerCase().trim();

  return store.siiaiClientes.filter(c => {
    const matchesQ = !q || c.name.toLowerCase().includes(q) || c.rut.toLowerCase().includes(q);
    const st = getSiiaiStatus(c).key;
    const matchesS = status === "all" || status === st;
    return matchesQ && matchesS;
  });
}

/**
 * Alta cliente (demo).
 */
export function addSiiaiClient() {
  const id = "ai-" + Math.random().toString(16).slice(2, 7);

  const newClient = {
    id,
    name: "Nuevo Cliente (pendiente)",
    rut: "00.000.000-0",
    password: "",
    plan: "Starter",
    start: "2026-01-26",
    end: "2026-04-26",
    maxCompanies: 1,
  };

  store.siiaiClientes.unshift(newClient);

  auditLog({
    unit: "SII-AI",
    action: `Alta cliente (demo): ${newClient.name}`,
    result: "OK",
  });

  return newClient;
}

/**
 * Edita cliente (whitelist de campos).
 */
export function updateSiiaiClient(id, patch) {
  const c = store.siiaiClientes.find(x => x.id === id);
  if (!c) return { ok: false, error: "not_found" };

  const allowed = ["name", "rut", "password", "plan", "start", "end"];
  for (const k of allowed) {
    if (k in patch) c[k] = patch[k];
  }

  auditLog({
    unit: "SII-AI",
    action: `Edición cliente (demo): ${c.name}`,
    result: "OK",
  });

  return { ok: true, client: c };
}

/**
 * Upgrade (empresas/tiempo)
 */
export function applySiiaiUpgrade(id, { addCompanies = 0, addMonths = 0 } = {}) {
  const c = store.siiaiClientes.find(x => x.id === id);
  if (!c) return { ok: false, error: "not_found" };

  const companies = parseInt(addCompanies || 0, 10);
  const months = parseInt(addMonths || 0, 10);

  if (companies > 0) c.maxCompanies += companies;

  if (months > 0) {
    const end = new Date(c.end);
    end.setMonth(end.getMonth() + months);
    const yyyy = end.getFullYear();
    const mm = String(end.getMonth() + 1).padStart(2, "0");
    const dd = String(end.getDate()).padStart(2, "0");
    c.end = `${yyyy}-${mm}-${dd}`;
  }

  auditLog({
    unit: "SII-AI",
    action: `Upgrade (demo): ${c.name} (+${companies} emp, +${months} meses)`,
    result: "OK",
  });

  return { ok: true, client: c };
}

/**
 * Elimina cliente.
 */
export function deleteSiiaiClient(id) {
  const idx = store.siiaiClientes.findIndex(x => x.id === id);
  if (idx < 0) return { ok: false, error: "not_found" };

  const name = store.siiaiClientes[idx].name;
  store.siiaiClientes.splice(idx, 1);

  auditLog({
    unit: "SII-AI",
    action: `Baja cliente (demo): ${name}`,
    result: "OK",
  });

  return { ok: true };
}
