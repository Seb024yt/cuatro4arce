// app/data/seed.js
export const seed = {
  claveEmpresas: [
    { id:"ct-1", name:"Comercial Andina SpA", rut:"76.123.456-7", period:"2026-01", status:"alta" },
    { id:"ct-2", name:"Servicios Delta Ltda.", rut:"77.987.654-3", period:"2026-01", status:"media" },
    { id:"ct-3", name:"Inversiones Sur SpA", rut:"78.111.222-5", period:"2026-01", status:"alta" },
    { id:"ct-4", name:"Transportes Norte EIRL", rut:"76.333.444-9", period:"2026-01", status:"baja" },
  ],

  siiaiClientes: [
    { id:"ai-1", name:"Panadería El Trigo", rut:"12.345.678-9", password:"clave123", plan:"Starter", start:"2026-01-05", end:"2026-04-05", maxCompanies:1 },
    { id:"ai-2", name:"Constructora Horizonte", rut:"76.555.666-1", password:"SII_2026!", plan:"Pro", start:"2026-01-10", end:"2026-02-03", maxCompanies:3 },
    { id:"ai-3", name:"Market Sur", rut:"77.000.111-9", password:"", plan:"Enterprise", start:"2026-01-12", end:"2025-12-30", maxCompanies:10 },
  ],

  activity: [
    { date:"2026-01-26 10:12", unit:"Clave Tributaria", action:"Generación F29 lote (2 empresas)", result:"OK" },
    { date:"2026-01-26 11:40", unit:"SII-AI", action:"Upgrade plan (Constructora Horizonte) +2 empresas", result:"OK" },
    { date:"2026-01-26 13:05", unit:"SII-AI", action:"Cliente por vencer (Panadería El Trigo)", result:"ALERTA" },
  ]
};
