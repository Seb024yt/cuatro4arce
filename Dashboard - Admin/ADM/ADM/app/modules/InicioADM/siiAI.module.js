// modules/InicioADM/siiAi.module.js
import { store } from "../../data/store.js";
import {
  listSiiaiClients,
  getSiiaiStatus,
  addSiiaiClient,
  updateSiiaiClient,
  applySiiaiUpgrade,
  deleteSiiaiClient
} from "../../services/siiai.service.js";

/**
 * Listado + filtros para SII-AI
 */
export function getSiiaiListado({ query = "", status = "all" } = {}) {
  return listSiiaiClients({ query, status });
}

/**
 * KPIs ejecutivos para SII-AI
 */
export function getSiiaiKPIs() {
  const total = store.siiaiClientes.length;
  const active = store.siiaiClientes.filter(c => getSiiaiStatus(c).key === "active").length;
  const expiring = store.siiaiClientes.filter(c => getSiiaiStatus(c).key === "expiring").length;
  const expired = store.siiaiClientes.filter(c => getSiiaiStatus(c).key === "expired").length;

  return { total, active, expiring, expired };
}

/**
 * Estado por cliente
 */
export function getClienteStatus(cliente) {
  return getSiiaiStatus(cliente);
}

/**
 * Alta cliente (demo)
 */
export function createSiiaiClient() {
  return addSiiaiClient();
}

/**
 * Edición cliente
 */
export function patchSiiaiClient(id, patch) {
  return updateSiiaiClient(id, patch);
}

/**
 * Upgrade (empresas/tiempo)
 */
export function upgradeSiiaiClient(id, { addCompanies = 0, addMonths = 0 } = {}) {
  return applySiiaiUpgrade(id, { addCompanies, addMonths });
}

/**
 * Baja cliente
 */
export function removeSiiaiClient(id) {
  return deleteSiiaiClient(id);
}
