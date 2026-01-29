// app/services/audit.service.js
import { store } from "../data/store.js";

/**
 * Registra un evento en la bitácora.
 * Se inserta al inicio (más reciente arriba).
 */
export function auditLog({ unit, action, result = "OK" }) {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mi = String(now.getMinutes()).padStart(2, "0");

  store.activity.unshift({
    date: `${yyyy}-${mm}-${dd} ${hh}:${mi}`,
    unit,
    action,
    result,
  });
}
