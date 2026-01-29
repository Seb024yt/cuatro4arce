// app/modules/edicionesIndependientes.module.js
import { store } from "../data/store.js";
import { openModal } from "../ui/components/modal.js";

import { updateSiiaiClient, applySiiaiUpgrade, deleteSiiaiClient } from "../services/siiai.service.js";
import { updateClaveEmpresa, deleteClaveEmpresa } from "../services/clave.service.js";

const schemas = {
  siiai: {
    title: "Editar cliente (SII-AI)",
    subtitle: "Gestión de plan, fechas y upgrades (empresas/tiempo).",
    hint:
      "<b>Gobierno de datos:</b> En producción no almacene contraseñas en texto plano. " +
      "Utilice cifrado/vault y registre cambios en auditoría.",
    fields: [
      { key: "unit", label: "Unidad", type: "text", disabled: true },
      { key: "name", label: "Empresa", type: "text", placeholder: "Nombre empresa" },
      { key: "rut", label: "RUT", type: "text", placeholder: "11.111.111-1" },
      { key: "password", label: "Contraseña", type: "text", placeholder: "••••••••" },
      { key: "plan", label: "Plan", type: "select", options: ["Starter", "Pro", "Enterprise"] },
      { key: "start", label: "Fecha incorporación", type: "date" },
      { key: "end", label: "Fecha finalización", type: "date" },
      { key: "addCompanies", label: "Upgrade • Cantidad de empresas (+)", type: "number", min: 0, placeholder: "Ej: 1" },
      { key: "addMonths", label: "Upgrade • Extensión en meses (+)", type: "number", min: 0, placeholder: "Ej: 3" },
    ],
  },

  clave: {
    title: "Editar empresa (Clave Tributaria)",
    subtitle: "Gestión de atributos base e importancia operativa.",
    hint:
      "<b>Recomendación operativa:</b> Mantener trazabilidad por cambios (quién, cuándo, qué) y parametrizar " +
      "períodos (YYYY-MM) para ejecución F29.",
    fields: [
      { key: "unit", label: "Unidad", type: "text", disabled: true },
      { key: "name", label: "Empresa", type: "text", placeholder: "Nombre empresa" },
      { key: "rut", label: "RUT", type: "text", placeholder: "76.123.456-7" },
      { key: "period", label: "Periodo (YYYY-MM)", type: "text", placeholder: "2026-01" },
      {
        key: "status",
        label: "Importancia",
        type: "select",
        options: [
          { value: "alta", label: "Alta" },
          { value: "media", label: "Media" },
          { value: "baja", label: "Baja" }
        ],
      },
    ],
  },
};

export function openEditModal({ unit, id }) {
  if (unit === "siiai") {
    const c = store.siiaiClientes.find(x => x.id === id);
    if (!c) return;

    openModal({
      title: schemas.siiai.title,
      subtitle: schemas.siiai.subtitle,
      schema: schemas.siiai,
      initialValues: {
        unit: "SII-AI",
        name: c.name,
        rut: c.rut,
        password: c.password,
        plan: c.plan,
        start: c.start,
        end: c.end,
        addCompanies: "",
        addMonths: "",
      },
      onSave: (values) => {
        updateSiiaiClient(id, {
          name: values.name?.trim(),
          rut: values.rut?.trim(),
          password: values.password ?? "",
          plan: values.plan,
          start: values.start,
          end: values.end,
        });

        const addCompanies = parseInt(values.addCompanies || 0, 10);
        const addMonths = parseInt(values.addMonths || 0, 10);
        if (addCompanies > 0 || addMonths > 0) {
          applySiiaiUpgrade(id, { addCompanies, addMonths });
        }

        window.ADM.refresh();
      },
      onDelete: () => {
        deleteSiiaiClient(id);
        window.ADM.refresh();
      },
    });

    return;
  }

  if (unit === "clave") {
    const e = store.claveEmpresas.find(x => x.id === id);
    if (!e) return;

    openModal({
      title: schemas.clave.title,
      subtitle: schemas.clave.subtitle,
      schema: schemas.clave,
      initialValues: {
        unit: "Clave Tributaria",
        name: e.name,
        rut: e.rut,
        period: e.period,
        status: e.status,
      },
      onSave: (values) => {
        updateClaveEmpresa(id, {
          name: values.name?.trim(),
          rut: values.rut?.trim(),
          period: values.period?.trim(),
          status: values.status,
        });
        window.ADM.refresh();
      },
      onDelete: () => {
        deleteClaveEmpresa(id);
        window.ADM.refresh();
      },
    });

    return;
  }
}
