// app/ui/components/toast.js
let container = null;

function ensureContainer() {
  if (container) return;
  container = document.createElement("div");
  container.style.position = "fixed";
  container.style.right = "18px";
  container.style.bottom = "18px";
  container.style.zIndex = "9999";
  container.style.display = "flex";
  container.style.flexDirection = "column";
  container.style.gap = "10px";
  document.body.appendChild(container);
}

export function toast(message, kind = "info") {
  ensureContainer();

  const el = document.createElement("div");
  el.className = "card";
  el.style.minWidth = "280px";
  el.style.maxWidth = "420px";
  el.style.display = "flex";
  el.style.alignItems = "flex-start";
  el.style.gap = "10px";
  el.style.padding = "12px";

  const dot = document.createElement("span");
  dot.className = "dot " + (kind === "ok" ? "good" : kind === "warn" ? "warn" : kind === "bad" ? "bad" : "");
  dot.style.marginTop = "6px";

  const txt = document.createElement("div");
  txt.innerHTML = `<div style="font-weight:900; font-size:13px;">${kind.toUpperCase()}</div>
                   <div class="muted" style="margin-top:4px; font-size:12px; line-height:1.35;">${message}</div>`;

  el.appendChild(dot);
  el.appendChild(txt);
  container.appendChild(el);

  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(6px)";
    el.style.transition = "all .25s ease";
    setTimeout(() => el.remove(), 260);
  }, 2800);
}
