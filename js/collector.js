/* ============================================================
 * Tab4 外部信息采集：关键词/URL 采集 + 结果展示 + 外部库清单
 * ============================================================ */
(function () {
  const { $, esc, toast } = window.Utils;

  function init() {
    $("#collectBtn").addEventListener("click", collect);
    $("#refreshExternalDocs").addEventListener("click", refreshExternalDocs);
    refreshExternalDocs();
  }

  async function collect() {
    const keywords = $("#collectKeywords").value.trim();
    const urlText = $("#collectUrls").value.trim();
    const maxPages = parseInt($("#collectMaxPages").value, 10) || 5;

    if (!keywords && !urlText) return toast("请输入关键词或提供公开网页 URL");

    const manualUrls = urlText ? urlText.split("\n").map((s) => s.trim()).filter(Boolean) : null;
    if (manualUrls) {
      const bad = manualUrls.find((u) => !/^https?:\/\//i.test(u));
      if (bad) return toast("URL 需以 http/https 开头：" + bad);
    }

    const btn = $("#collectBtn");
    const status = $("#collectStatus");
    btn.disabled = true;
    status.textContent = "🌐 采集进行中（robots 校验 → 抓取 → 登录墙检测 → 清洗入库）…";

    try {
      const data = await window.API.call("/api/collect", {
        method: "POST",
        body: { keywords, max_pages: maxPages, manual_urls: manualUrls }
      });
      renderResults(data);
      const s = data.summary;
      status.innerHTML =
        '采集完成：<span class="status-ok">' + s.collected + " 页入库</span> · " +
        '<span class="status-skip">' + s.skipped + " 页按合规规则跳过</span>";
      refreshExternalDocs();
    } catch (err) {
      status.textContent = "采集失败：" + err.message;
    } finally {
      btn.disabled = false;
    }
  }

  function renderResults(data) {
    const tbody = $("#collectTbody");
    $("#collectResultCount").textContent = data.summary.total + " 页";
    if (!data.results.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="table-empty">未获取到可采集的公开网页</td></tr>';
      return;
    }
    tbody.innerHTML = data.results.map((r) => {
      const isOk = r.status === "已入库";
      const statusTag = isOk
        ? '<span class="tag active">✅ 已入库</span>'
        : '<span class="tag pending">⛔ 跳过</span>';
      return (
        "<tr><td>" + (isOk ? "🌐 " : "") + esc(r.title) + "</td>" +
        '<td class="url-cell" title="' + esc(r.url) + '">' + esc(r.url) + "</td>" +
        "<td>" + statusTag + "</td>" +
        "<td>" + (r.chunks || "-") + "</td>" +
        '<td style="color:var(--text-2)">' + esc(r.reason || "清洗后入库外部公开库，并生成 Wiki 候选条目") + "</td></tr>"
      );
    }).join("");
  }

  async function refreshExternalDocs() {
    const tbody = $("#externalDocsTbody");
    try {
      const docs = await window.API.call("/api/collect/external-docs");
      if (!docs.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="table-empty">暂无资料，请先发起采集</td></tr>';
        return;
      }
      tbody.innerHTML = docs.map((d) =>
        "<tr><td>🌐 " + esc(d.name) + "</td>" +
        "<td>" + d.chunks + " 块</td>" +
        '<td><span class="tag external">外部公开库</span></td>' +
        "<td>" + esc(d.type) + "</td></tr>"
      ).join("");
    } catch (err) {
      tbody.innerHTML = '<tr><td colspan="4" class="table-empty">加载失败：' + esc(err.message) + "</td></tr>";
    }
  }

  window.CollectModule = { init, refresh: refreshExternalDocs };
})();
