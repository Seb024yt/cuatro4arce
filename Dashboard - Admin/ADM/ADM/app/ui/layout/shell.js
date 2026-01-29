/* shell.js */
import { $ } from "../../core/dom.js";
import { state } from "../../core/state.js";
import { routes } from "../../core/routes.js";
import { renderLeftNav } from "./leftNav.js";
import { renderTopbar } from "./topbar.js";
import { renderRightPanel } from "./rightPanel.js";

export function mountShell(){
  // Initial mount
  render();

  function render(){
    // Keep side panels in sync with state
    renderLeftNav($("#leftNav"), state.view);
    renderRightPanel($("#rightPanel"));

    const main = $("#main");
    main.innerHTML = "";
    main.appendChild(renderTopbar());

    const viewFn = routes[state.view] || routes["vision-general"];
    main.appendChild(viewFn());
  }

  // Exponer un hook global para navegar (simple y directo)
  window.ADM = window.ADM || {};
  window.ADM.navigate = (view) => { state.view = view; render(); };
  window.ADM.refresh = () => render();
}
