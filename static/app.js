/* ==========================================================================
   MovStok ERP - Corporate SaaS Architecture
   Core: Application Controller, State & Service Registry
   ========================================================================== */

const MovStok = {
  version: "2.0.0",
  
  state: {
    isBooted: false,
    currentPage: "dashboard",
    user: null,
    permissions: new Set(),
    cache: {
      categories: [],
      suppliers: [],
      products: [],
      employees: [],
      roles: [],
      permissions: [],
      locations: [],
    },
    charts: {},
    security: {
      csrfToken: null,
    },
  },

  // Camada de Serviços: Abstração de I/O
  Services: {
    request: (path, options) => api(path, options),

    Products: {
      list: (params) => api(`/api/products${buildQuery(params)}`),
      save: (data, id = null) => MovStok.Services.request(id ? `/api/products/${id}` : "/api/products", {
        method: id ? "PUT" : "POST",
        body: data
      }),
    },
    Stock: {
      entry: (data) => MovStok.Services.request("/api/entries", { method: "POST", body: data }),
      output: (data) => MovStok.Services.request("/api/outputs", { method: "POST", body: data }),
    },
    Auth: {
      async check() {
        const session = await MovStok.Services.request("/api/auth/me");
        if (session.authenticated) {
          MovStok.state.user = session.user;
          MovStok.state.permissions = new Set(session.permissions || []);
          return true;
        }
        return false;
      },
      logout: async () => {
        await MovStok.Services.request("/api/auth/logout", { method: "POST" });
        location.reload();
      }
    }
  },

  // Engine de UI: Componentização e Helpers visuais
  UI: {
    setLoading(title = "Processando") {
      $("#page-wrap").innerHTML = `
        <div class="panel">
          <div class="panel-body text-center" style="padding: 60px 20px">
            <i class="fa-solid fa-circle-notch fa-spin fa-2x text-primary" style="margin-bottom:15px"></i>
            <p class="text-muted">${escapeHtml(title)}...</p>
          </div>
        </div>`;
    },
    
    toast(title, message, type = "success") {
      const root = $("#toast-root");
      const node = document.createElement("div");
      node.className = `toast ${type}`;
      node.innerHTML = `
        <i class="fa-solid ${type === 'danger' ? 'fa-circle-xmark' : 'fa-circle-check'}"></i>
        <div><strong>${escapeHtml(title)}</strong>${message ? `<small>${escapeHtml(message)}</small>` : ""}</div>`;
      root.appendChild(node);
      setTimeout(() => node.remove(), 4000);
    }
  }
};

const Pages = {
  dashboard: "Painel",
  entradas: "Entradas",
  saidas: "Saídas",
  estoque: "Estoque",
  produtos: "Produtos",
  categorias: "Categorias",
  fornecedores: "Fornecedores",
  funcionarios: "Funcionários",
  matriculas: "Matrículas",
  relatorios: "Relatórios",
  financeiro: "Financeiro",
  atividades: "Atividades",
  usuarios: "Usuários",
  configuracoes: "Configurações",
  administracao: "Administração",
};

const Icons = {
  dashboard: "fa-gauge-high",
  entradas: "fa-truck-ramp-box",
  saidas: "fa-dolly",
  estoque: "fa-boxes-stacked",
  produtos: "fa-barcode",
  categorias: "fa-layer-group",
  fornecedores: "fa-handshake",
  funcionarios: "fa-id-badge",
  matriculas: "fa-id-card",
  relatorios: "fa-chart-column",
  financeiro: "fa-coins",
  atividades: "fa-clipboard-list",
  usuarios: "fa-user-shield",
  configuracoes: "fa-gear",
  administracao: "fa-screwdriver-wrench",
};

const PagePermissions = {
  dashboard: "dashboard.view",
  produtos: "products.view",
  categorias: "categories.view",
  fornecedores: "suppliers.view",
  entradas: "stock.entry",
  saidas: "stock.output",
  estoque: "stock.view",
  funcionarios: "employees.view",
  matriculas: "employees.view",
  relatorios: "reports.view",
  financeiro: "finance.view",
  atividades: "admin.system",
  usuarios: "users.manage",
  configuracoes: "settings.view",
  administracao: "admin.system",
};

const Money = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const NumberBR = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 3,
});

const DateTimeBR = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

const DateBR = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
});

function $(selector, root = document) {
  return root.querySelector(selector);
}

function $all(selector, root = document) {
  return [...root.querySelectorAll(selector)];
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fmtMoney(value) {
  return Money.format(Number(value || 0));
}

function fmtQty(value) {
  return NumberBR.format(Number(value || 0));
}

function fmtDate(value, withTime = true) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return withTime ? DateTimeBR.format(date) : DateBR.format(date);
}

function animateValue(id, start, end, duration) {
  const obj = typeof id === "string" ? document.getElementById(id) : id;
  if (!obj) return;
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    const current = Math.floor(progress * (end - start) + start);
    obj.innerHTML = typeof end === "number" && end % 1 !== 0 ? fmtQty(current) : current;
    if (progress < 1) {
      window.requestAnimationFrame(step);
    }
  };
  window.requestAnimationFrame(step);
}

function initials(name) {
  return String(name || "U")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function hasPermission(code) {
  return MovStok.state.permissions.has(code) || ["admin", "super_admin"].includes(MovStok.state.user?.role?.name);
}

function canAccessPage(page) {
  const permission = PagePermissions[page];
  return !permission || hasPermission(permission);
}

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

function isUnsafeRequest(method = "GET") {
  return ["POST", "PUT", "PATCH", "DELETE"].includes(String(method || "GET").toUpperCase());
}

async function getCsrfToken() {
  if (MovStok.state.security.csrfToken) {
    return MovStok.state.security.csrfToken;
  }

  const response = await fetch("/api/auth/csrf", {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.csrf_token) {
    throw new Error("Não foi possível validar a segurança da sessão.");
  }
  MovStok.state.security.csrfToken = payload.csrf_token;
  return payload.csrf_token;
}

async function api(path, options = {}) {
  // Centralização de segurança e headers ERP
  const headers = {
    Accept: "application/json",
    "X-Requested-With": "XMLHttpRequest",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  };

  if (isUnsafeRequest(options.method)) {
    headers["X-CSRF-Token"] = await getCsrfToken();
  }

  const config = {
    credentials: "same-origin",
    headers,
    ...options,
  };

  if (options.body && typeof options.body !== "string") {
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, config);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    if (response.status === 401) {
      showAuth();
    }
    if (response.status === 419) {
      MovStok.state.security.csrfToken = null;
    }
    const message = typeof payload === "string"
      ? payload
      : payload.error || "Não foi possível concluir a operação.";
    throw new Error(message);
  }

  return payload;
}

function pageWrap() {
  return $("#page-wrap");
}

function setLoading(title = "Carregando dados") {
  pageWrap().innerHTML = `
    <div class="panel">
      <div class="panel-body">
        <div class="skeleton" style="height:18px;width:180px;margin-bottom:14px"></div>
        <div class="skeleton" style="height:12px;width:70%;margin-bottom:10px"></div>
        <div class="skeleton" style="height:12px;width:45%"></div>
        <span class="text-muted" style="display:block;margin-top:16px">${escapeHtml(title)}...</span>
      </div>
    </div>
  `;
}

function pageHeader(page, subtitle, actions = "") {
  return `
    <div class="page-head">
      <div>
        <h1><i class="fa-solid ${Icons[page] || "fa-table"}"></i> ${Pages[page] || page}</h1>
        <div class="subtitle">${escapeHtml(subtitle)}</div>
      </div>
      <div class="page-actions">${actions}</div>
    </div>
  `;
}

function forbiddenPage(page) {
  return `
    ${pageHeader(page, "Seu perfil atual nao permite acessar esta area.")}
    <div class="panel">
      <div class="panel-body">
        ${emptyState("fa-lock", "Acesso restrito", "Solicite a um Super Admin ou administrador a permissao necessaria.")}
      </div>
    </div>
  `;
}

function emptyState(icon, title, description) {
  return `
    <div class="empty-state">
      <div class="empty-illustration"><i class="fa-solid ${icon}"></i></div>
      <h4>${escapeHtml(title)}</h4>
      <p>${escapeHtml(description)}</p>
    </div>
  `;
}

function statusBadge(status, map) {
  const cfg = map[status] || map.default || { label: status || "-", cls: "neutral" };
  return `<span class="badge ${cfg.cls}">${escapeHtml(cfg.label)}</span>`;
}

function stockBadge(product) {
  const status = product.stock_status;
  return statusBadge(status, {
    ok: { label: "OK", cls: "success" },
    low: { label: "Baixo", cls: "warning" },
    out: { label: "Zerado", cls: "danger" },
  });
}

function activeBadge(active) {
  return statusBadge(active ? "active" : "inactive", {
    active: { label: "Ativo", cls: "success" },
    inactive: { label: "Inativo", cls: "neutral" },
  });
}

function userStatusBadge(status) {
  return statusBadge(status, {
    active: { label: "Ativo", cls: "success" },
    inactive: { label: "Inativo", cls: "neutral" },
    blocked: { label: "Bloqueado", cls: "danger" },
    leave: { label: "Afastado", cls: "warning" },
    terminated: { label: "Desligado", cls: "danger" },
    default: { label: status || "-", cls: "neutral" },
  });
}

function movementStatusBadge(status) {
  return statusBadge(status, {
    confirmed: { label: "Confirmado", cls: "success" },
    cancelled: { label: "Cancelado", cls: "danger" },
    default: { label: status || "-", cls: "neutral" },
  });
}

function reasonLabel(reason) {
  return ({
    sale: "Venda",
    consumption: "Consumo",
    loss: "Perda",
    transfer: "Transferência",
  })[reason] || reason || "-";
}

function roleLabel(role) {
  return role?.label || role?.name || "-";
}

function table(headers, rows, emptyHtml) {
  return `
    <div class="table-wrap">
      ${tableBody(headers, rows, emptyHtml)}
    </div>
  `;
}

function tableBody(headers, rows, emptyHtml) {
  if (!rows.length) {
    return emptyHtml;
  }

  return `
    <table class="data-table">
      <thead>
        <tr>${headers.map((h) => `<th class="${h.cls || ""}">${h.label}</th>`).join("")}</tr>
      </thead>
      <tbody>${rows.join("")}</tbody>
    </table>
  `;
}

function toolbar({ id, placeholder = "Buscar", filters = "", extra = "" }) {
  return `
    <div class="toolbar">
      <div class="search">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input id="${id}-search" type="text" placeholder="${escapeHtml(placeholder)}"/>
      </div>
      ${filters}
      ${extra}
    </div>
  `;
}

function pagination(meta, onClickName) {
  if (!meta || meta.pages <= 1) return "";
  const pages = [];
  const start = Math.max(1, meta.page - 2);
  const end = Math.min(meta.pages, meta.page + 2);

  pages.push(`<button ${meta.has_prev ? "" : "disabled"} data-page-target="${meta.page - 1}">Anterior</button>`);
  for (let page = start; page <= end; page += 1) {
    pages.push(`<button class="${page === meta.page ? "active" : ""}" data-page-target="${page}">${page}</button>`);
  }
  pages.push(`<button ${meta.has_next ? "" : "disabled"} data-page-target="${meta.page + 1}">Próxima</button>`);

  return `
    <div class="pagination" data-pagination="${onClickName}">
      <span>${meta.total} registros · página ${meta.page} de ${meta.pages}</span>
      <div class="pages">${pages.join("")}</div>
    </div>
  `;
}

function bindPagination(name, callback) {
  const root = $(`[data-pagination="${name}"]`);
  if (!root) return;
  root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page-target]");
    if (!button || button.disabled) return;
    callback(Number(button.dataset.pageTarget));
  });
}

function toast(title, message = "", type = "success") {
  const root = $("#toast-root");
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  const icon = type === "danger" ? "fa-circle-exclamation"
    : type === "warning" ? "fa-triangle-exclamation"
      : "fa-circle-check";
  node.innerHTML = `
    <i class="fa-solid ${icon}"></i>
    <div>
      <strong>${escapeHtml(title)}</strong>
      ${message ? `<small>${escapeHtml(message)}</small>` : ""}
    </div>
  `;
  root.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

function openModal({ title, body, footer = "", size = "" }) {
  const root = $("#modal-root");
  root.innerHTML = `
    <div class="modal ${size}">
      <div class="modal-head">
        <h3>${escapeHtml(title)}</h3>
        <button type="button" data-modal-close>&times;</button>
      </div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ""}
    </div>
  `;
  root.classList.add("show");
  $all("[data-modal-close]", root).forEach((button) => {
    button.addEventListener("click", closeModal);
  });
  root.addEventListener("click", closeModalOnBackdrop);
}

function closeModalOnBackdrop(event) {
  if (event.target.id === "modal-root") closeModal();
}

function closeModal() {
  const root = $("#modal-root");
  root.classList.remove("show");
  root.removeEventListener("click", closeModalOnBackdrop);
  root.innerHTML = "";
}

function getFormData(form) {
  const data = {};
  new FormData(form).forEach((value, key) => {
    data[key] = typeof value === "string" ? value.trim() : value;
  });
  return data;
}

function optionList(items, selected, label = "name") {
  return items.map((item) => `
    <option value="${item.id}" ${Number(selected) === Number(item.id) ? "selected" : ""}>
      ${escapeHtml(item[label])}
    </option>
  `).join("");
}

async function confirmAction(title, message, actionLabel, action) {
  openModal({
    title,
    body: `<p class="text-muted">${escapeHtml(message)}</p>`,
    footer: `
      <button type="button" class="btn ghost" data-modal-close>Cancelar</button>
      <button type="button" class="btn danger" id="confirm-action">${escapeHtml(actionLabel)}</button>
    `,
  });
  $("#confirm-action").addEventListener("click", async () => {
    try {
      await action();
      closeModal();
    } catch (error) {
      toast("Operação não concluída", error.message, "danger");
    }
  });
}

async function loadLookupData(types = ["categories", "suppliers", "products", "employees", "locations"]) {
  const tasks = [];
  if (types.includes("categories")) {
    tasks.push(api("/api/categories").then((data) => { MovStok.state.cache.categories = data.items || []; }));
  }
  if (types.includes("suppliers")) {
    tasks.push(api("/api/suppliers?paginated=0").then((data) => { MovStok.state.cache.suppliers = data.items || []; }));
  }
  if (types.includes("products")) {
    tasks.push(api("/api/products?per_page=200").then((data) => { MovStok.state.cache.products = data.items || []; }));
  }
  if (types.includes("employees")) {
    tasks.push(api("/api/employees?paginated=0").then((data) => { MovStok.state.cache.employees = data.items || []; }));
  }
  if (types.includes("roles")) {
    tasks.push(api("/api/roles").then((data) => { MovStok.state.cache.roles = data.items || []; }));
  }
  if (types.includes("permissions")) {
    tasks.push(api("/api/permissions").then((data) => { MovStok.state.cache.permissions = data.items || []; }));
  }
  if (types.includes("locations")) {
    tasks.push(api("/api/locations").then((data) => { MovStok.state.cache.locations = data.items || []; }));
  }
  await Promise.all(tasks);
}

function destroyCharts() {
  Object.values(MovStok.state.charts).forEach((chart) => chart?.destroy?.());
  MovStok.state.charts = {};
}

function renderLineChart(canvasId, labels, entries, outputs) {
  if (!window.Chart) return;
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  MovStok.state.charts[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Entradas",
          data: entries,
          borderColor: "#15803d",
          backgroundColor: "rgba(21,128,61,0.08)",
          tension: 0.42,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
          fill: true,
        },
        {
          label: "Saídas",
          data: outputs,
          borderColor: "#dc2626",
          backgroundColor: "rgba(220,38,38,0.08)",
          tension: 0.42,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true, padding: 18 } },
        tooltip: {
          backgroundColor: "#111827",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
          padding: 12,
          titleFont: { weight: "700" },
          bodyFont: { weight: "500" },
          displayColors: true,
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#6b7280" } },
        y: { beginAtZero: true, grid: { color: "rgba(148,163,184,0.18)" }, ticks: { color: "#6b7280" } },
      },
    },
  });
}

function renderBarChart(canvasId, labels, data) {
  if (!window.Chart) return;
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  MovStok.state.charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Produtos",
        data,
        backgroundColor: "#1d4ed8",
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#111827",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
          padding: 12,
          titleFont: { weight: "700" },
          bodyFont: { weight: "500" },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#6b7280" } },
        y: { beginAtZero: true, grid: { color: "rgba(148,163,184,0.18)" }, ticks: { precision: 0, color: "#6b7280" } },
      },
    },
  });
}

// ===================================================
// AUTH VISUAL EFFECTS (PREMIUM SAAS)
// ===================================================

function showAuth() {
  const authEl = document.getElementById("auth");
  if (authEl) {
    authEl.style.display = "flex"; // Necessário para o layout Premium
    authEl.classList.add("fade-in");
  }
  document.getElementById("app-shell")?.classList.remove("show");
  MovStok.state.user = null;
  MovStok.state.permissions = new Set();
  if (window.location.pathname !== "/login") {
    history.replaceState({}, "", "/login");
  }
}

function showApp() {
  $("#auth").style.display = "none";
  $("#app-shell").classList.add("show");
}

function updateUserBox() {
  $("#user-name").textContent = MovStok.state.user?.name || "Usuário";
  $("#user-role").textContent = roleLabel(MovStok.state.user?.role);
  $("#user-avatar").textContent = initials(MovStok.state.user?.name);
}

function enforceMenuPermissions() {
  $all(".menu-item").forEach((item) => {
    const allowed = canAccessPage(item.dataset.page);
    item.hidden = !allowed;
    item.setAttribute("aria-hidden", allowed ? "false" : "true");
  });
}

async function checkSession() {
  const session = await api("/api/auth/me");
  if (!session.authenticated) {
    showAuth();
    return false;
  }
  MovStok.state.user = session.user;
  MovStok.state.permissions = new Set(session.permissions || []);
  updateUserBox();
  enforceMenuPermissions();
  showApp();
  return true;
}

function pageFromPath() {
  const path = location.pathname.replace(/\/+$/, "");
  if (path === "/app" || path === "") return "dashboard";
  const match = path.match(/^\/app\/([^/]+)/);
  return match && Pages[match[1]] ? match[1] : "dashboard";
}

function updateNavigation(page) {
  MovStok.state.currentPage = page;
  $("#bc-current").textContent = Pages[page] || page;
  $all(".menu-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.page === page);
  });
}

function navigate(page, replace = false) {
  if (!Pages[page]) page = "dashboard";
  const path = page === "dashboard" ? "/app" : `/app/${page}`;
  if (replace) {
    history.replaceState({ page }, "", path);
  } else if (location.pathname !== path) {
    history.pushState({ page }, "", path);
  }
  renderPage(page);
}

const PageRenderers = {
  dashboard: renderDashboard,
  produtos: renderProducts,
  estoque: renderStock,
  entradas: renderEntries,
  saidas: renderOutputs,
  categorias: renderCategories,
  fornecedores: renderSuppliers,
  funcionarios: renderEmployees,
  matriculas: renderEnrollments,
  relatorios: renderReports,
  financeiro: renderFinance,
  atividades: renderActivities,
  usuarios: renderUsers,
  configuracoes: renderSettings,
  administracao: renderAdministration,
};

async function renderPage(page = pageFromPath()) {
  destroyCharts();
  if (!canAccessPage(page)) {
    updateNavigation(page);
    pageWrap().innerHTML = forbiddenPage(page);
    return;
  }
  updateNavigation(page);
  setLoading(Pages[page]);

  try {
    const renderer = PageRenderers[page] || renderDashboard;
    await renderer();
    loadNotifications();
  } catch (error) {
    pageWrap().innerHTML = `
      ${pageHeader(page, "Não foi possível carregar esta tela.")}
      <div class="panel">
        <div class="panel-body">
          ${emptyState("fa-triangle-exclamation", "Erro ao carregar", error.message)}
        </div>
      </div>
    `;
  }
}

async function renderDashboard() {
  const data = await api("/api/dashboard");
  const kpi = data.kpi || {};

  // Saudação Dinâmica baseada no horário local
  const hour = new Date().getHours();
  let greeting = "Boa noite 🌙";
  if (hour >= 5 && hour < 12) greeting = "Bom dia 👋";
  else if (hour >= 12 && hour < 18) greeting = "Boa tarde ☀️";

  // Formatação de data completa para o cabeçalho
  const todayFull = new Intl.DateTimeFormat('pt-BR', { 
    dateStyle: 'full' 
  }).format(new Date());

  // KPIs consolidados com IDs para animação
  pageWrap().innerHTML = `
    <div class="greeting-box">
      <h2>${greeting}, ${escapeHtml(MovStok.state.user?.name.split(' ')[0])}</h2>
      <p>Hoje é ${escapeHtml(todayFull)}</p>
    </div>

    <div class="kpi-grid">
      ${kpiCard("Produtos", kpi.total_products, "Itens no catálogo", "fa-barcode", "", "kpi-products")}
      ${kpiCard("Estoque Total", kpi.total_units, "Unidades em posse", "fa-boxes-stacked", "green", "kpi-units")}
      ${kpiCard("Valor Contábil", fmtMoney(kpi.inventory_value), "Patrimônio atual", "fa-wallet", "cyan", "kpi-value")}
      ${kpiCard("Alertas", (Number(kpi.low_stock) + Number(kpi.out_stock)), "Ações necessárias", "fa-triangle-exclamation", "amber", "kpi-alerts")}
      ${kpiCard("Entradas (Hoje)", kpi.entries_today, "Recebidas", "fa-arrow-down-long", "green", "kpi-entries")}
      ${kpiCard("Saídas (Hoje)", kpi.outputs_today, "Expedidas", "fa-arrow-up-long", "red", "kpi-outputs")}
    </div>

    <div class="dash-main-grid">
      <section class="panel">
        <div class="panel-head"><h3>Fluxo de Movimentação (14 dias)</h3></div>
        <div class="panel-body">
          <div class="chart-box"><canvas id="movement-chart"></canvas></div>
        </div>
      </section>

      <div class="dash-row">
        <section class="panel">
          <div class="panel-head"><h3>⚠️ Estoque Crítico</h3></div>
          <div class="panel-body" style="padding:0">
            ${renderCriticalStock(data.critical_stock || [])}
          </div>
        </section>

        <section class="panel">
          <div class="panel-head"><h3>📊 Resumo Executivo</h3></div>
          <div class="panel-body">
            <div style="display:flex; flex-direction:column; gap:16px">
              ${summaryItem("Produtos Ativos", kpi.total_products, "fa-tag")}
              ${summaryItem("Categorias", kpi.categories_count, "fa-layer-group")}
              <hr style="border:0; border-top:1px solid var(--border); margin:4px 0">
              ${summaryItem("Entradas no Mês", fmtQty(kpi.entries_month), "fa-arrow-down", "text-success")}
              ${summaryItem("Saídas no Mês", fmtQty(kpi.outputs_month), "fa-arrow-up", "text-danger")}
              ${summaryItem("Valor Total", fmtMoney(kpi.inventory_value), "fa-wallet", "text-primary")}
            </div>
          </div>
        </section>
      </div>

      <section class="panel">
        <div class="panel-head"><h3>Distribuição de Inventário por Categoria</h3></div>
        <div class="panel-body">
          <div class="chart-box sm"><canvas id="category-chart"></canvas></div>
        </div>
      </section>
    </div>
  `;

  // Animação dos contadores
  animateValue("kpi-products", 0, kpi.total_products, 1000);
  animateValue("kpi-units", 0, kpi.total_units, 1000);
  animateValue("kpi-alerts", 0, (Number(kpi.low_stock) + Number(kpi.out_stock)), 1000);
  animateValue("kpi-entries", 0, kpi.entries_today, 1000);
  animateValue("kpi-outputs", 0, kpi.outputs_today, 1000);

  // Gráficos Reais
  const movement = data.chart_movements || [];
  renderLineChart(
    "movement-chart",
    movement.map((item) => fmtDate(item.date, false)),
    movement.map((item) => item.entries),
    movement.map((item) => item.outputs),
  );

  const categories = data.categories_chart || [];
  renderBarChart(
    "category-chart",
    categories.map((item) => item.name),
    categories.map((item) => item.count),
  );

}

function renderCriticalStock(items) {
  if (!items || items.length === 0) {
    return emptyState("fa-check-circle", "Tudo em ordem", "Não há produtos com estoque crítico no momento.");
  }
  return `
    <table class="data-table">
      <thead>
        <tr><th>Item</th><th class="num">Qtd</th><th class="num">Mín</th><th>Status</th></tr>
      </thead>
      <tbody>
        ${items.map(p => `
          <tr>
            <td><strong>${escapeHtml(p.name)}</strong><div class="text-muted mono" style="font-size:11px">${escapeHtml(p.sku)}</div></td>
            <td class="num" style="color:var(--danger); font-weight:700">${fmtQty(p.stock)}</td>
            <td class="num">${fmtQty(p.min)}</td>
            <td><span class="badge ${p.stock <= 0 ? 'danger' : 'warning'}">${p.stock <= 0 ? 'Zerado' : 'Baixo'}</span></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

function kpiCard(label, value, delta, icon, color = "", id = "") {
  return `
    <div class="kpi-card">
      <div>
        <div class="kpi-label">${escapeHtml(label)}</div>
        <div class="kpi-value" id="${id}">${escapeHtml(value ?? 0)}</div>
        <div class="kpi-delta">${escapeHtml(delta)}</div>
      </div>
      <div class="kpi-icon ${color}"><i class="fa-solid ${icon}"></i></div>
    </div>
  `;
}

function summaryItem(label, value, icon, colorClass = "") {
  return `
    <div style="display:flex; justify-content:space-between; align-items:center; padding: 4px 0">
      <div style="display:flex; align-items:center; gap:10px; color:var(--text-2)">
        <i class="fa-solid ${icon} ${colorClass}" style="width:16px; text-align:center"></i>
        <span style="font-size:13px">${escapeHtml(label)}</span>
      </div>
      <strong style="font-size:14px">${escapeHtml(value)}</strong>
    </div>
  `;
}

function dashboardTopProducts(items) {
  if (!items.length) {
    return emptyState("fa-chart-simple", "Nenhuma movimentação encontrada", "Comece cadastrando seus primeiros produtos para visualizar este ranking.");
  }
  return table(
    [
      { label: "SKU" },
      { label: "Produto" },
      { label: "Saídas", cls: "num" },
      { label: "Estoque", cls: "num" },
    ],
    items.map((p) => `
      <tr>
        <td class="mono">${escapeHtml(p.sku)}</td>
        <td>${escapeHtml(p.name)}</td>
        <td class="num">${fmtQty(p.quantity)}</td>
        <td class="num">${fmtQty(p.stock)}</td>
      </tr>
    `),
    emptyState("fa-chart-simple", "Nenhuma movimentação encontrada", "Nenhum produto saiu do estoque nos últimos 30 dias."),
  );
}

function activityList(items) {
  if (!items.length) {
    return emptyState("fa-clock-rotate-left", "Nenhuma atividade encontrada", "As ações do sistema aparecerão aqui conforme você utiliza o ERP.");
  }
  return `
    <div class="activity-timeline">
      ${items.map((item) => `
        <div class="activity-item">
          <div class="activity-marker"><i class="fa-solid ${activityIcon(item.action)}"></i></div>
          <div class="activity-content">
            <div class="activity-main">${escapeHtml(item.description || item.entity)}</div>
            <div class="activity-meta">
              <span>${escapeHtml(item.user?.name || "Sistema")}</span>
              <span>${escapeHtml(actionLabel(item.action))}</span>
            </div>
          </div>
          <time>${fmtDate(item.created_at)}</time>
        </div>
      `).join("")}
    </div>
  `;
}

function activityIcon(action) {
  return ({
    login: "fa-right-to-bracket",
    logout: "fa-right-from-bracket",
    create: "fa-plus",
    update: "fa-pen",
    delete: "fa-ban",
    entry: "fa-truck-ramp-box",
    output: "fa-dolly",
    password_reset_request: "fa-key",
  })[action] || "fa-clipboard-check";
}

function actionLabel(action) {
  return ({
    login: "Login",
    logout: "Logout",
    create: "Criação",
    update: "Atualização",
    delete: "Exclusão",
    entry: "Entrada",
    output: "Saída",
    password_reset_request: "Recuperação de senha",
  })[action] || action || "Atividade";
}

async function renderProducts(params = {}) {
  await loadLookupData(["categories", "suppliers"]);
  const data = await api(`/api/products${buildQuery({ page: params.page || 1, search: params.search, stock_status: params.stock_status, category_id: params.category_id })}`);
  const canEdit = hasPermission("products.edit");
  const canDelete = hasPermission("products.delete");
  const canCreate = hasPermission("products.create");

  pageWrap().innerHTML = `
    ${pageHeader("produtos", "Catálogo completo de materiais, SKUs, custos e níveis mínimos.", canCreate ? `
      <button class="btn ghost" id="download-template"><i class="fa-solid fa-file-download"></i> Modelo</button>
      <button class="btn ghost" id="import-products"><i class="fa-solid fa-file-import"></i> Importar Planilha</button>
      <button class="btn primary" id="new-product"><i class="fa-solid fa-plus"></i> Novo produto</button>
    ` : "")}
    <div class="table-wrap">
      ${toolbar({
        id: "products",
        placeholder: "Buscar por nome, SKU ou código de barras",
        filters: `
          <select id="products-category">
            <option value="">Todas as categorias</option>
            ${optionList(MovStok.state.cache.categories, params.category_id)}
          </select>
          <select id="products-stock">
            <option value="">Todos os estoques</option>
            <option value="ok" ${params.stock_status === "ok" ? "selected" : ""}>OK</option>
            <option value="low" ${params.stock_status === "low" ? "selected" : ""}>Baixo</option>
            <option value="out" ${params.stock_status === "out" ? "selected" : ""}>Zerado</option>
          </select>
        `,
      })}
      ${productsTable(data.items || [], { canEdit, canDelete })}
      ${pagination(data.meta, "products")}
    </div>
  `;

  $("#products-search").value = params.search || "";
  bindSearch("#products-search", (value) => renderProducts({ ...params, page: 1, search: value }));
  $("#products-category").addEventListener("change", (event) => renderProducts({ ...params, page: 1, category_id: event.target.value }));
  $("#products-stock").addEventListener("change", (event) => renderProducts({ ...params, page: 1, stock_status: event.target.value }));
  bindPagination("products", (page) => renderProducts({ ...params, page }));
  $("#new-product")?.addEventListener("click", () => openProductModal());
  $("#import-products")?.addEventListener("click", () => openImportModal());
  $("#download-template")?.addEventListener("click", () => downloadImportTemplate());
  bindRowActions({
    edit: (id) => openProductModal(data.items.find((item) => item.id === id)),
    delete: (id) => deleteProduct(id),
  });
}

function productsTable(items, { canEdit, canDelete }) {
  return tableBody(
    [
      { label: "SKU" },
      { label: "Produto" },
      { label: "Categoria" },
      { label: "Fornecedor" },
      { label: "Estoque", cls: "num" },
      { label: "Mínimo", cls: "num" },
      { label: "Custo", cls: "num" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((p) => `
      <tr>
        <td class="mono">${escapeHtml(p.sku)}</td>
        <td>
          <strong>${escapeHtml(p.name)}</strong>
          <div class="text-muted">${escapeHtml(p.unit || "UN")}${p.barcode ? ` · ${escapeHtml(p.barcode)}` : ""}</div>
        </td>
        <td>${escapeHtml(p.category?.name || "-")}</td>
        <td>${escapeHtml(p.supplier?.name || "-")}</td>
        <td class="num">
          ${fmtQty(p.stock_quantity)}
          ${stockBar(p)}
        </td>
        <td class="num">${fmtQty(p.min_stock)}</td>
        <td class="num">${fmtMoney(p.cost_price)}</td>
        <td>${stockBadge(p)}</td>
        <td class="actions">
          ${canEdit ? `<button class="btn icon-only sm" title="Editar" data-action="edit" data-id="${p.id}"><i class="fa-solid fa-pen"></i></button>` : ""}
          ${canDelete ? `<button class="btn icon-only sm danger" title="Desativar" data-action="delete" data-id="${p.id}"><i class="fa-solid fa-ban"></i></button>` : ""}
        </td>
      </tr>
    `),
    emptyState("fa-tags", "Nenhum produto encontrado", "Cadastre produtos para movimentar o estoque."),
  );
}

function stockBar(p) {
  const max = Number(p.max_stock || p.min_stock || p.stock_quantity || 1);
  const percent = Math.max(5, Math.min(100, (Number(p.stock_quantity || 0) / max) * 100));
  return `
    <div class="stock-bar ${p.stock_status}">
      <span style="width:${percent}%"></span>
    </div>
  `;
}

function productForm(product = {}) {
  return `
    <form id="product-form" class="form-grid">
      <div class="field">
        <label>SKU</label>
        <input name="sku" value="${escapeHtml(product.sku || "")}" required>
      </div>
      <div class="field">
        <label>Unidade</label>
        <input name="unit" value="${escapeHtml(product.unit || "UN")}" required>
      </div>
      <div class="field full">
        <label>Nome do produto</label>
        <input name="name" value="${escapeHtml(product.name || "")}" required>
      </div>
      <div class="field">
        <label>Categoria</label>
        <select name="category_id">
          <option value="">Sem categoria</option>
          ${optionList(MovStok.state.cache.categories, product.category?.id)}
        </select>
      </div>
      <div class="field">
        <label>Fornecedor</label>
        <select name="supplier_id">
          <option value="">Sem fornecedor</option>
          ${optionList(MovStok.state.cache.suppliers, product.supplier?.id)}
        </select>
      </div>
      <div class="field">
        <label>Local de estoque</label>
        <input name="location_name" value="${escapeHtml(product.location?.name || "")}" placeholder="Ex: Prateleira 1">
      </div>
      <div class="field">
        <label>Código de barras</label>
        <input name="barcode" value="${escapeHtml(product.barcode || "")}">
      </div>
      <div class="field">
        <label>Custo unitário</label>
        <input name="cost_price" type="number" step="0.01" min="0" value="${product.cost_price ?? 0}">
      </div>
      <div class="field">
        <label>Preço de saída</label>
        <input name="sale_price" type="number" step="0.01" min="0" value="${product.sale_price ?? 0}">
      </div>
      <div class="field">
        <label>Estoque mínimo</label>
        <input name="min_stock" type="number" step="0.001" min="0" value="${product.min_stock ?? 0}">
      </div>
      <div class="field">
        <label>Estoque máximo</label>
        <input name="max_stock" type="number" step="0.001" min="0" value="${product.max_stock ?? 0}">
      </div>
      ${product.id ? "" : `
        <div class="field">
          <label>Estoque inicial</label>
          <input name="stock_quantity" type="number" step="0.001" min="0" value="0">
        </div>
      `}
      <div class="field">
        <label>Status</label>
        <select name="status">
          <option value="active" ${product.status === "active" ? "selected" : ""}>Ativo</option>
          <option value="inactive" ${product.status === "inactive" ? "selected" : ""}>Inativo</option>
          <option value="discontinued" ${product.status === "discontinued" ? "selected" : ""}>Descontinuado</option>
        </select>
      </div>
      <div class="field full">
        <label>Descrição</label>
        <textarea name="description">${escapeHtml(product.description || "")}</textarea>
      </div>
    </form>
  `;
}

async function loadExcelLibrary() {
  if (window.XLSX) return true;
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    // Versão 0.18.5 é a última estável disponível no jsDelivr/NPM
    script.src = "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js";
    script.type = "text/javascript";
    script.crossOrigin = "anonymous";
    script.onload = () => resolve(true);
    script.onerror = () => {
      toast("Erro de Carregamento", "A biblioteca XLSX (v0.18.5) falhou ao carregar. Verifique sua conexão ou política de rede.", "danger");
      reject(new Error("CSP or Network Error"));
    };
    document.head.appendChild(script);
  });
}

function downloadImportTemplate() {
  const headers = ["Nome Produto", "Código SKU", "Quantidade", "Preço Custo", "Preço Venda", "Estoque Mínimo", "Unidade"];
  const data = [
    ["Mouse Gamer", "M001", "10", "45.00", "99.90", "5", "UN"],
    ["Teclado RGB", "T001", "5", "80.00", "149.90", "2", "UN"]
  ];
  const csvContent = "\uFEFF" + [headers.join(","), ...data.map(e => e.join(","))].join("\n");
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "modelo_importacao_movstok.csv";
  link.click();
}

async function openImportModal() {
  openModal({
    title: "Importar Produtos",
    body: `
      <div class="empty-state" id="import-dropzone" style="border: 2px dashed var(--border-strong); cursor: pointer; padding: 40px;">
        <i class="fa-solid fa-cloud-arrow-up"></i>
        <h4>Selecione ou arraste a planilha</h4>
        <p>Suporta .xlsx, .xls e .csv</p>
        <input type="file" id="import-file" accept=".xlsx, .xls, .csv" style="display:none">
      </div>
      <div id="import-preview" style="display:none; margin-top:20px"></div>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" id="start-import" disabled>Iniciar Importação</button>
    `
  });

  // Carrega a biblioteca em segundo plano sem travar a abertura do modal
  loadExcelLibrary().catch(() => closeModal());

  const fileInput = $("#import-file");
  const dropzone = $("#import-dropzone");
  let importedData = [];

  dropzone.onclick = () => fileInput.click();
  fileInput.onchange = (e) => processFile(e.target.files[0]);

  async function processFile(file) {
    if (!file) return;
    
    // Garante que a lib está carregada antes de tentar ler o arquivo
    try {
      await loadExcelLibrary();
    } catch (e) {
      return; // O erro já foi disparado pelo toast no loadExcelLibrary
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const data = new Uint8Array(e.target.result);
      const workbook = XLSX.read(data, { type: 'array' });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json(sheet); // Lê como objetos usando a primeira linha como chave
      
      if (rows.length === 0) {
        toast("Planilha vazia", "Não foram encontrados dados para importar.", "warning");
        return;
      }

      // Helper de normalização: minúsculas, sem acentos, sem espaços extras
      const normalize = (s) => String(s || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim();

      // Mapeamento inteligente por nome de coluna
      importedData = rows.map(r => {
        const rowKeys = Object.keys(r).map(k => ({ 
          original: k, 
          normalized: normalize(k) 
        }));

        const findValue = (searchKeys) => {
          const normalizedSearch = searchKeys.map(normalize);
          const found = rowKeys.find(rk => normalizedSearch.includes(rk.normalized));
          return found ? r[found.original] : null;
        };

        const sku = findValue(["codigo", "sku", "codigo sku", "ref"]);
        const name = findValue(["item", "produto", "nome", "nome produto"]);

        // Validação básica: Requer ao menos SKU e Nome
        if (!sku || !name) return null;

        // Tenta resolver a categoria pelo nome usando o cache do MovStok
        const catName = findValue(["categoria"]);
        const category = MovStok.state.cache.categories.find(c => normalize(c.name) === normalize(catName));

        return {
          sku: String(sku).trim(),
          name: String(name).trim(),
          stock_quantity: findValue(["quantidade", "qtd", "estoque"]) || 0,
          unit: findValue(["unidade", "un"]) || "UN",
          cost_price: findValue(["preço custo", "custo", "preço"]) || 0,
          sale_price: findValue(["preço venda", "venda"]) || 0,
          min_stock: findValue(["estoque mínimo", "mínimo", "min"]) || 0,
          location_name: findValue(["localizacao", "localização", "local"]),
          category_id: category ? category.id : null
        };
      }).filter(item => item !== null);

      if (importedData.length === 0) {
        toast("Importação inválida", "Nenhum produto com Código e Item válidos foi identificado.", "warning");
        return;
      }

      renderPreview();
    };
    reader.readAsArrayBuffer(file);
  }

  function renderPreview() {
    dropzone.style.display = "none";
    const preview = $("#import-preview");
    preview.style.display = "block";
    preview.innerHTML = `
      <p class="text-muted" style="margin-bottom:10px">Encontrados <strong>${importedData.length}</strong> produtos para importar.</p>
      <div class="table-wrap" style="max-height: 300px">
        <table class="data-table">
          <thead><tr><th>Produto</th><th>SKU</th><th>Qtd</th><th>Preço</th></tr></thead>
          <tbody>
            ${importedData.slice(0, 5).map(r => `<tr><td>${r.name}</td><td>${r.sku}</td><td>${r.stock_quantity}</td><td>${r.sale_price}</td></tr>`).join('')}
          </tbody>
        </table>
        ${importedData.length > 5 ? `<p class="text-center text-muted" style="padding:10px">...e mais ${importedData.length - 5} itens.</p>` : ''}
      </div>
      <div id="import-progress" style="display:none; margin-top:15px">
        <div class="stock-bar" style="width:100%; height:10px"><span id="progress-bar" style="width:0%"></span></div>
        <small id="progress-text" class="text-muted"></small>
      </div>
    `;
    $("#start-import").disabled = false;
  }

  $("#start-import").onclick = async () => {
    const btn = $("#start-import");
    const progressDiv = $("#import-progress");
    const bar = $("#progress-bar");
    const txt = $("#progress-text");
    
    btn.disabled = true;
    progressDiv.style.display = "block";
    
    let success = 0;
    let errors = 0;

    for (let i = 0; i < importedData.length; i++) {
      try {
        const item = importedData[i];
        if (!item.name || !item.sku) throw new Error("Campos obrigatórios ausentes");
        
        await api("/api/products", { method: "POST", body: item });
        success++;
      } catch (err) {
        errors++;
        console.error("Erro na linha", i, err);
      }
      
      const pct = Math.round(((i + 1) / importedData.length) * 100);
      bar.style.width = pct + "%";
      txt.textContent = `Processando: ${i + 1}/${importedData.length}...`;
    }

    toast(
      "Importação concluída", 
      `${success} produtos importados com sucesso. ${errors} falhas.`,
      errors > 0 ? "warning" : "success"
    );
    
    closeModal();
    renderProducts();
  };
}

function openProductModal(product = null) {
  openModal({
    title: product ? "Editar produto" : "Novo produto",
    size: "lg",
    body: productForm(product || {}),
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="product-form">
        <i class="fa-solid fa-floppy-disk"></i> Salvar
      </button>
    `,
  });
  $("#product-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = getFormData(event.currentTarget);
      await api(product ? `/api/products/${product.id}` : "/api/products", {
        method: product ? "PUT" : "POST",
        body: data,
      });
      closeModal();
      toast("Produto salvo", "Cadastro atualizado com sucesso.");
      renderProducts();
    } catch (error) {
      toast("Erro ao salvar produto", error.message, "danger");
    }
  });
}

function deleteProduct(id) {
  confirmAction(
    "Desativar produto",
    "O produto será mantido no histórico, mas ficará inativo para novas operações.",
    "Desativar",
    async () => {
      await api(`/api/products/${id}`, { method: "DELETE" });
      toast("Produto desativado");
      renderProducts();
    },
  );
}

async function renderStock(params = {}) {
  const data = await api(`/api/stock${buildQuery({ page: params.page || 1, search: params.search, stock_status: params.stock_status })}`);
  pageWrap().innerHTML = `
    ${pageHeader("estoque", "Consulta operacional de saldo, alertas e cobertura.", `
      <a class="btn ghost" href="/api/reports/export/stock.xlsx"><i class="fa-solid fa-file-excel"></i> Excel</a>
      <a class="btn ghost" href="/api/reports/export/stock.pdf"><i class="fa-solid fa-file-pdf"></i> PDF</a>
    `)}
    <div class="table-wrap">
      ${toolbar({
        id: "stock",
        placeholder: "Buscar por produto ou SKU",
        filters: `
          <select id="stock-status">
            <option value="">Todos</option>
            <option value="ok" ${params.stock_status === "ok" ? "selected" : ""}>OK</option>
            <option value="low" ${params.stock_status === "low" ? "selected" : ""}>Baixo</option>
            <option value="out" ${params.stock_status === "out" ? "selected" : ""}>Zerado</option>
          </select>
        `,
      })}
      ${stockTable(data.items || [])}
      ${pagination(data.meta, "stock")}
    </div>
  `;

  $("#stock-search").value = params.search || "";
  bindSearch("#stock-search", (value) => renderStock({ ...params, page: 1, search: value }));
  $("#stock-status").addEventListener("change", (event) => renderStock({ ...params, page: 1, stock_status: event.target.value }));
  bindPagination("stock", (page) => renderStock({ ...params, page }));
  bindRowActions({
    entry: async (id) => {
      await loadLookupData(["products", "suppliers"]);
      openEntryModal({ product_id: id });
    },
    output: async (id) => {
      await loadLookupData(["products", "employees"]);
      openOutputModal({ product_id: id });
    },
  });
}

function stockTable(items) {
  return tableBody(
    [
      { label: "SKU" },
      { label: "Produto" },
      { label: "Local" },
      { label: "Atual", cls: "num" },
      { label: "Mínimo", cls: "num" },
      { label: "Máximo", cls: "num" },
      { label: "Valor", cls: "num" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((p) => `
      <tr>
        <td class="mono">${escapeHtml(p.sku)}</td>
        <td>
          <strong>${escapeHtml(p.name)}</strong>
          <div class="text-muted">${escapeHtml(p.category?.name || "Sem categoria")}</div>
        </td>
        <td>${escapeHtml(p.location?.name || "-")}</td>
        <td class="num">${fmtQty(p.stock_quantity)}${stockBar(p)}</td>
        <td class="num">${fmtQty(p.min_stock)}</td>
        <td class="num">${fmtQty(p.max_stock)}</td>
        <td class="num">${fmtMoney(Number(p.stock_quantity || 0) * Number(p.cost_price || 0))}</td>
        <td>${stockBadge(p)}</td>
        <td class="actions">
          <button class="btn icon-only sm success" title="Entrada" data-action="entry" data-id="${p.id}"><i class="fa-solid fa-plus"></i></button>
          <button class="btn icon-only sm danger" title="Saída" data-action="output" data-id="${p.id}"><i class="fa-solid fa-minus"></i></button>
        </td>
      </tr>
    `),
    emptyState("fa-boxes-stacked", "Sem itens em estoque", "Os saldos dos produtos aparecerão nesta consulta."),
  );
}

async function renderEntries(params = {}) {
  await loadLookupData(["products", "suppliers"]);
  const data = await api(`/api/entries${buildQuery({ page: params.page || 1 })}`);
  pageWrap().innerHTML = `
    ${pageHeader("entradas", "Recebimentos, compras, devoluções e ajustes positivos.", hasPermission("stock.entry") ? `
      <button class="btn primary" id="new-entry"><i class="fa-solid fa-plus"></i> Registrar entrada</button>
    ` : "")}
    ${entriesTable(data.items || [])}
    ${pagination(data.meta, "entries")}
  `;
  $("#new-entry")?.addEventListener("click", () => openEntryModal());
  bindPagination("entries", (page) => renderEntries({ ...params, page }));
  bindRowActions({
    cancel: (id) => cancelEntry(id),
  });
}

function entriesTable(items) {
  return table(
    [
      { label: "Data" },
      { label: "Documento" },
      { label: "Produto" },
      { label: "Fornecedor" },
      { label: "Qtde", cls: "num" },
      { label: "Custo", cls: "num" },
      { label: "Total", cls: "num" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((e) => `
      <tr>
        <td>${fmtDate(e.entry_date)}</td>
        <td class="mono">${escapeHtml(e.document || "-")}</td>
        <td>${escapeHtml(e.product?.sku || "")} · ${escapeHtml(e.product?.name || "-")}</td>
        <td>${escapeHtml(e.supplier?.name || "-")}</td>
        <td class="num">${fmtQty(e.quantity)}</td>
        <td class="num">${fmtMoney(e.unit_cost)}</td>
        <td class="num">${fmtMoney(e.total_cost)}</td>
        <td>${movementStatusBadge(e.status)}</td>
        <td class="actions">
          ${e.status !== "cancelled" ? `<button class="btn icon-only sm danger" title="Cancelar" data-action="cancel" data-id="${e.id}"><i class="fa-solid fa-ban"></i></button>` : ""}
        </td>
      </tr>
    `),
    emptyState("fa-arrow-down-to-bracket", "Nenhuma entrada registrada", "Registre recebimentos para atualizar o saldo de estoque."),
  );
}

function movementProductOptions(selected) {
  return MovStok.state.cache.products.map((p) => `
    <option value="${p.id}" ${Number(selected) === Number(p.id) ? "selected" : ""}>
      ${escapeHtml(p.sku)} · ${escapeHtml(p.name)} (${fmtQty(p.stock_quantity)} ${escapeHtml(p.unit)})
    </option>
  `).join("");
}

function openEntryModal(defaults = {}) {
  openModal({
    title: "Registrar entrada",
    size: "lg",
    body: `
      <form id="entry-form" class="form-grid">
        <div class="field full">
          <label>Produto</label>
          <select name="product_id" required>
            <option value="">Selecione</option>
            ${movementProductOptions(defaults.product_id)}
          </select>
        </div>
        <div class="field">
          <label>Fornecedor</label>
          <select name="supplier_id">
            <option value="">Fornecedor do produto</option>
            ${optionList(MovStok.state.cache.suppliers)}
          </select>
        </div>
        <div class="field">
          <label>Documento</label>
          <input name="document" placeholder="NF, OC ou referência">
        </div>
        <div class="field">
          <label>Quantidade</label>
          <input name="quantity" type="number" min="0.001" step="0.001" required>
        </div>
        <div class="field">
          <label>Custo unitário</label>
          <input name="unit_cost" type="number" min="0" step="0.01">
        </div>
        <div class="field full">
          <label>Observações</label>
          <textarea name="notes"></textarea>
        </div>
      </form>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn success" type="submit" form="entry-form">
        <i class="fa-solid fa-check"></i> Confirmar entrada
      </button>
    `,
  });
  $("#entry-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/entries", { method: "POST", body: getFormData(event.currentTarget) });
      closeModal();
      toast("Entrada registrada", "Saldo atualizado com sucesso.");
      renderPage(MovStok.state.currentPage);
    } catch (error) {
      toast("Erro ao registrar entrada", error.message, "danger");
    }
  });
}

function cancelEntry(id) {
  confirmAction(
    "Cancelar entrada",
    "O saldo do produto será revertido conforme a quantidade dessa entrada.",
    "Cancelar entrada",
    async () => {
      await api(`/api/entries/${id}`, { method: "DELETE" });
      toast("Entrada cancelada");
      renderEntries();
    },
  );
}

async function renderOutputs(params = {}) {
  await loadLookupData(["products", "employees"]);
  const data = await api(`/api/outputs${buildQuery({ page: params.page || 1 })}`);
  pageWrap().innerHTML = `
    ${pageHeader("saidas", "Requisições internas, consumo, perdas, transferências e vendas.", hasPermission("stock.output") ? `
      <button class="btn primary" id="new-output"><i class="fa-solid fa-plus"></i> Registrar saída</button>
    ` : "")}
    ${outputsTable(data.items || [])}
    ${pagination(data.meta, "outputs")}
  `;
  $("#new-output")?.addEventListener("click", () => openOutputModal());
  bindPagination("outputs", (page) => renderOutputs({ ...params, page }));
  bindRowActions({
    cancel: (id) => cancelOutput(id),
  });
}

function outputsTable(items) {
  return table(
    [
      { label: "Data" },
      { label: "Documento" },
      { label: "Produto" },
      { label: "Funcionário" },
      { label: "Motivo" },
      { label: "Qtde", cls: "num" },
      { label: "Total", cls: "num" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((o) => `
      <tr>
        <td>${fmtDate(o.output_date)}</td>
        <td class="mono">${escapeHtml(o.document || "-")}</td>
        <td>${escapeHtml(o.product?.sku || "")} · ${escapeHtml(o.product?.name || "-")}</td>
        <td>${escapeHtml(o.employee?.enrollment || "")} ${escapeHtml(o.employee?.name || "-")}</td>
        <td>${escapeHtml(reasonLabel(o.reason))}</td>
        <td class="num">${fmtQty(o.quantity)}</td>
        <td class="num">${fmtMoney(o.total_price)}</td>
        <td>${movementStatusBadge(o.status)}</td>
        <td class="actions">
          ${o.status !== "cancelled" ? `<button class="btn icon-only sm danger" title="Cancelar" data-action="cancel" data-id="${o.id}"><i class="fa-solid fa-ban"></i></button>` : ""}
        </td>
      </tr>
    `),
    emptyState("fa-arrow-up-from-bracket", "Nenhuma saída registrada", "Registre requisições para baixar o saldo de estoque."),
  );
}

function openOutputModal(defaults = {}) {
  openModal({
    title: "Registrar saída",
    size: "lg",
    body: `
      <form id="output-form" class="form-grid">
        <div class="field full">
          <label>Produto</label>
          <select name="product_id" required>
            <option value="">Selecione</option>
            ${movementProductOptions(defaults.product_id)}
          </select>
        </div>
        <div class="field">
          <label>Funcionário</label>
          <select name="employee_id">
            <option value="">Sem vínculo</option>
            ${MovStok.state.cache.employees.map((e) => `<option value="${e.id}">${escapeHtml(e.enrollment)} · ${escapeHtml(e.name)}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>Motivo</label>
          <select name="reason">
            <option value="consumption">Consumo</option>
            <option value="sale">Venda</option>
            <option value="loss">Perda</option>
            <option value="transfer">Transferência</option>
          </select>
        </div>
        <div class="field">
          <label>Documento</label>
          <input name="document" placeholder="REQ, OS ou referência">
        </div>
        <div class="field">
          <label>Quantidade</label>
          <input name="quantity" type="number" min="0.001" step="0.001" required>
        </div>
        <div class="field">
          <label>Valor unitário</label>
          <input name="unit_price" type="number" min="0" step="0.01">
        </div>
        <div class="field full">
          <label>Destino</label>
          <input name="destination" placeholder="Setor, obra, centro de custo">
        </div>
        <div class="field full">
          <label>Observações</label>
          <textarea name="notes"></textarea>
        </div>
      </form>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn danger" type="submit" form="output-form">
        <i class="fa-solid fa-check"></i> Confirmar saída
      </button>
    `,
  });
  $("#output-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/outputs", { method: "POST", body: getFormData(event.currentTarget) });
      closeModal();
      toast("Saída registrada", "Saldo atualizado com sucesso.");
      renderPage(MovStok.state.currentPage);
    } catch (error) {
      toast("Erro ao registrar saída", error.message, "danger");
    }
  });
}

function cancelOutput(id) {
  confirmAction(
    "Cancelar saída",
    "O saldo do produto será devolvido ao estoque.",
    "Cancelar saída",
    async () => {
      await api(`/api/outputs/${id}`, { method: "DELETE" });
      toast("Saída cancelada");
      renderOutputs();
    },
  );
}

async function renderCategories() {
  const data = await api("/api/categories");
  pageWrap().innerHTML = `
    ${pageHeader("categorias", "Agrupamento de produtos para relatórios, filtros e operação.", hasPermission("categories.manage") ? `
      <button class="btn primary" id="new-category"><i class="fa-solid fa-plus"></i> Nova categoria</button>
    ` : "")}
    ${categoriesTable(data.items || [])}
  `;
  $("#new-category")?.addEventListener("click", () => openCategoryModal());
  bindRowActions({
    edit: (id) => openCategoryModal((data.items || []).find((item) => item.id === id)),
    delete: (id) => deleteCategory(id),
  });
}

function categoriesTable(items) {
  return table(
    [
      { label: "Nome" },
      { label: "Descrição" },
      { label: "Produtos", cls: "num" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((c) => `
      <tr>
        <td>
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${escapeHtml(c.color || "#1d4ed8")};margin-right:8px"></span>
          <strong>${escapeHtml(c.name)}</strong>
        </td>
        <td>${escapeHtml(c.description || "-")}</td>
        <td class="num">${fmtQty(c.products_count)}</td>
        <td>${activeBadge(c.active)}</td>
        <td class="actions">
          <button class="btn icon-only sm" title="Editar" data-action="edit" data-id="${c.id}"><i class="fa-solid fa-pen"></i></button>
          <button class="btn icon-only sm danger" title="Excluir" data-action="delete" data-id="${c.id}"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
    `),
    emptyState("fa-layer-group", "Nenhuma categoria", "Organize o catálogo por grupos de materiais."),
  );
}

function openCategoryModal(category = null) {
  openModal({
    title: category ? "Editar categoria" : "Nova categoria",
    body: `
      <form id="category-form" class="form-grid">
        <div class="field">
          <label>Nome</label>
          <input name="name" value="${escapeHtml(category?.name || "")}" required>
        </div>
        <div class="field">
          <label>Cor</label>
          <input name="color" type="color" value="${escapeHtml(category?.color || "#1d4ed8")}">
        </div>
        <div class="field full">
          <label>Descrição</label>
          <textarea name="description">${escapeHtml(category?.description || "")}</textarea>
        </div>
      </form>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="category-form">Salvar</button>
    `,
  });
  $("#category-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(category ? `/api/categories/${category.id}` : "/api/categories", {
        method: category ? "PUT" : "POST",
        body: getFormData(event.currentTarget),
      });
      closeModal();
      toast("Categoria salva");
      renderCategories();
    } catch (error) {
      toast("Erro ao salvar categoria", error.message, "danger");
    }
  });
}

function deleteCategory(id) {
  confirmAction(
    "Excluir categoria",
    "A categoria só será removida se não houver produtos vinculados.",
    "Excluir",
    async () => {
      await api(`/api/categories/${id}`, { method: "DELETE" });
      toast("Categoria excluída");
      renderCategories();
    },
  );
}

async function renderSuppliers(params = {}) {
  const data = await api(`/api/suppliers${buildQuery({ page: params.page || 1, search: params.search })}`);
  pageWrap().innerHTML = `
    ${pageHeader("fornecedores", "Cadastro comercial para compras e recebimentos.", hasPermission("suppliers.manage") ? `
      <button class="btn primary" id="new-supplier"><i class="fa-solid fa-plus"></i> Novo fornecedor</button>
    ` : "")}
    <div class="table-wrap">
      ${toolbar({ id: "suppliers", placeholder: "Buscar por nome, CNPJ ou e-mail" })}
      ${suppliersTable(data.items || [])}
      ${pagination(data.meta, "suppliers")}
    </div>
  `;
  $("#suppliers-search").value = params.search || "";
  bindSearch("#suppliers-search", (value) => renderSuppliers({ ...params, page: 1, search: value }));
  bindPagination("suppliers", (page) => renderSuppliers({ ...params, page }));
  $("#new-supplier")?.addEventListener("click", () => openSupplierModal());
  bindRowActions({
    edit: (id) => openSupplierModal((data.items || []).find((item) => item.id === id)),
    delete: (id) => deleteSupplier(id),
  });
}

function suppliersTable(items) {
  return tableBody(
    [
      { label: "Fornecedor" },
      { label: "CNPJ" },
      { label: "Contato" },
      { label: "Cidade/UF" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((s) => `
      <tr>
        <td>
          <strong>${escapeHtml(s.name)}</strong>
          <div class="text-muted">${escapeHtml(s.email || "-")}</div>
        </td>
        <td class="mono">${escapeHtml(s.cnpj || "-")}</td>
        <td>${escapeHtml(s.contact_person || "-")}<div class="text-muted">${escapeHtml(s.phone || "")}</div></td>
        <td>${escapeHtml([s.city, s.state].filter(Boolean).join("/") || "-")}</td>
        <td>${activeBadge(s.active)}</td>
        <td class="actions">
          <button class="btn icon-only sm" title="Editar" data-action="edit" data-id="${s.id}"><i class="fa-solid fa-pen"></i></button>
          <button class="btn icon-only sm danger" title="Desativar" data-action="delete" data-id="${s.id}"><i class="fa-solid fa-ban"></i></button>
        </td>
      </tr>
    `),
    emptyState("fa-truck-fast", "Nenhum fornecedor", "Cadastre fornecedores para vincular compras e produtos."),
  );
}

function supplierForm(s = {}) {
  return `
    <form id="supplier-form" class="form-grid">
      <div class="field full">
        <label>Nome/Razão social</label>
        <input name="name" value="${escapeHtml(s.name || "")}" required>
      </div>
      <div class="field">
        <label>CNPJ</label>
        <input name="cnpj" value="${escapeHtml(s.cnpj || "")}">
      </div>
      <div class="field">
        <label>Contato</label>
        <input name="contact_person" value="${escapeHtml(s.contact_person || "")}">
      </div>
      <div class="field">
        <label>E-mail</label>
        <input name="email" type="email" value="${escapeHtml(s.email || "")}">
      </div>
      <div class="field">
        <label>Telefone</label>
        <input name="phone" value="${escapeHtml(s.phone || "")}">
      </div>
      <div class="field full">
        <label>Endereço</label>
        <input name="address" value="${escapeHtml(s.address || "")}">
      </div>
      <div class="field">
        <label>Cidade</label>
        <input name="city" value="${escapeHtml(s.city || "")}">
      </div>
      <div class="field">
        <label>UF</label>
        <input name="state" value="${escapeHtml(s.state || "")}" maxlength="2">
      </div>
      <div class="field full">
        <label>Observações</label>
        <textarea name="notes">${escapeHtml(s.notes || "")}</textarea>
      </div>
    </form>
  `;
}

function openSupplierModal(supplier = null) {
  openModal({
    title: supplier ? "Editar fornecedor" : "Novo fornecedor",
    size: "lg",
    body: supplierForm(supplier || {}),
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="supplier-form">Salvar</button>
    `,
  });
  $("#supplier-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(supplier ? `/api/suppliers/${supplier.id}` : "/api/suppliers", {
        method: supplier ? "PUT" : "POST",
        body: getFormData(event.currentTarget),
      });
      closeModal();
      toast("Fornecedor salvo");
      renderSuppliers();
    } catch (error) {
      toast("Erro ao salvar fornecedor", error.message, "danger");
    }
  });
}

function deleteSupplier(id) {
  confirmAction(
    "Desativar fornecedor",
    "O fornecedor será mantido para histórico e ocultado de novas operações.",
    "Desativar",
    async () => {
      await api(`/api/suppliers/${id}`, { method: "DELETE" });
      toast("Fornecedor desativado");
      renderSuppliers();
    },
  );
}

async function renderEmployees(params = {}) {
  const data = await api(`/api/employees${buildQuery({ page: params.page || 1, search: params.search, status: params.status })}`);
  pageWrap().innerHTML = `
    ${pageHeader("funcionarios", "Equipe operacional vinculada às requisições e movimentações.", hasPermission("employees.manage") ? `
      <button class="btn primary" id="new-employee"><i class="fa-solid fa-plus"></i> Novo funcionário</button>
    ` : "")}
    <div class="table-wrap">
      ${toolbar({
        id: "employees",
        placeholder: "Buscar por nome, matrícula, CPF ou setor",
        filters: `
          <select id="employees-status">
            <option value="">Todos</option>
            <option value="active" ${params.status === "active" ? "selected" : ""}>Ativos</option>
            <option value="leave" ${params.status === "leave" ? "selected" : ""}>Afastados</option>
            <option value="terminated" ${params.status === "terminated" ? "selected" : ""}>Desligados</option>
          </select>
        `,
      })}
      ${employeesTable(data.items || [])}
      ${pagination(data.meta, "employees")}
    </div>
  `;
  $("#employees-search").value = params.search || "";
  bindSearch("#employees-search", (value) => renderEmployees({ ...params, page: 1, search: value }));
  $("#employees-status").addEventListener("change", (event) => renderEmployees({ ...params, page: 1, status: event.target.value }));
  bindPagination("employees", (page) => renderEmployees({ ...params, page }));
  $("#new-employee")?.addEventListener("click", () => openEmployeeModal());
  bindRowActions({
    edit: (id) => openEmployeeModal((data.items || []).find((item) => item.id === id)),
    delete: (id) => deleteEmployee(id),
  });
}

function employeesTable(items) {
  return tableBody(
    [
      { label: "Matrícula" },
      { label: "Funcionário" },
      { label: "Setor" },
      { label: "Cargo" },
      { label: "Contato" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((e) => `
      <tr>
        <td class="mono">${escapeHtml(e.enrollment)}</td>
        <td>
          <strong>${escapeHtml(e.name)}</strong>
          <div class="text-muted">${escapeHtml(e.cpf || "-")}</div>
        </td>
        <td>${escapeHtml(e.department || "-")}</td>
        <td>${escapeHtml(e.position || "-")}</td>
        <td>${escapeHtml(e.email || "-")}<div class="text-muted">${escapeHtml(e.phone || "")}</div></td>
        <td>${userStatusBadge(e.status)}</td>
        <td class="actions">
          <button class="btn icon-only sm" title="Editar" data-action="edit" data-id="${e.id}"><i class="fa-solid fa-pen"></i></button>
          <button class="btn icon-only sm danger" title="Desligar" data-action="delete" data-id="${e.id}"><i class="fa-solid fa-user-slash"></i></button>
        </td>
      </tr>
    `),
    emptyState("fa-users", "Nenhum funcionário", "Cadastre colaboradores para rastrear requisições internas."),
  );
}

function employeeForm(e = {}) {
  return `
    <form id="employee-form" class="form-grid">
      <div class="field">
        <label>Matrícula</label>
        <input name="enrollment" value="${escapeHtml(e.enrollment || "")}" ${e.id ? "readonly" : ""} placeholder="Automática se vazio">
      </div>
      <div class="field">
        <label>CPF</label>
        <input name="cpf" value="${escapeHtml(e.cpf || "")}">
      </div>
      <div class="field full">
        <label>Nome</label>
        <input name="name" value="${escapeHtml(e.name || "")}" required>
      </div>
      <div class="field">
        <label>E-mail</label>
        <input name="email" type="email" value="${escapeHtml(e.email || "")}">
      </div>
      <div class="field">
        <label>Telefone</label>
        <input name="phone" value="${escapeHtml(e.phone || "")}">
      </div>
      <div class="field">
        <label>Setor</label>
        <input name="department" value="${escapeHtml(e.department || "")}">
      </div>
      <div class="field">
        <label>Cargo</label>
        <input name="position" value="${escapeHtml(e.position || "")}">
      </div>
      <div class="field">
        <label>Status</label>
        <select name="status">
          <option value="active" ${e.status === "active" ? "selected" : ""}>Ativo</option>
          <option value="leave" ${e.status === "leave" ? "selected" : ""}>Afastado</option>
          <option value="terminated" ${e.status === "terminated" ? "selected" : ""}>Desligado</option>
        </select>
      </div>
      <div class="field full">
        <label>Observações</label>
        <textarea name="notes">${escapeHtml(e.notes || "")}</textarea>
      </div>
    </form>
  `;
}

function openEmployeeModal(employee = null) {
  openModal({
    title: employee ? "Editar funcionário" : "Novo funcionário",
    size: "lg",
    body: employeeForm(employee || {}),
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="employee-form">Salvar</button>
    `,
  });
  $("#employee-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(employee ? `/api/employees/${employee.id}` : "/api/employees", {
        method: employee ? "PUT" : "POST",
        body: getFormData(event.currentTarget),
      });
      closeModal();
      toast("Funcionário salvo");
      renderEmployees();
    } catch (error) {
      toast("Erro ao salvar funcionário", error.message, "danger");
    }
  });
}

function deleteEmployee(id) {
  confirmAction(
    "Desligar funcionário",
    "O funcionário ficará com status desligado e permanecerá no histórico.",
    "Desligar",
    async () => {
      await api(`/api/employees/${id}`, { method: "DELETE" });
      toast("Funcionário desligado");
      renderEmployees();
    },
  );
}

async function renderEnrollments(params = {}) {
  const data = await api(`/api/employees${buildQuery({ page: params.page || 1, search: params.search })}`);
  pageWrap().innerHTML = `
    ${pageHeader("matriculas", "Consulta rápida de matrículas, setores e vínculos operacionais.")}
    <div class="table-wrap">
      ${toolbar({ id: "enrollments", placeholder: "Buscar matrícula, nome ou setor" })}
      ${tableBody(
        [
          { label: "Matrícula" },
          { label: "Nome" },
          { label: "Setor" },
          { label: "Cargo" },
          { label: "Admissão" },
          { label: "Status" },
        ],
        (data.items || []).map((e) => `
          <tr>
            <td class="mono"><strong>${escapeHtml(e.enrollment)}</strong></td>
            <td>${escapeHtml(e.name)}</td>
            <td>${escapeHtml(e.department || "-")}</td>
            <td>${escapeHtml(e.position || "-")}</td>
            <td>${fmtDate(e.hire_date, false)}</td>
            <td>${userStatusBadge(e.status)}</td>
          </tr>
        `),
        emptyState("fa-id-card", "Nenhuma matrícula", "As matrículas cadastradas em funcionários aparecerão aqui."),
      )}
      ${pagination(data.meta, "enrollments")}
    </div>
  `;
  $("#enrollments-search").value = params.search || "";
  bindSearch("#enrollments-search", (value) => renderEnrollments({ ...params, page: 1, search: value }));
  bindPagination("enrollments", (page) => renderEnrollments({ ...params, page }));
}

async function renderReports() {
  const summary = await api("/api/reports/summary?days=30");
  pageWrap().innerHTML = `
    ${pageHeader("relatorios", "Indicadores e exportações gerenciais em PDF e Excel.", `
      <a class="btn ghost" href="/api/reports/export/stock.xlsx"><i class="fa-solid fa-file-excel"></i> Estoque Excel</a>
      <a class="btn ghost" href="/api/reports/export/stock.pdf"><i class="fa-solid fa-file-pdf"></i> Estoque PDF</a>
      <a class="btn ghost" href="/api/reports/export/movements.xlsx"><i class="fa-solid fa-file-lines"></i> Movimentações</a>
    `)}
    <div class="kpi-grid">
      ${kpiCard("Entradas", summary.entries_count, `${fmtQty(summary.total_in)} unidades`, "fa-arrow-down-to-bracket", "green")}
      ${kpiCard("Saídas", summary.outputs_count, `${fmtQty(summary.total_out)} unidades`, "fa-arrow-up-from-bracket", "red")}
      ${kpiCard("Valor recebido", fmtMoney(summary.value_in), "Últimos 30 dias", "fa-file-invoice-dollar", "cyan")}
      ${kpiCard("Valor de saída", fmtMoney(summary.value_out), "Últimos 30 dias", "fa-receipt", "amber")}
    </div>
    <section class="panel">
      <div class="panel-head">
        <h3>Exportações disponíveis</h3>
      </div>
      <div class="panel-body">
        <table class="data-table">
          <tbody>
            <tr>
              <td><strong>Relatório de estoque</strong><div class="text-muted">Saldos, custos, categorias e status</div></td>
              <td class="actions">
                <a class="btn sm ghost" href="/api/reports/export/stock.xlsx"><i class="fa-solid fa-file-excel"></i> Excel</a>
                <a class="btn sm ghost" href="/api/reports/export/stock.pdf"><i class="fa-solid fa-file-pdf"></i> PDF</a>
              </td>
            </tr>
            <tr>
              <td><strong>Relatório de movimentações</strong><div class="text-muted">Entradas e saídas dos últimos 30 dias</div></td>
              <td class="actions">
                <a class="btn sm ghost" href="/api/reports/export/movements.xlsx"><i class="fa-solid fa-file-excel"></i> Excel</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `;
}

async function renderFinance() {
  const summary = await api("/api/finance/summary");
  pageWrap().innerHTML = `
    ${pageHeader("financeiro", "Valores operacionais do estoque e movimentações financeiras.")}
    <div class="kpi-grid">
      ${kpiCard("Valor em estoque", fmtMoney(summary.stock_value), "Custo atual dos saldos", "fa-boxes-stacked", "blue")}
      ${kpiCard("Compras 30 dias", fmtMoney(summary.entries_value_30d), "Entradas confirmadas", "fa-file-invoice-dollar", "green")}
      ${kpiCard("Saídas 30 dias", fmtMoney(summary.outputs_value_30d), "Saídas confirmadas", "fa-receipt", "amber")}
    </div>
    <section class="panel">
      <div class="panel-head"><h3>Controle financeiro</h3></div>
      <div class="panel-body">
        <table class="data-table">
          <tbody>
            <tr><td><strong>Permissão ativa</strong><div class="text-muted">Somente perfis com finance.view acessam esta tela.</div></td><td>${statusBadge("ready", { ready: { label: "Protegido", cls: "info" } })}</td></tr>
            <tr><td><strong>Gestão financeira</strong><div class="text-muted">Use finance.manage para liberar futuras ações de edição financeira.</div></td><td>${hasPermission("finance.manage") ? statusBadge("ready", { ready: { label: "Liberada", cls: "success" } }) : statusBadge("locked", { locked: { label: "Restrita", cls: "neutral" } })}</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  `;
}

async function renderAdministration() {
  const data = await api("/api/admin/system");
  pageWrap().innerHTML = `
    ${pageHeader("administracao", "Administração do sistema, segurança e governança de acesso.")}
    <div class="kpi-grid">
      ${kpiCard("Usuários", data.users, "Nesta empresa", "fa-users", "blue")}
      ${kpiCard("Perfis", data.roles, "Roles cadastradas", "fa-user-shield", "cyan")}
      ${kpiCard("Permissões", data.permissions, "Códigos RBAC", "fa-key", "green")}
      ${kpiCard("Auditoria", data.activities, "Eventos registrados", "fa-clipboard-list", "amber")}
    </div>
    <section class="panel">
      <div class="panel-head"><h3>Ações administrativas</h3></div>
      <div class="panel-body">
        <table class="data-table">
          <tbody>
            <tr><td><strong>Gerenciar usuários</strong><div class="text-muted">Criar, editar, desativar e alterar perfis.</div></td><td class="actions"><button class="btn sm ghost" id="admin-users"><i class="fa-solid fa-user-shield"></i> Abrir</button></td></tr>
            <tr><td><strong>Auditoria</strong><div class="text-muted">Acompanhar log de ações do sistema.</div></td><td class="actions"><button class="btn sm ghost" id="admin-activities"><i class="fa-solid fa-clipboard-list"></i> Abrir</button></td></tr>
          </tbody>
        </table>
      </div>
    </section>
  `;
  $("#admin-users")?.addEventListener("click", () => navigate("usuarios"));
  $("#admin-activities")?.addEventListener("click", () => navigate("atividades"));
}

async function renderActivities(params = {}) {
  const data = await api(`/api/activities${buildQuery({ page: params.page || 1, action: params.action, entity: params.entity })}`);
  pageWrap().innerHTML = `
    ${pageHeader("atividades", "Auditoria de ações realizadas pelos usuários do sistema.")}
    <div class="table-wrap">
      ${toolbar({
        id: "activities",
        placeholder: "Filtro por entidade",
        filters: `
          <select id="activities-action">
            <option value="">Todas as ações</option>
            <option value="login" ${params.action === "login" ? "selected" : ""}>Login</option>
            <option value="create" ${params.action === "create" ? "selected" : ""}>Criação</option>
            <option value="update" ${params.action === "update" ? "selected" : ""}>Atualização</option>
            <option value="delete" ${params.action === "delete" ? "selected" : ""}>Exclusão/cancelamento</option>
            <option value="entry" ${params.action === "entry" ? "selected" : ""}>Entrada</option>
            <option value="output" ${params.action === "output" ? "selected" : ""}>Saída</option>
            <option value="export" ${params.action === "export" ? "selected" : ""}>Exportação</option>
          </select>
        `,
      })}
      ${activitiesTable(data.items || [])}
      ${pagination(data.meta, "activities")}
    </div>
  `;
  $("#activities-search").value = params.entity || "";
  bindSearch("#activities-search", (value) => renderActivities({ ...params, page: 1, entity: value }));
  $("#activities-action").addEventListener("change", (event) => renderActivities({ ...params, page: 1, action: event.target.value }));
  bindPagination("activities", (page) => renderActivities({ ...params, page }));
}

function activitiesTable(items) {
  return tableBody(
    [
      { label: "Data" },
      { label: "Usuário" },
      { label: "Ação" },
      { label: "Entidade" },
      { label: "Descrição" },
      { label: "IP" },
    ],
    items.map((a) => `
      <tr>
        <td>${fmtDate(a.created_at)}</td>
        <td>${escapeHtml(a.user?.name || "Sistema")}</td>
        <td><span class="badge info">${escapeHtml(a.action)}</span></td>
        <td>${escapeHtml(a.entity)} ${a.entity_id ? `<span class="text-muted">#${a.entity_id}</span>` : ""}</td>
        <td>${escapeHtml(a.description || "-")}</td>
        <td class="mono">${escapeHtml(a.ip || "-")}</td>
      </tr>
    `),
    emptyState("fa-clock-rotate-left", "Sem atividades", "Os logs de auditoria aparecerão conforme o sistema for usado."),
  );
}

async function renderUsers(params = {}) {
  await loadLookupData(["roles", "permissions"]);
  const data = await api(`/api/users${buildQuery({ search: params.search })}`);
  pageWrap().innerHTML = `
    ${pageHeader("usuarios", "Controle de acesso, perfis e permissões por função.", hasPermission("users.manage") ? `
      <button class="btn primary" id="new-user"><i class="fa-solid fa-plus"></i> Novo usuário</button>
    ` : "")}
    <div class="table-wrap">
      ${toolbar({ id: "users", placeholder: "Buscar por nome ou e-mail" })}
      ${usersTable(data.items || [])}
    </div>
  `;
  $("#users-search").value = params.search || "";
  bindSearch("#users-search", (value) => renderUsers({ ...params, search: value }));
  $("#new-user")?.addEventListener("click", () => openUserModal());
  bindRowActions({
    edit: (id) => openUserModal((data.items || []).find((item) => item.id === id)),
    delete: (id) => deleteUser(id),
  });
}

function usersTable(items) {
  return tableBody(
    [
      { label: "Usuário" },
      { label: "Perfil" },
      { label: "Telefone" },
      { label: "Último login" },
      { label: "Status" },
      { label: "", cls: "actions" },
    ],
    items.map((u) => `
      <tr>
        <td>
          <strong>${escapeHtml(u.name)}</strong>
          <div class="text-muted">${escapeHtml(u.email)}</div>
        </td>
        <td>${escapeHtml(roleLabel(u.role))}</td>
        <td>${escapeHtml(u.phone || "-")}</td>
        <td>${fmtDate(u.last_login_at)}</td>
        <td>${userStatusBadge(u.status)}</td>
        <td class="actions">
          <button class="btn icon-only sm" title="Editar" data-action="edit" data-id="${u.id}"><i class="fa-solid fa-pen"></i></button>
          <button class="btn icon-only sm danger" title="Desativar" data-action="delete" data-id="${u.id}"><i class="fa-solid fa-ban"></i></button>
        </td>
      </tr>
    `),
    emptyState("fa-user-shield", "Nenhum usuário", "Usuários autorizados aparecerão nesta tela."),
  );
}

function userForm(u = {}) {
  const selectedRole = u.role?.id || "";
  return `
    <form id="user-form" class="form-grid">
      <div class="field full">
        <label>Nome</label>
        <input name="name" value="${escapeHtml(u.name || "")}" required>
      </div>
      <div class="field full">
        <label>E-mail</label>
        <input name="email" type="email" value="${escapeHtml(u.email || "")}" ${u.id ? "readonly" : "required"}>
      </div>
      <div class="field">
        <label>Telefone</label>
        <input name="phone" value="${escapeHtml(u.phone || "")}">
      </div>
      <div class="field">
        <label>Perfil</label>
        <select name="role_id" id="user-role-select">
          <option value="">Sem perfil</option>
          ${optionList(MovStok.state.cache.roles, selectedRole, "label")}
        </select>
      </div>
      <div class="field full">
        <label>Permissões do perfil</label>
        <div id="role-permission-preview" style="min-height:42px;border:1px solid var(--border-strong);border-radius:var(--radius);padding:8px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;background:var(--panel-2)"></div>
      </div>
      <div class="field">
        <label>Status</label>
        <select name="status">
          <option value="active" ${u.status === "active" ? "selected" : ""}>Ativo</option>
          <option value="inactive" ${u.status === "inactive" ? "selected" : ""}>Inativo</option>
          <option value="blocked" ${u.status === "blocked" ? "selected" : ""}>Bloqueado</option>
        </select>
      </div>
      <div class="field">
        <label>${u.id ? "Nova senha" : "Senha"}</label>
        <input name="password" type="password" ${u.id ? "" : "required"} minlength="6">
      </div>
    </form>
  `;
}

function rolePermissionPreview(roleId) {
  const role = MovStok.state.cache.roles.find((item) => Number(item.id) === Number(roleId));
  if (!role) return `<span class="text-muted">Selecione um perfil para aplicar permissões.</span>`;
  if (["admin", "super_admin"].includes(role.name)) {
    return `<span class="badge success">Acesso total</span>`;
  }
  const labels = (role.permissions || []).map((code) => {
    const permission = MovStok.state.cache.permissions.find((item) => item.code === code);
    return permission?.label || code;
  });
  return labels.length
    ? labels.map((label) => `<span class="badge info">${escapeHtml(label)}</span>`).join("")
    : `<span class="badge neutral">Sem permissões</span>`;
}

function openUserModal(user = null) {
  openModal({
    title: user ? "Editar usuário" : "Novo usuário",
    body: userForm(user || {}),
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="user-form">Salvar</button>
    `,
  });
  const roleSelect = $("#user-role-select");
  const permissionPreview = $("#role-permission-preview");
  const refreshPermissions = () => {
    permissionPreview.innerHTML = rolePermissionPreview(roleSelect.value);
  };
  roleSelect?.addEventListener("change", refreshPermissions);
  refreshPermissions();
  $("#user-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = getFormData(event.currentTarget);
      await api(user ? `/api/users/${user.id}` : "/api/users", {
        method: user ? "PUT" : "POST",
        body: data,
      });
      closeModal();
      toast("Usuário salvo");
      renderUsers();
    } catch (error) {
      toast("Erro ao salvar usuário", error.message, "danger");
    }
  });
}

function deleteUser(id) {
  confirmAction(
    "Desativar usuário",
    "O acesso do usuário será desativado imediatamente.",
    "Desativar",
    async () => {
      await api(`/api/users/${id}`, { method: "DELETE" });
      toast("Usuário desativado");
      renderUsers();
    },
  );
}

async function renderSettings() {
  await loadLookupData(["locations"]);
  const company = await api("/api/company");
  pageWrap().innerHTML = `
    ${pageHeader("configuracoes", "Dados da empresa, locais de estoque e bases para integrações futuras.")}
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head"><h3>Empresa</h3></div>
        <div class="panel-body">
          <form id="company-form" class="form-grid">
            <div class="field full">
              <label>Nome fantasia</label>
              <input name="name" value="${escapeHtml(company.name || "")}" required>
            </div>
            <div class="field full">
              <label>Razão social</label>
              <input name="legal_name" value="${escapeHtml(company.legal_name || "")}">
            </div>
            <div class="field">
              <label>CNPJ</label>
              <input name="cnpj" value="${escapeHtml(company.cnpj || "")}">
            </div>
            <div class="field">
              <label>E-mail</label>
              <input name="email" type="email" value="${escapeHtml(company.email || "")}">
            </div>
            <div class="field">
              <label>Telefone</label>
              <input name="phone" value="${escapeHtml(company.phone || "")}">
            </div>
            <div class="field">
              <label>CEP</label>
              <input name="zipcode" value="${escapeHtml(company.zipcode || "")}">
            </div>
            <div class="field full">
              <label>Endereço</label>
              <input name="address" value="${escapeHtml(company.address || "")}">
            </div>
            <div class="field">
              <label>Cidade</label>
              <input name="city" value="${escapeHtml(company.city || "")}">
            </div>
            <div class="field">
              <label>UF</label>
              <input name="state" value="${escapeHtml(company.state || "")}" maxlength="2">
            </div>
            <div class="field full">
              <button class="btn primary" type="submit"><i class="fa-solid fa-floppy-disk"></i> Salvar empresa</button>
            </div>
          </form>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h3>Locais de estoque</h3>
          <button class="btn sm ghost" id="new-location"><i class="fa-solid fa-plus"></i> Adicionar</button>
        </div>
        <div class="panel-body">
          ${locationsTable(MovStok.state.cache.locations)}
        </div>
      </section>
    </div>
    <section class="panel">
      <div class="panel-head"><h3>Preparação técnica</h3></div>
      <div class="panel-body">
        <table class="data-table">
          <tbody>
            <tr>
              <td><strong>Pagamentos e planos</strong><div class="text-muted">Estrutura multiempresa, usuários, perfis e configuração por ambiente já separadas para integração posterior.</div></td>
              <td>${statusBadge("ready", { ready: { label: "Base pronta", cls: "info" } })}</td>
            </tr>
            <tr>
              <td><strong>Aplicativo mobile</strong><div class="text-muted">APIs REST autenticadas e rotas por módulo estão disponíveis para consumo por app.</div></td>
              <td>${statusBadge("ready", { ready: { label: "API pronta", cls: "info" } })}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `;

  $("#company-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/company", { method: "PUT", body: getFormData(event.currentTarget) });
      toast("Empresa atualizada");
      renderSettings();
    } catch (error) {
      toast("Erro ao salvar empresa", error.message, "danger");
    }
  });
  $("#new-location").addEventListener("click", openLocationModal);
}

function locationsTable(items) {
  if (!items.length) {
    return emptyState("fa-location-dot", "Nenhum local", "Cadastre depósitos, almoxarifados ou endereços internos.");
  }
  return `
    <table class="data-table">
      <thead><tr><th>Código</th><th>Local</th><th>Status</th></tr></thead>
      <tbody>
        ${items.map((l) => `
          <tr>
            <td class="mono">${escapeHtml(l.code)}</td>
            <td><strong>${escapeHtml(l.name)}</strong><div class="text-muted">${escapeHtml(l.description || "")}</div></td>
            <td>${activeBadge(l.active)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function openLocationModal() {
  openModal({
    title: "Novo local de estoque",
    body: `
      <form id="location-form" class="form-grid">
        <div class="field">
          <label>Código</label>
          <input name="code" required>
        </div>
        <div class="field">
          <label>Nome</label>
          <input name="name" required>
        </div>
        <div class="field full">
          <label>Descrição</label>
          <textarea name="description"></textarea>
        </div>
      </form>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="location-form">Salvar</button>
    `,
  });
  $("#location-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/locations", { method: "POST", body: getFormData(event.currentTarget) });
      closeModal();
      toast("Local cadastrado");
      renderSettings();
    } catch (error) {
      toast("Erro ao salvar local", error.message, "danger");
    }
  });
}

function bindSearch(selector, callback) {
  const input = $(selector);
  let timer = null;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => callback(input.value.trim()), 300);
  });
}

function bindRowActions(actions) {
  const root = pageWrap();
  root._rowActions = actions;
  if (root._rowActionsBound) return;
  root._rowActionsBound = true;
  root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action][data-id]");
    if (!button) return;
    const action = root._rowActions?.[button.dataset.action];
    if (!action) return;
    action(Number(button.dataset.id));
  });
}

async function loadNotifications() {
  if (!MovStok.state.user) return;
  try {
    const data = await api("/api/notifications");
    const count = $("#notif-count");
    count.textContent = data.unread || 0;
    count.classList.toggle("show", Number(data.unread || 0) > 0);
    $("#notif-list").innerHTML = notificationItems(data.items || []);
  } catch {
    $("#notif-list").innerHTML = emptyState("fa-bell-slash", "Notificações indisponíveis", "Tente novamente em alguns instantes.");
  }
}

function notificationItems(items) {
  if (!items.length) {
    return emptyState("fa-bell", "Sem notificações", "Alertas operacionais aparecerão aqui.");
  }
  return items.map((n) => `
    <div class="notif-item ${escapeHtml(n.type)} ${n.read ? "" : "unread"}" data-notif-id="${n.id}">
      <div class="ni-icon"><i class="fa-solid ${n.type === "warning" ? "fa-triangle-exclamation" : "fa-circle-info"}"></i></div>
      <div class="ni-body">
        <strong>${escapeHtml(n.title)}</strong>
        <p>${escapeHtml(n.message || "")}</p>
        <small>${fmtDate(n.created_at)}</small>
      </div>
    </div>
  `).join("");
}

function openRegisterModal() {
  openModal({
    title: "Criar Conta",
    body: `
      <form id="register-form" class="form-grid one">
        <div class="field full">
          <label>Seu Nome</label>
          <input name="name" required placeholder="Como quer ser chamado"/>
        </div>
        <div class="field full">
          <label>Nome da Empresa</label>
          <input name="company_name" required placeholder="Ex: Minha Loja Ltda"/>
        </div>
        <div class="field full">
          <label>E-mail</label>
          <input type="email" name="email" required placeholder="seu@email.com"/>
        </div>
        <div class="field full">
          <label>Telefone</label>
          <input name="phone" placeholder="(00) 00000-0000"/>
        </div>
        <div class="field full">
          <label>Senha</label>
          <input type="password" name="password" required minlength="6" placeholder="Mínimo 6 caracteres"/>
        </div>
        <div class="field full">
          <label>Confirmar Senha</label>
          <input type="password" name="confirm_password" required minlength="6" placeholder="Repita sua senha"/>
        </div>
        <div class="form-message full" id="register-feedback" role="status"></div>
      </form>
      <p class="text-muted" style="font-size: 12px; margin-top: 15px">
        Ao criar conta, você concorda com nossos <a href="javascript:MovStok.UI.showTerms()">Termos de Uso</a>.</p>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="register-form" id="register-submit">
        <i class="fa-solid fa-user-plus"></i> Criar minha conta
      </button>
    `,
  });

  $("#register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("#register-submit");
    const feedback = $("#register-feedback");
    const formData = getFormData(event.currentTarget);

    if (formData.password !== formData.confirm_password) {
      feedback.className = "form-message full error";
      return feedback.textContent = "As senhas não conferem.";
    }

    // UX: Limpeza e Normalização
    formData.name = formData.name?.trim();
    formData.company_name = formData.company_name?.trim();
    formData.email = formData.email?.trim().toLowerCase();

    // Segurança: Impedir clique duplo
    feedback.className = "form-message full";
    feedback.textContent = "";
    button.disabled = true;
    button.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Criando conta...`;

    try {
      await api("/api/auth/register", { method: "POST", body: formData });
      toast("Bem-vindo!", "Sua conta foi criada e você já está logado.");
      
      // Login Automático: Atualiza a sessão e navega para o dashboard
      await checkSession();
      navigate("dashboard", true);
      closeModal();
    } catch (error) {
      feedback.classList.add("error");
      feedback.textContent = error.message;
    } finally {
      button.disabled = false;
      button.innerHTML = `<i class="fa-solid fa-user-plus"></i> Criar minha conta`;
    }
  });
}

function openForgotPasswordModal() {
  const email = $("#login-email")?.value?.trim() || "";
  openModal({
    title: "Recuperar senha",
    body: `
      <form id="forgot-form" class="form-grid one">
        <div class="field full">
          <label>E-mail corporativo</label>
          <input type="email" name="email" value="${escapeHtml(email)}" required placeholder="usuario@empresa.com"/>
        </div>
        <div class="form-message full" id="forgot-feedback" role="status"></div>
      </form>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="forgot-form" id="forgot-submit">
        <i class="fa-solid fa-paper-plane"></i> Enviar instruções
      </button>
    `,
  });

  $("#forgot-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("#forgot-submit");
    const feedback = $("#forgot-feedback");
    feedback.className = "form-message full";
    feedback.textContent = "";
    button.disabled = true;
    button.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Enviando...`;
    try {
      const data = await api("/api/auth/forgot-password", {
        method: "POST",
        body: getFormData(event.currentTarget),
      });
      feedback.classList.add("success");
      feedback.textContent = data.message || "Solicitação registrada com sucesso.";
      toast("Solicitação enviada", "Verifique as instruções de recuperação.");
    } catch (error) {
      feedback.classList.add("error");
      feedback.textContent = error.message;
    } finally {
      button.disabled = false;
      button.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Enviar instruções`;
    }
  });
}

function openResetPasswordModal(token) {
  openModal({
    title: "Definir nova senha",
    body: `
      <form id="reset-p-form" class="form-grid one">
        <input type="hidden" name="token" value="${escapeHtml(token)}"/>
        <div class="field full">
          <label>Nova Senha</label>
          <input type="password" name="password" required minlength="6" placeholder="Mínimo 6 caracteres"/>
        </div>
        <div class="field full">
          <label>Confirmar Nova Senha</label>
          <input type="password" name="confirm_password" required minlength="6" placeholder="Repita a nova senha"/>
        </div>
        <div class="form-message full" id="reset-feedback"></div>
      </form>
    `,
    footer: `<button class="btn primary" type="submit" form="reset-p-form" id="reset-submit">Alterar Senha</button>`
  });

  $("#reset-p-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#reset-submit");
    const fb = $("#reset-feedback");
    const data = getFormData(e.currentTarget);

    if (data.password !== data.confirm_password) {
      fb.className = "form-message full error";
      return fb.textContent = "As senhas não conferem.";
    }

    btn.disabled = true;
    btn.textContent = "Processando...";
    
    try {
      await api("/api/auth/reset-password", { method: "POST", body: data });
      toast("Sucesso", "Sua senha foi atualizada. Agora você pode entrar.");
      closeModal();
      history.replaceState({}, "", "/login"); // Limpa o token da URL
    } catch (err) {
      fb.className = "form-message full error";
      fb.textContent = err.message;
      btn.disabled = false;
      btn.textContent = "Alterar Senha";
    }
  });
}

function openChangePasswordModal() {
  openModal({
    title: "Trocar senha",
    body: `
      <form id="password-form" class="form-grid">
        <div class="field full">
          <label>Senha atual</label>
          <input name="current_password" type="password" required>
        </div>
        <div class="field full">
          <label>Nova senha</label>
          <input name="new_password" type="password" required minlength="6">
        </div>
      </form>
    `,
    footer: `
      <button class="btn ghost" type="button" data-modal-close>Cancelar</button>
      <button class="btn primary" type="submit" form="password-form">Atualizar senha</button>
    `,
  });
  $("#password-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/auth/change-password", {
        method: "POST",
        body: getFormData(event.currentTarget),
      });
      closeModal();
      toast("Senha alterada");
    } catch (error) {
      toast("Erro ao trocar senha", error.message, "danger");
    }
  });
}

function bindShellEvents() {
  const sidebar = $("#sidebar");
  const sidebarBackdrop = $("#sidebar-backdrop");
  const closeSidebarDrawer = () => {
    sidebar.classList.remove("show-mobile");
    sidebarBackdrop?.classList.remove("show");
  };

  // Efeito Mostrar/Ocultar Senha
  $("#login-show-password")?.addEventListener("change", (event) => {
    $("#login-password").type = event.currentTarget.checked ? "text" : "password";
  });

  

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector(".login-btn");
    const btnLabel = button.querySelector(".btn-label");
    const error = $("#login-error");
    error.textContent = "";
    button.disabled = true;
    const originalLabel = btnLabel.innerHTML;
    btnLabel.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Autenticando...`;

    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: {
          email: $("#login-email").value,
          password: $("#login-password").value,
          remember: $("#login-remember").checked,
        },
      });
      MovStok.state.user = data.user;
      await checkSession();
      navigate(pageFromPath(), true);
      toast("Bem-vindo", "Sessão iniciada com sucesso.");
    } catch (err) {
      error.textContent = err.message;
      btnLabel.innerHTML = originalLabel;
    } finally {
      button.disabled = false;
    }
  });

  $("#forgot-password")?.addEventListener("click", openForgotPasswordModal);

  const optionsToggle = $("#login-options-toggle");
  const optionsPanel = $("#login-options-panel");
  if (optionsToggle && optionsPanel) {
    optionsToggle.addEventListener("click", () => {
      const isOpen = optionsToggle.getAttribute("aria-expanded") === "true";
      optionsToggle.setAttribute("aria-expanded", String(!isOpen));
      optionsPanel.hidden = isOpen;
    });
  }

  $("#register-link")?.addEventListener("click", openRegisterModal);

  // Fallback para telas antigas que ainda não tenham o botão no HTML.
  const forgotBtn = $("#forgot-password");
  if (forgotBtn && !$("#register-link")) {
    forgotBtn.insertAdjacentHTML('afterend', `
      <span class="text-muted" style="margin: 0 8px">|</span>
      <a href="javascript:void(0)" id="register-link" class="text-primary" style="font-weight:600">Criar Conta</a>
    `);
    $("#register-link").addEventListener("click", openRegisterModal);
  }

  $all(".menu-item").forEach((item) => {
    item.addEventListener("click", () => {
      closeSidebarDrawer();
      navigate(item.dataset.page);
    });
  });

  $("#sidebar-toggle").addEventListener("click", () => {
    $("#sidebar").classList.toggle("collapsed");
  });

  $("#mobile-menu").addEventListener("click", () => {
    sidebar.classList.toggle("show-mobile");
    sidebarBackdrop?.classList.toggle("show", sidebar.classList.contains("show-mobile"));
  });

  sidebarBackdrop?.addEventListener("click", closeSidebarDrawer);

  $("#user-box").addEventListener("click", (event) => {
    event.stopPropagation();
    $("#user-menu").classList.toggle("show");
  });

  document.addEventListener("click", () => {
    $("#user-menu").classList.remove("show");
    $("#notif-drawer").classList.remove("show");
  });

  $("#user-menu").addEventListener("click", async (event) => {
    const item = event.target.closest("[data-action]");
    if (!item) return;
    event.stopPropagation();
    const action = item.dataset.action;
    $("#user-menu").classList.remove("show");
    if (action === "logout") {
      await api("/api/auth/logout", { method: "POST" });
      toast("Sessão encerrada");
      showAuth();
    } else if (action === "settings") {
      navigate("configuracoes");
    } else if (action === "change-password") {
      openChangePasswordModal();
    } else if (action === "profile") {
      openModal({
        title: "Meu perfil",
        body: `
          <table class="data-table">
            <tbody>
              <tr><td>Nome</td><td><strong>${escapeHtml(MovStok.state.user?.name)}</strong></td></tr>
              <tr><td>E-mail</td><td>${escapeHtml(MovStok.state.user?.email)}</td></tr>
              <tr><td>Perfil</td><td>${escapeHtml(roleLabel(MovStok.state.user?.role))}</td></tr>
              <tr><td>Status</td><td>${userStatusBadge(MovStok.state.user?.status)}</td></tr>
            </tbody>
          </table>
        `,
        footer: `<button class="btn primary" type="button" data-modal-close>Fechar</button>`,
      });
    }
  });

  $("#notif-btn").addEventListener("click", (event) => {
    event.stopPropagation();
    $("#notif-drawer").classList.toggle("show");
  });

  $("#notif-drawer").addEventListener("click", (event) => {
    event.stopPropagation();
    const item = event.target.closest("[data-notif-id]");
    if (!item) return;
    api(`/api/notifications/${item.dataset.notifId}/read`, { method: "POST" })
      .then(loadNotifications)
      .catch(() => {});
  });

  $("#notif-readall").addEventListener("click", () => {
    api("/api/notifications/read-all", { method: "POST" })
      .then(loadNotifications)
      .catch((error) => toast("Erro nas notificações", error.message, "danger"));
  });

  $("#global-search").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    navigate("produtos");
    setTimeout(() => {
      renderProducts({ search: event.currentTarget.value.trim() });
    }, 0);
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      $("#global-search").focus();
    }
    if (event.key === "Escape") {
      closeModal();
      closeSidebarDrawer();
    }
  });

  window.addEventListener("popstate", () => renderPage(pageFromPath()));
}

MovStok.UI.showHelp = () => {
  openModal({
    title: "Central de Ajuda",
    body: `<p>Para suporte rápido, utilize o atalho <strong>Ctrl + K</strong> para pesquisar produtos ou acesse o módulo de <strong>Atividades</strong> para auditoria.</p>`,
    footer: `<button class="btn primary" data-modal-close>Entendido</button>`
  });
};

MovStok.UI.showSupport = () => {
  openModal({
    title: "Contato com Suporte",
    body: `<p>E-mail: suporte@movstok.com.br<br>WhatsApp: (11) 99999-9999<br>Atendimento de Segunda a Sexta, das 08h às 18h.</p>`,
    footer: `<button class="btn primary" data-modal-close>Fechar</button>`
  });
};

MovStok.UI.showTerms = () => {
  openModal({
    title: "Termos de Uso",
    body: `<div style="font-size:13px"><p>O MovStok ERP é uma ferramenta de gestão. O usuário é responsável pela veracidade dos dados inseridos e pela segurança de sua senha.</p></div>`,
    footer: `<button class="btn primary" data-modal-close>Fechar</button>`
  });
};

MovStok.UI.showPrivacy = () => {
  openModal({
    title: "Política de Privacidade",
    body: `<div style="font-size:13px"><p>Seus dados são criptografados e não são compartilhados com terceiros. Utilizamos cookies apenas para manter sua sessão ativa.</p></div>`,
    footer: `<button class="btn primary" data-modal-close>Fechar</button>`
  });
};

async function boot() {
  // UX: Atualiza o ano no rodapé automaticamente
  $("#auth-year").textContent = new Date().getFullYear();
  
  bindShellEvents();

  // Institucional: Bind de links do rodapé e login
  $("#btn-help")?.addEventListener("click", MovStok.UI.showHelp);
  $("#btn-support")?.addEventListener("click", MovStok.UI.showSupport);
  $("#btn-terms")?.addEventListener("click", MovStok.UI.showTerms);
  $("#btn-privacy")?.addEventListener("click", MovStok.UI.showPrivacy);

  // Recuperação de Senha: Checa se há um token de reset na URL
  const urlParams = new URLSearchParams(window.location.search);
  const resetToken = urlParams.get('reset_token');
  if (resetToken) {
    setTimeout(() => openResetPasswordModal(resetToken), 500);
    return; // Aguarda o reset antes de tentar logar
  }

  try {
    if (await checkSession()) {
      navigate(pageFromPath(), true);
    }
  } catch {
    showAuth();
  }
}

document.addEventListener("DOMContentLoaded", boot);
