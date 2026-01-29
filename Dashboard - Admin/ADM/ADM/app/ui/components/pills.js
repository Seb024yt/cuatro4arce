// app/ui/components/pills.js
export function statusPill(label, kind = "good") {
  const dotClass =
    kind === "good" ? "dot good" :
    kind === "warn" ? "dot warn" : "dot bad";

  const pill = document.createElement("span");
  pill.className = "pill";
  pill.innerHTML = `<span class="${dotClass}"></span>${label}`;
  return pill;
}
