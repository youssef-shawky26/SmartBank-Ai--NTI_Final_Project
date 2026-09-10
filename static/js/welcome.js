// Animate "Welcome" left to right, one letter at a time, then reveal the
// subtitle and the login card in sequence.
(function animateWelcome() {
  const word = "Welcome";
  const letterDelay = 0.09;   // seconds between each letter starting
  const letterDuration = 0.5; // seconds each letter takes to fade+rise in

  const el = document.getElementById("welcome-word");
  el.setAttribute("aria-label", word);
  [...word].forEach((ch, i) => {
    const span = document.createElement("span");
    span.textContent = ch;
    span.style.animationDelay = `${i * letterDelay}s`;
    el.appendChild(span);
  });

  const wordFinishedAt = (word.length - 1) * letterDelay + letterDuration;

  const sub = document.querySelector(".welcome-sub");
  sub.style.animationDelay = `${wordFinishedAt + 0.15}s`;

  const card = document.querySelector(".auth-card");
  card.style.animationDelay = `${wordFinishedAt + 0.55}s`;
})();

let selectedRole = "client";

document.querySelectorAll(".role-switch button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".role-switch button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    selectedRole = btn.dataset.role;
    document.querySelector(".manager-only").style.display = selectedRole === "manager" ? "block" : "none";
    document.querySelectorAll(".client-only").forEach(el => {
      el.style.display = selectedRole === "manager" ? "none" : "grid";
    });
  });
});

document.querySelectorAll(".auth-tabs button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".auth-tabs button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    document.getElementById("login-form").style.display = tab === "login" ? "block" : "none";
    document.getElementById("signup-form").style.display = tab === "signup" ? "block" : "none";
    hideError();
  });
});

function hideError() { document.getElementById("auth-error").style.display = "none"; }
function showError(msg) {
  const el = document.getElementById("auth-error");
  el.textContent = msg;
  el.style.display = "block";
}

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();
  const fd = new FormData(e.target);
  try {
    const { user } = await api.post("/api/auth/login", {
      username: fd.get("username"), password: fd.get("password"), role: selectedRole,
    });
    window.location.href = user.role === "manager" ? "/manager" : "/app";
  } catch (err) { showError(err.message); }
});

document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  payload.role = selectedRole;
  try {
    const { user } = await api.post("/api/auth/register", payload);
    window.location.href = user.role === "manager" ? "/manager" : "/app";
  } catch (err) { showError(err.message); }
});
