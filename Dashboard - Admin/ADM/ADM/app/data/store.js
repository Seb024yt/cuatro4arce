// app/data/store.js
import { seed } from "./seed.js";

export const store = {
  claveEmpresas: structuredClone(seed.claveEmpresas),
  siiaiClientes: structuredClone(seed.siiaiClientes),
  activity: structuredClone(seed.activity),
};
