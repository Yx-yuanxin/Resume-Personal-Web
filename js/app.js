/* ============================================================
 * 应用核心：API 层（LIVE/演示自动切换）+ Tab 路由 + 公共工具
 * ============================================================ */
(function () {
  const CFG = window.APP_CONFIG;

  /* ---------------- API 层 ---------------- */
  const API = {
    mode: "demo", // "live" | "demo"

    async call(path, options) {
      const opts = options || {};
      const method = (opts.method || "GET").toUpperCase();
      if (this.mode === "demo") return window.MockAPI.handle(path, method, opts.body || {});

      const url = CFG.apiBase + path;
      const fetchOpts = { method, headers: {} };
      if (opts.formData) {
        fetchOpts.body = opts.formData; // 浏览器自动设置 multipart 边界
      } else if (opts.body) {
        fetchOpts.headers["Content-Type"] = "application/json";
        fetchOpts.body = JSON.stringify(opts.body);
      }

      const ctrl = new AbortController();
      fetchOpts.signal = ctrl.signal;
      const timer = setTimeout(() => ctrl.abort(), CFG.requestTimeout);

      try {
        const resp = await fetch(url, fetchOpts);
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(data.detail || ("HTTP " + resp.status));
        }
        return data;
      } finally {
        clearTimeout(timer);
      }
    },

    async detectMode() {
      if (CFG.forceDemo) { this.mode = "demo"; return this.mode; }
      try {
        const ctrl = new AbortController();
        setTimeout(() => ctrl.abort(), 3000);
        const resp = await fetch(CFG.apiBase + "/api/health", { signal: ctrl.signal });
        const data = await resp.json();
        this.mode = data.status === "ok" ? "live" : "demo";
      } catch (e) {
        this.mode = "demo";
      }
      return this.mode;
    }
  };
  window.API = API;

  /* ---------------- 公共工具 ---------------- */
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** 轻量 markdown：**加粗** / 列表行 / 空行分段 */
  function md(text) {
    const lines = esc(text).split("\n");
    return lines.map((line) => {
      if (!line.trim()) return "<br>";
      line = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      if (/^\s*[-·]\s+/.test(line)) {
        return '<div style="padding-left:14px">' + line + "</div>";
      }
      return "<div>" + line + "</div>";
    }).join("");
  }

  let toastTimer = null;
  function toast(msg, ms) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, ms || 2400);
  }

  function confirmDialog(msg) { return window.confirm(msg); }

  window.Utils = { $, $$, esc, md, toast, confirmDialog };

  /* ---------------- Tab 路由 ---------------- */
  function switchTab(tabId) {
    $$(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabId));
    $$(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + tabId));
    // 懒刷新：切到对应 Tab 时刷新其数据
    const hooks = { upload: "UploadModule", wiki: "WikiModule", collect: "CollectModule" };
    if (hooks[tabId] && window[hooks[tabId]]) window[hooks[tabId]].refresh();
  }

  /* ---------------- 启动 ---------------- */
  async function init() {
    $$(".tab-btn").forEach((b) =>
      b.addEventListener("click", () => switchTab(b.dataset.tab)));

    const mode = await API.detectMode();
    const badge = $("#modeBadge");
    if (mode === "live") {
      badge.classList.add("live");
      badge.innerHTML = '<span class="dot"></span>已连接后端服务';
    } else {
      badge.classList.add("demo");
      badge.innerHTML = '<span class="dot"></span>演示模式（内置示例数据）';
    }

    // 各模块初始化
    window.ChatModule.init();
    window.UploadModule.init();
    window.WikiModule.init();
    window.CollectModule.init();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
