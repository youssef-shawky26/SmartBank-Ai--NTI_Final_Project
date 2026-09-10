// Small fetch wrapper so every page talks to the Flask API the same way.
const api = {
  async _call(method, url, body) {
    const opts = { method, headers: {}, credentials: "same-origin" };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) {
      const message = (data && data.error) || `Request failed (${res.status})`;
      throw new Error(message);
    }
    return data;
  },
  get(url) { return this._call("GET", url); },
  post(url, body) { return this._call("POST", url, body); },
  put(url, body) { return this._call("PUT", url, body); },
};

function showToast(message, isError = false) {
  let el = document.getElementById("global-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "global-toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 3600);
}

function initThemeToggle(toggleEl) {
  if (!toggleEl) return;
  const apply = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("verdict-theme", theme);
    window.dispatchEvent(new CustomEvent("verdict-theme-change", { detail: { theme } }));
  };
  toggleEl.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    apply(current === "light" ? "dark" : "light");
  });
}

// Theme-aware colors for Chart.js — call fresh each render so charts stay
// legible after a theme switch (line color, grid lines, and axis/legend
// text all need to change between light and dark).
function chartColors() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const style = getComputedStyle(document.documentElement);
  return {
    line: isDark ? "#9FB4E3" : (style.getPropertyValue("--navy").trim() || "#111844"),
    fill: isDark ? "rgba(159,180,227,0.16)" : "rgba(75,86,148,0.12)",
    grid: isDark ? "rgba(234,224,207,0.08)" : "rgba(17,24,68,0.06)",
    text: (style.getPropertyValue("--text-muted").trim()) || (isDark ? "#9199C4" : "#6b7290"),
    segmentA: isDark ? "#9FB4E3" : "#7288AE",
    segmentB: isDark ? "#E3B15E" : "#B9862F",
  };
}

function initials(name) {
  if (!name) return "?";
  return name.split(" ").filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join("");
}

function money(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n || 0);
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso + "Z");
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
