/* ============================================================
 * Tab1 对话问答：聊天流 / 溯源卡片 / 外部提示 / Wiki 沉淀提示
 * ============================================================ */
(function () {
  const { $, $$, md, esc, toast } = window.Utils;

  function init() {
    const input = $("#chatInput");
    const sendBtn = $("#sendBtn");

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
    });
    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 120) + "px";
    });
    $("#clearChat").addEventListener("click", () => {
      $("#chatStream").innerHTML = "";
      $("#chatEmpty") && $("#chatStream").appendChild($("#chatEmpty"));
    });

    $$(".quick-q").forEach((b) =>
      b.addEventListener("click", () => {
        input.value = b.dataset.q;
        send();
      }));
  }

  async function send() {
    const input = $("#chatInput");
    const question = input.value.trim();
    if (!question) return toast("请输入问题");
    if (input.parentElement.querySelector(".typing")) return; // 防止连击

    const scope = $("#chatScope").value;
    input.value = "";
    input.style.height = "auto";

    appendUser(question);
    const typingEl = appendTyping();

    let result;
    try {
      result = await window.API.call("/api/chat", {
        method: "POST", body: { question, scope }
      });
    } catch (err) {
      typingEl.remove();
      appendBot({
        answer: "请求失败：" + esc(err.message),
        sources: [], no_match: false, external_disclaimer: "",
        wiki_candidate: null, wiki_hit: false, compliance_note: "网络异常"
      });
      return;
    }
    typingEl.remove();
    appendBot(result);
  }

  /* ---------------- 渲染 ---------------- */
  function appendUser(text) {
    hideEmpty();
    const stream = $("#chatStream");
    const div = document.createElement("div");
    div.className = "msg user";
    div.innerHTML = '<div class="avatar">我</div><div class="bubble">' + esc(text) + "</div>";
    stream.appendChild(div);
    stream.scrollTop = stream.scrollHeight;
  }

  function appendTyping() {
    const stream = $("#chatStream");
    const div = document.createElement("div");
    div.className = "msg bot";
    div.innerHTML = '<div class="avatar">东</div><div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>';
    stream.appendChild(div);
    stream.scrollTop = stream.scrollHeight;
    return div;
  }

  function appendBot(r) {
    hideEmpty();
    const stream = $("#chatStream");
    const div = document.createElement("div");
    div.className = "msg bot";

    let html = '<div class="avatar">东</div><div class="bubble">';
    if (r.wiki_hit) html += '<div class="wiki-hit-badge">⚡ 已生效Wiki知识命中（优先检索）</div>';
    html += '<div class="answer-text' + (r.no_match ? " dim" : "") + '">' + md(r.answer) + "</div>";

    // 来源溯源（硬性要求：每条回答必须携带）
    if (r.sources && r.sources.length) {
      html += '<div class="sources"><div class="sources-title">📎 来源溯源（' + r.sources.length + "）</div>";
      r.sources.forEach((s) => {
        const isExt = s.type === "external";
        const kindLabel = s.kind === "wiki" ? "Wiki" : "文档";
        html +=
          '<div class="source-item ' + (isExt ? "tag-external" : "tag-internal") + (s.kind === "wiki" ? " kind-wiki" : "") + '">' +
          '<span class="tag ' + (isExt ? "external" : "internal") + '">' + (isExt ? "🌐 公开网络" : "🔒 内部制度") + "</span>" +
          '<span class="tag pending" style="font-size:11px">' + kindLabel + "</span>" +
          '<span class="ref" title="' + esc(s.snippet || "") + '">' + esc(s.ref) + "</span>" +
          '<span class="score">相关度 ' + Math.round((s.score || 0) * 100) + "%</span>" +
          "</div>";
      });
      html += "</div>";
    }

    // 外部信息强制提示（硬性要求）
    if (r.external_disclaimer) {
      html += '<div class="external-disclaimer">⚠️ ' + esc(r.external_disclaimer) + "</div>";
    }

    // LLM-Wiki 知识沉淀提示
    if (r.wiki_candidate) {
      const c = r.wiki_candidate;
      html +=
        '<div class="wiki-candidate-note"><span>✨ 本轮问答已沉淀知识条目《' + esc(c.knowledge_title) +
        '》（' + esc(c.status) + "）</span>" +
        '<button data-candidate="1">去审核 →</button></div>';
    }

    if (r.compliance_note) {
      html += '<div class="compliance-note">✔ ' + esc(r.compliance_note) + "</div>";
    }
    html += "</div>";

    div.innerHTML = html;

    // "去审核" → 跳转 Wiki Tab
    const goBtn = div.querySelector("[data-candidate]");
    if (goBtn) {
      goBtn.addEventListener("click", () => {
        document.querySelector('[data-tab="wiki"]').click();
        toast("该条目在列表顶部，可执行审核操作");
      });
    }

    stream.appendChild(div);
    stream.scrollTop = stream.scrollHeight;
  }

  function hideEmpty() {
    const empty = $("#chatEmpty");
    if (empty) empty.style.display = "none";
  }

  window.ChatModule = { init };
})();
