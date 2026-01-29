// app/services/clave.service.js
import { store } from "../data/store.js";
import { auditLog } from "./audit.service.js";

/**
 * Lista empresas Clave Tributaria aplicando filtros.
 * Nota: "status" representa la importancia (alta/media/baja).
 */
export function listClaveEmpresas({ query = "", status = "all" } = {}) {
  const q = (query || "").toLowerCase().trim();
  return store.claveEmpresas.filter(e => {
    const matchesQ = !q || e.name.toLowerCase().includes(q) || e.rut.toLowerCase().includes(q);
    const matchesS = status === "all" || e.status === status;
    return matchesQ && matchesS;
  });
}

/**
 * Generación F29 en lote (demo): no altera la importancia.
 */
export function generateF29Batch(ids = []) {
  if (!ids.length) return { updated: 0 };

  auditLog({
    unit: "Clave Tributaria",
    action: `Generación F29 lote: ${ids.length} empresa(s)`,
    result: "OK",
  });

  return { updated: ids.length };
}

/**
 * Descarga masiva (demo): solo registra auditoría.
 */
export function downloadF29Batch(ids = []) {
  auditLog({
    unit: "Clave Tributaria",
    action: `Descarga masiva F29 (demo): ${ids.length} empresa(s)`,
    result: "OK",
  });

  return { ok: true };
}

/**
 * Edita empresa (whitelist de campos).
 */
export function updateClaveEmpresa(id, patch) {
  const e = store.claveEmpresas.find(x => x.id === id);
  if (!e) return { ok: false, error: "not_found" };

  const allowed = ["name", "rut", "period", "status"];
  for (const k of allowed) {
    if (k in patch) e[k] = patch[k];
  }

  auditLog({
    unit: "Clave Tributaria",
    action: `Edición empresa (demo): ${e.name}`,
    result: "OK",
  });

  return { ok: true, empresa: e };
}

/**
 * Elimina empresa.
 */
export function deleteClaveEmpresa(id) {
  const idx = store.claveEmpresas.findIndex(x => x.id === id);
  if (idx < 0) return { ok: false, error: "not_found" };

  const name = store.claveEmpresas[idx].name;
  store.claveEmpresas.splice(idx, 1);

  auditLog({
    unit: "Clave Tributaria",
    action: `Baja empresa (demo): ${name}`,
    result: "OK",
  });

  return { ok: true };
}
