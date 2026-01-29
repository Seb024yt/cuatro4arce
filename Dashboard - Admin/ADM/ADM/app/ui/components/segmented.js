// app/ui/components/segmented.js
/**
 * Segmented control simple.
 * items: [{ key, label }]
 * activeKey: string
 * onChange: (key) => void
 */
export function segmented({ items = [], activeKey, onChange }) {
  const wrap = document.createElement("div");
  wrap.style.display = "inline-flex";
  wrap.style.gap = "8px";
  wrap.style.padding = "6px";
  wrap.style.borderRadius = "999px";
  wrap.style.border = "1px solid rgba(255,255,255,.10)";
  wrap.style.background = "rgba(0,0,0,.18)";

  items.forEach(it => {
    const b = document.createElement("button");
    b.className = "btn";
    b.style.borderRadius = "999px";
    b.textContent = it.label;
    if (it.key === activeKey) b.classList.add("primary");
    b.addEventListener("click", () => {
      if (typeof onChange === "function") onChange(it.key);
    });
    wrap.appendChild(b);
  });

  return wrap;
}
