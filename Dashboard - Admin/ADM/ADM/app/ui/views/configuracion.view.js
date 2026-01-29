// app/ui/views/configuracion.view.js
export function renderConfiguracion() {
  const section = document.createElement("section");
  section.id = "view-config";
  section.style.display = "block";

  section.innerHTML = `
    <div class="card">
      <h3>Configuración</h3>
      <div class="hintBox">
        Recomendado: RBAC (roles), 2FA, rotación de claves, cifrado de secretos en servidor, y bitácora inmutable de cambios de planes.
        <br/><br/>
        Para SII-AI: no persistir contraseñas en texto plano; utilice vault/secret manager y control de acceso por perfil.
      </div>
    </div>
  `;

  return section;
}
