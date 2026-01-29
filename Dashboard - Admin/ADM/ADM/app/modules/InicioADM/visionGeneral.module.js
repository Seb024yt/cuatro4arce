// modules/InicioADM/visionGeneral.module.js
import { store } from "../../data/store.js";
import { getSiiaiStatus } from "../../services/siiai.service.js";

/**
 * KPIs ejecutivos de la Visión General
 * - Mantiene la lógica centralizada para que la vista sea liviana.
 */
export function getVisionGeneralKPIs() {
  const claveTotal = store.claveEmpresas.length;
  const claveAlta = store.claveEmpresas.filter(e => e.status === "alta").length;

  const siiaiActive = store.siiaiClientes.filter(c => getSiiaiStatus(c).key === "active").length;

  return {
    claveTotal,
    clavePend: claveAlta,
    siiaiActive,
  };
}

/**
 * Checklist operativo (texto)
 * - Ideal para estandarizar operación diaria.
 */
export function getChecklistOperacional() {
  return [
    "Clave Tributaria: validar credenciales, ejecutar lote F29, descargar masivo, archivar evidencias.",
    "SII-AI: monitorear vencimientos, upgrades, control de acceso a credenciales, auditoría de cambios.",
    "Estándar recomendado: log_id por acción + usuario operador + timestamp.",
  ];
}

/**
 * Actividad reciente
 */
export function getActividadReciente(limit = 12) {
  return (store.activity || []).slice(0, limit);
}
