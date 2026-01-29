/* utils.js */
export function maskPassword(p){
  if(!p) return "—";
  return "•".repeat(Math.min(10, p.length));
}
