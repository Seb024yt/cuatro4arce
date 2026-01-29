// modules/InicioADM/claveTributaria.module.js
import { store } from "../../data/store.js";
import {
  listClaveEmpresas,
  generateF29Batch,
  downloadF29Batch,
  updateClaveEmpresa,
  deleteClaveEmpresa
} from "../../services/clave.service.js";

/**
 * Listado + filtros para Clave Tributaria
 * Nota: "status" representa la importancia (alta/media/baja).
 */
export function getClaveListado({ query = "", status = "all" } = {}) {
  return listClaveEmpresas({ query, status });
}

/**
 * KPIs operativos para Clave Tributaria
 */
export function getClaveKPIs() {
  const total = store.claveEmpresas.length;
  const alta = store.claveEmpresas.filter(e => e.status === "alta").length;
  const media = store.claveEmpresas.filter(e => e.status === "media").length;
  const baja = store.claveEmpresas.filter(e => e.status === "baja").length;

  return { total, alta, media, baja };
}

/**
 * Acciones batch (lote)
 */
export function runClaveBatchGenerate(ids = []) {
  return generateF29Batch(ids);
}

export function runClaveBatchDownload(ids = []) {
  return downloadF29Batch(ids);
}

/**
 * Acciones unitarias (edición / baja)
 */
export function patchClaveEmpresa(id, patch) {
  return updateClaveEmpresa(id, patch);
}

export function removeClaveEmpresa(id) {
  return deleteClaveEmpresa(id);
}
