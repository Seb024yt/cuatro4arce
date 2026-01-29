// app/ui/layout/leftNav.js
export function renderLeftNav(mount, activeView = "vision-general"){
  const isActive = (view) => activeView === view ? "active" : "";

  mount.innerHTML = `
    <div class="brand">
      <div class="logo" aria-hidden="true"></div>
      <div>
        <h1>Consola Administrativa</h1>
        <p>Gestión operativa • Clave Tributaria & SII-AI</p>
      </div>
    </div>

    <div class="nav">
      <div class="sectionTitle">Módulos</div>

      <button class="${isActive("vision-general")}" onclick="ADM.navigate('vision-general')">
        <span>Visión General</span>
        <span class="meta">KPIs</span>
      </button>

      <button class="${isActive("clave-tributaria")}" onclick="ADM.navigate('clave-tributaria')">
        <span>Clave Tributaria</span>
        <span class="meta">F29 masivo</span>
      </button>

      <button class="${isActive("sii-ai")}" onclick="ADM.navigate('sii-ai')">
        <span>SII-AI</span>
        <span class="meta">Clientes & planes</span>
      </button>

      <div class="sectionTitle">Operación</div>

      <button class="${isActive("auditoria")}" onclick="ADM.navigate('auditoria')">
        <span>Auditoría</span>
        <span class="meta">Logs</span>
      </button>

      <button class="${isActive("configuracion")}" onclick="ADM.navigate('configuracion')">
        <span>Configuración</span>
        <span class="meta">Seguridad</span>
      </button>
    </div>

    <div class="card" style="margin-top:auto;">
      <h3>Estado del sistema</h3>
      <div class="pill"><span class="dot good"></span>Servicios activos <span class="muted">• OK</span></div>
      <div style="height:10px"></div>
      <div class="hintBox">
        Recomendación de gobierno: mantener control de accesos (roles), rotación de credenciales y trazabilidad
        por operación (generación F29 / cambios de plan).
      </div>
    </div>
  `;
}
