/* routes.js */
import { renderVisionGeneral } from "../ui/views/InicioADM/vision-general.view.js";
import { renderClaveTributaria } from "../ui/views/InicioADM/clave-tributaria.view.js";
import { renderSiiAI } from "../ui/views/InicioADM/sii-ai.view.js";
import { renderAuditoria } from "../ui/views/auditoria.view.js";
import { renderConfiguracion } from "../ui/views/configuracion.view.js";

export const routes = {
  "vision-general": renderVisionGeneral,
  "clave-tributaria": renderClaveTributaria,
  "sii-ai": renderSiiAI,
  "auditoria": renderAuditoria,
  "configuracion": renderConfiguracion,
};
