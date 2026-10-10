/* ============================================================
 * Tab2 文档上传：拖拽/点选上传 + 内部库文档清单管理
 * ============================================================ */
(function () {
  const { $, esc, toast, confirmDialog } = window.Utils;

  function init() {
    const dz = $("#dropzone");
    const fileInput = $("#fileInput");

    dz.addEventListener("click", () => fileInput.click());
    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("dragover"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("dragover"));
    dz.addEventListener("drop", (e) => {
      e.preventDefault();
      dz.classList.remove("dragover");
      handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener("change", () => {
      handleFiles(fileInput.files);
      fileInput.value = "";
    });

    refresh();
  }

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    for (const file of files) {
      const ext = file.name.split(".").pop().toLowerCase();
      if (!["pdf", "docx", "doc", "txt"].includes(ext)) {
        toast("跳过不支持的文件：" + file.name);
        continue;
      }
      if (file.size > 20 * 1024 * 1024) {
        toast("文件超过 20MB：" + file.name);
        continue;
      }

      try {
        if (window.API.mode === "demo") {
          await window.API.call("/api/documents/upload", {
            method: "POST", body: { fileNames: [file.name] }
          });
        } else {
          const fd = new FormData();
          fd.append("file", file);
          await window.API.call("/api/documents/upload", { method: "POST", formData: fd });
        }
        toast("✅ 《" + file.name + "》已解析入库（内部私有库）");
      } catch (err) {
        toast("❌ 上传失败：" + err.message);
      }
    }
    refresh();
  }

  async function refresh() {
    const tbody = $("#docTbody");
    tbody.innerHTML = '<tr><td colspan="4" class="table-empty">加载中…</td></tr>';
    try {
      const docs = await window.API.call("/api/documents");
      $("#docCount").textContent = docs.length + " 份";
      if (!docs.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="table-empty">暂无文档，请上传内部制度文档</td></tr>';
        return;
      }
      tbody.innerHTML = docs.map((d) =>
        "<tr><td>📄 " + esc(d.name) + "</td>" +
        "<td>" + d.chunks + " 块</td>" +
        '<td><span class="tag internal">🔒 内部私有库</span></td>' +
        '<td><button class="btn-ghost btn-plain" data-del="' + esc(d.name) + '">删除</button></td></tr>'
      ).join("");

      tbody.querySelectorAll("[data-del]").forEach((btn) =>
        btn.addEventListener("click", async () => {
          const name = btn.dataset.del;
          if (!confirmDialog("确认从内部库删除《" + name + "》的全部分块？")) return;
          try {
            await window.API.call("/api/documents/" + encodeURIComponent(name), { method: "DELETE" });
            toast("已删除《" + name + "》");
            refresh();
          } catch (err) { toast("删除失败：" + err.message); }
        }));
    } catch (err) {
      tbody.innerHTML = '<tr><td colspan="4" class="table-empty">加载失败：' + esc(err.message) + "</td></tr>";
    }
  }

  window.UploadModule = { init, refresh };
})();
