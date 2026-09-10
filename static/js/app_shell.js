const shell = {
  sections: {},
  activeSection: null,

  init(defaultSection) {
    document.querySelectorAll(".glass-nav-link[data-section]").forEach(btn => {
      btn.addEventListener("click", () => {
        this.showSection(btn.dataset.section);
      });
    });

    initThemeToggle(document.getElementById("theme-toggle"));

    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", async () => {
        await api.post("/api/auth/logout");
        window.location.href = "/";
      });
    }

    this.showSection(defaultSection);

    api.get("/api/auth/me").then(({ user }) => {
      const avatarEl = document.getElementById("avatar");
      if (avatarEl) {
        avatarEl.textContent = initials(user.full_name);
      }
    }).catch(() => { window.location.href = "/"; });
  },

  onSection(name, loader) {
    this.sections[name] = { loader, loaded: false };
  },

  showSection(name) {
    document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
    document.querySelectorAll(".glass-nav-link[data-section]").forEach(b => b.classList.toggle("active", b.dataset.section === name));
    const target = document.getElementById(`section-${name}`);
    if (target) target.classList.add("active");
    this.activeSection = name;
    const entry = this.sections[name];
    if (entry && !entry.loaded) {
      entry.loaded = true;
      entry.loader();
    }
  },

  reload(name) {
    const entry = this.sections[name];
    if (entry) entry.loader();
  },

  setBadge(section, count) {
    document.querySelectorAll(`#badge-${section}`).forEach(el => {
      if (count > 0) {
        el.textContent = count > 99 ? "99+" : String(count);
        el.style.display = "inline-flex";
      } else {
        el.style.display = "none";
      }
    });
  },
};