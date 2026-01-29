/* state.js */
export const state = {
  view: "vision-general",    // ruta inicial
  unit: "clave",             // unidad activa (right panel)
  filters: {
    claveQuery: "",
    claveStatus: "all",
    siiaiQuery: "",
    siiaiStatus: "all",
  },
  modal: { open:false, unit:null, id:null }
};
