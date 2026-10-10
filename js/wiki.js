/* ============================================================
 * Tab3 LLM-Wiki 知识库：统计卡 / 筛选 / 条目卡片 / 审核编辑删除
 * ============================================================ */
(function () {
  const { $, $$, esc, toast, confirmDialog } = window.Utils;
  let statusFilter = "";
  let sourceFilter = "";

  function init() {
    $("#wikiStatusFilter").addEventListener("click", (e) => {
      const btn = e.target.closest(".seg");
      if (!btn) return;
      $$("#wikiStatusFilter .seg").forEach((s) => s.classList.remove("active"));
      btn.classList.add("active");
      statusFilter = btn.dataset.v;
      refresh();
    });
    $("#wikiSourceFilter").addEventListener("click", (e) => {
      const btn = e.target.closest(".seg");
      if (!btn) return;
      $$("#wikiSourceFilter .seg").forEach((s) => s.classList.remove("active"));
      btn.classList.add("active");
      sourceFilter = btn.dataset.v;
      refresh();
    });

    // 编辑弹窗
    $("#wikiEditCancel").addEventListener("click", () => { $("#wikiModal").hidden = true; });
    $("#wikiEditSave").addEventListener("click", saveEdit);
  }

  let editingId = null;

  async function refresh() {
    const listEl = $("#wikiList");
    listEl.innerHTML = '<div class="table-empty">加载中…</div>';

    try {
      const query = [];
      if (statusFilter) query.push("status=" + encodeURIComponent(statusFilter));
      if (sourceFilter) query.push("source_type=" + encodeURIComponent(sourceFilter));
      const qs = query.length ? "?" + query.join("&") : "";
      const entries = await window.API.call("/api/wiki" + qs);

      // 统计（拉全量再算，演示级简化）
      const all = entries.length === 0 || (statusFilter || sourceFilter)
        ? await window.API.call("/api/wiki")
        : entries;
      renderStats(all);

      if (!entries.length) {
        listEl.innerHTML = '<div class="table-empty">暂无符合条件的知识条目。<br>去「对话问答」提问，系统会自动沉淀知识候选。</div>';
        return;
      }

      listEl.innerHTML = entries.map((e) => renderCard(e)).join("");
      bindActions(listEl);
    } catch (err) {
      listEl.innerHTML = '<div class="table-empty">加载失败：' + esc(err.message) + "</div>";
    }
  }

  function renderStats(all) {
    $("#statTotal").textContent = all.length;
    $("#statPending").textContent = all.filter((e) => e.status === "待审核").length;
    $("#statActive").textContent = all.filter((e) => e.status === "已生效").length;
    $("#statInternal").textContent = all.filter((e) => e.source_type === "internal").length;
    $("#statExternal").textContent = all.filter((e) => e.source_type === "external").length;
  }

  function renderCard(e) {
    const isPending = e.status === "待审核";
    const srcTag = e.source_type === "internal"
      ? '<span class="tag internal">🔒 内部</span>'
      : '<span class="tag external">🌐 外部</span>';
    const statusTag = isPending
      ? '<span class="tag pending">⏳ 待审核</span>'
      : '<span class="tag active">✅ 已生效</span>';

    let actions = "";
    if (isPending) {
      actions =
        '<button class="btn-ghost btn-approve" data-act="approve" data-id="' + e.id + '">✔ 通过生效</button>' +
        '<button class="btn-ghost" data-act="reject" data-id="' + e.id + '">✖ 驳回</button>' +
        '<button class="btn-ghost btn-plain" data-act="edit" data-id="' + e.id + '">✎ 编辑</button>';
    } else {
      actions =
        '<button class="btn-ghost btn-plain" data-act="edit" data-id="' + e.id + '">✎ 编辑</button>' +
        '<button class="btn-ghost" data-act="delete" data-id="' + e.id + '">🗑 删除</button>';
    }

    return (
      '<div class="wiki-card">' +
      '<div class="wiki-card-top"><h4>' + esc(e.knowledge_title) + "</h4>" +
      '<div class="wiki-tags">' + srcTag + statusTag + "</div></div>" +
      '<div class="wiki-content">' + esc(e.knowledge_content) + "</div>" +
      '<div class="wiki-meta">' +
      "<span>📎 来源：" + esc(e.source_reference) + "</span>" +
      "<span>🕒 " + esc(e.create_time) + "</span>" +
      (e.approve_time ? "<span>✔ 生效于 " + esc(e.approve_time) + "</span>" : "") +
      "</div>" +
      '<div class="wiki-actions">' + actions + "</div>" +
      "</div>"
    );
  }

  function bindActions(listEl) {
    listEl.querySelectorAll("[data-act]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        const act = btn.dataset.act;
        try {
          if (act === "approve") {
            await window.API.call("/api/wiki/" + id + "/approve", { method: "POST" });
            toast("✅ 已生效：该条目将优先参与问答检索");
          } else if (act === "reject") {
            await window.API.call("/api/wiki/" + id + "/reject", { method: "POST" });
            toast("已驳回（可编辑后重新审核）");
          } else if (act === "delete") {
            if (!confirmDialog("确认删除该知识条目？")) return;
            await window.API.call("/api/wiki/" + id, { method: "DELETE" });
            toast("已删除");
          } else if (act === "edit") {
            openEdit(id);
            return;
          }
          refresh();
        } catch (err) { toast("操作失败：" + err.message); }
      });
    });
  }

  async function openEdit(id) {
    const all = await window.API.call("/api/wiki");
    const entry = all.find((e) => e.id === id);
    if (!entry) return toast("条目不存在");
    editingId = id;
    $("#wikiModalTitle").textContent = "编辑知识条目（" + entry.status + "）";
    $("#wikiEditTitle").value = entry.knowledge_title;
    $("#wikiEditContent").value = entry.knowledge_content;
    $("#wikiEditActivate").checked = false;
    $("#wikiModal").hidden = false;
  }

  async function saveEdit() {
    const title = $("#wikiEditTitle").value.trim();
    const content = $("#wikiEditContent").value.trim();
    if (!title || !content) return toast("标题与内容不能为空");
    try {
      await window.API.call("/api/wiki/" + editingId, {
        method: "PUT",
        body: {
          knowledge_title: title,
          knowledge_content: content,
          activate: $("#wikiEditActivate").checked
        }
      });
      $("#wikiModal").hidden = true;
      toast("✅ 已保存");
      refresh();
    } catch (err) { toast("保存失败：" + err.message); }
  }

  window.WikiModule = { init, refresh };
})();
