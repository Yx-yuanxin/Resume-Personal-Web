/* ============================================================
 * 演示模式 Mock 引擎（GitHub Pages 部署 / 无后端环境使用）
 * 与后端接口签名完全一致：MockAPI.handle(path, method, body)
 * 内置语料与 backend/seed_demo.py 同构，保证演示口径统一。
 * ============================================================ */
(function () {
  let seq = 1000;
  const uid = (p) => p + "_" + Date.now() + "_" + (seq++);
  const now = () => new Date().toLocaleString("zh-CN", { hour12: false });

  /* ---------------- 内置数据（与后端种子数据同构） ---------------- */
  const store = {
    docs: [
      { name: "考勤与休假管理制度.pdf", chunks: 9, store: "internal", type: "内部制度文档" },
      { name: "差旅报销管理制度.pdf", chunks: 8, store: "internal", type: "内部制度文档" },
      { name: "信息安全管理制度.pdf", chunks: 8, store: "internal", type: "内部制度文档" }
    ],
    externalDocs: [
      { name: "2026年弹性退休政策解读（示例公开页面）.html", chunks: 3, store: "external", type: "公开网络采集" },
      { name: "企业数字化管理行业趋势（示例公开报告）.html", chunks: 3, store: "external", type: "公开网络采集" }
    ],
    wiki: [
      {
        id: "wk_seed_1", knowledge_title: "公司标准工作时间",
        knowledge_content: "公司实行标准工时制，周一至周五工作，每日 9:00-12:00、13:30-18:00，共 7.5 小时；9:00 后到岗计迟到，月累计第 4 次起每次扣绩效 50 元。",
        source_type: "internal", source_reference: "考勤与休假管理制度.pdf",
        create_time: "2026-10-08 09:30:00", status: "已生效"
      },
      {
        id: "wk_seed_2", knowledge_title: "出差住宿报销限额",
        knowledge_content: "住宿限额：北上广深每晚上限 600 元，省会及二线城市 450 元，其他城市 350 元；超标部分自理，会议统一安排的凭通知据实报销。",
        source_type: "internal", source_reference: "差旅报销管理制度.pdf",
        create_time: "2026-10-08 09:31:00", status: "已生效"
      }
    ],
    collectHistory: []
  };

  /* ---------------- 语料路由：问题关键词 → 模拟检索命中 ---------------- */
  const ROUTES = [
    {
      keys: ["工作时间", "几点", "上班", "作息", "迟到", "打卡"],
      wikiId: "wk_seed_1",
      answer: "公司实行**标准工时制**：\n\n- 工作日：周一至周五；\n- 每日时间：上午 9:00–12:00，下午 13:30–18:00，合计 7.5 小时；\n- 9:00 后到岗计为迟到，月度累计第 4 次起每次扣减绩效工资 50 元。",
      sources: [
        { type: "internal", kind: "wiki", ref: "公司标准工作时间（已生效Wiki条目）", score: 0.92 },
        { type: "internal", kind: "document", ref: "考勤与休假管理制度.pdf", score: 0.71 }
      ],
      scope: "internal"
    },
    {
      keys: ["住宿", "差旅", "报销", "出差", "交通", "餐补"],
      wikiId: "wk_seed_2",
      answer: "根据《差旅报销管理制度》，出差住宿费限额标准如下：\n\n- 一线城市（北上广深）：每晚上限 **600 元**；\n- 省会及二线城市：每晚上限 **450 元**；\n- 其他城市：每晚上限 **350 元**。\n\n超出限额部分由个人自理；因会议统一安排住宿超标的，凭会议通知据实报销。",
      sources: [
        { type: "internal", kind: "wiki", ref: "出差住宿报销限额（已生效Wiki条目）", score: 0.94 },
        { type: "internal", kind: "document", ref: "差旅报销管理制度.pdf", score: 0.78 }
      ],
      scope: "internal"
    },
    {
      keys: ["年假", "年休假", "事假", "病假", "婚假", "产假", "请假", "休假"],
      answer: "根据《考勤与休假管理制度》请假管理规定：\n\n- **年假**：司龄满 1 年不满 5 年为 5 天，满 5 年不满 10 年为 10 天，满 10 年以上为 15 天，原则上当年使用；\n- **事假**：提前 1 个工作日申请，期间不计薪；\n- **病假**：需二甲及以上医院证明，按当地最低工资 80% 计发；\n- **婚假** 3 天、**产假** 98 天、**陪产假** 15 天。",
      sources: [
        { type: "internal", kind: "document", ref: "考勤与休假管理制度.pdf", score: 0.74 }
      ],
      scope: "internal"
    },
    {
      keys: ["加班", "调休", "加班费"],
      answer: "根据《考勤与休假管理制度》加班管理规定：\n\n- 加班须**提前审批**，未经审批的延时工作不计加班；\n- 工作日加班按 **1.5 倍**时薪计发；\n- 休息日加班优先安排调休；\n- 法定节假日加班按 **3 倍**时薪计发。",
      sources: [
        { type: "internal", kind: "document", ref: "考勤与休假管理制度.pdf", score: 0.7 }
      ],
      scope: "internal"
    },
    {
      keys: ["USB", "u盘", "信息安全", "泄密", "机密", "密级", "锁屏", "外发"],
      answer: "根据《信息安全管理制度》：\n\n- 信息分为**公开 / 内部 / 机密**三级；\n- **USB 存储设备默认禁用**，因工作需要须提交申请开通，开通后使用行为将被审计；\n- 机密级信息（客户数据、财务数据、源代码）外发须部门负责人与信息安全负责人**双重审批**；\n- 离开工位超 30 分钟须锁屏。",
      sources: [
        { type: "internal", kind: "document", ref: "信息安全管理制度.pdf", score: 0.77 }
      ],
      scope: "internal"
    },
    {
      keys: ["退休", "延迟退休", "弹性退休", "养老"],
      answer: "根据公开网络资料：\n\n- 职工达到最低缴费年限后，可自愿选择**弹性提前**或**弹性延迟**退休；\n- 弹性提前：最早可在原法定退休年龄基础上提前不超过 **3 年**，且不得低于原法定退休年龄；\n- 弹性延迟：与单位协商一致后，延迟最长不超过 **3 年**；\n- 政策自 2025 年 1 月 1 日起施行。",
      sources: [
        { type: "external", kind: "document", ref: "2026年弹性退休政策解读（示例公开页面）.html", score: 0.81 }
      ],
      scope: "external"
    },
    {
      keys: ["数字化", "行业", "趋势", "智能问答", "大模型", "落地"],
      answer: "根据公开行业报告：\n\n- 超过 **70%** 的大型企业已部署智能问答类效率工具，制度问答、IT 自助服务、HR 政策查询是落地率最高的三类场景；\n- 采用「LLM + 企业知识库」架构后，问题一次解决率平均从 **42% 提升至 78%**；\n- 监管对 AI 生成内容提出可追溯要求：标注来源、区分内外数据、建立人工审核机制。",
      sources: [
        { type: "external", kind: "document", ref: "企业数字化管理行业趋势（示例公开报告）.html", score: 0.83 }
      ],
      scope: "external"
    }
  ];

  /* ---------------- Mock 接口实现 ---------------- */
  function mockChat(body) {
    const q = body.question || "";
    const route = ROUTES.find((r) => r.keys.some((k) => q.includes(k)));

    // scope 限制检查：仅内部库却命中外部队落 → 无匹配
    if (route && body.scope === "internal" && route.scope === "external") {
      return noMatch("internal");
    }
    if (route && body.scope === "external" && route.scope === "internal") {
      return noMatch("external");
    }
    if (!route) return noMatch("auto");

    const wikiHit = !!route.wikiId && store.wiki.some(
      (w) => w.id === route.wikiId && w.status === "已生效");

    const sources = route.sources.map((s) => ({
      ...s, snippet: route.answer.slice(0, 40) + "…"
    }));

    // LLM-Wiki 沉淀：生成待审核候选条目
    const candidate = {
      id: uid("wk"), knowledge_title: q.replace(/请问|呢|？|\?/g, "").slice(0, 18) || "新知识条目",
      knowledge_content: route.answer.replace(/[*#]/g, "").split("\n").filter(Boolean).join(" ").slice(0, 90) + "…",
      source_type: route.scope === "external" ? "external" : "internal",
      source_reference: route.sources[0].ref, create_time: now(), status: "待审核"
    };
    store.wiki.unshift(candidate);

    return {
      answer: route.answer,
      sources, question_scope: route.scope, no_match: false,
      wiki_hit: wikiHit, wiki_candidate: candidate,
      external_disclaimer: route.scope === "external"
        ? "该信息来源于公开网络，仅供参考，不作为企业内部制度依据" : "",
      compliance_note: "已通过合规检查：来源可溯" + (route.scope === "external" ? "，外部信息已附提示" : "")
    };
  }

  function noMatch(scope) {
    return {
      answer: "暂无相关制度或公开资料。您可以尝试更换关键词，或联系管理员上传相关制度文档后再试。",
      sources: [], question_scope: scope, no_match: true, wiki_hit: false,
      wiki_candidate: null, external_disclaimer: "",
      compliance_note: "未检索到匹配知识，已按合规要求拒绝编造内容"
    };
  }

  const delay = (ms) => new Promise((r) => setTimeout(r, ms));

  /* ---------------- 路由分发（与后端 REST 路径一致） ---------------- */
  window.MockAPI = {
    store,
    async handle(path, method, body) {
      await delay(method === "GET" ? 120 : 600); // 模拟网络与生成耗时

      if (path === "/api/health")
        return {
          status: "ok", app: "东知道", llm_mode: "MOCK",
          internal_store: { chunks: 25, sources: 3 },
          external_store: { chunks: 6, sources: 2 }, wiki: wikiStats()
        };

      if (path === "/api/chat" && method === "POST") return mockChat(body);

      if (path === "/api/documents" && method === "GET") return store.docs;
      if (path.startsWith("/api/documents/upload") && method === "POST") {
        const f = (body && body.fileNames) || ["新制度文档.docx"];
        f.forEach((name) => {
          store.docs = store.docs.filter((d) => d.name !== name);
          store.docs.unshift({ name, chunks: 5 + Math.floor(Math.random() * 6), store: "internal", type: "内部制度文档" });
        });
        return { filename: f.join("、"), chunks: 5, store: "internal", message: "已解析入库（内部私有库）" };
      }
      const delDoc = path.match(/^\/api\/documents\/(.+)$/);
      if (delDoc && method === "DELETE") {
        const name = decodeURIComponent(delDoc[1]);
        store.docs = store.docs.filter((d) => d.name !== name);
        return { message: "已删除" };
      }

      if (path.startsWith("/api/wiki?") || (path === "/api/wiki" && method === "GET")) {
        let list = store.wiki;
        const qs = path.split("?")[1];
        if (qs) {
          const params = new URLSearchParams(qs);
          const st = params.get("status"), ty = params.get("source_type");
          if (st) list = list.filter((w) => w.status === st);
          if (ty) list = list.filter((w) => w.source_type === ty);
        }
        return list;
      }
      if (path === "/api/wiki/stats") return wikiStats();
      const approveM = path.match(/^\/api\/wiki\/([^/]+)\/approve$/);
      if (approveM) {
        const w = store.wiki.find((x) => x.id === approveM[1]);
        if (w) { w.status = "已生效"; w.approve_time = now(); }
        return { entry: w, message: "已生效，将优先参与问答检索" };
      }
      const rejectM = path.match(/^\/api\/wiki\/([^/]+)\/reject$/);
      if (rejectM) {
        const w = store.wiki.find((x) => x.id === rejectM[1]);
        if (w) { w.status = "待审核"; w.rejected = true; }
        return { entry: w, message: "已驳回" };
      }
      const editM = path.match(/^\/api\/wiki\/([^/]+)$/);
      if (editM && method === "PUT") {
        const w = store.wiki.find((x) => x.id === editM[1]);
        if (w) {
          if (body.knowledge_title) w.knowledge_title = body.knowledge_title;
          if (body.knowledge_content) w.knowledge_content = body.knowledge_content;
          if (body.activate) { w.status = "已生效"; w.approve_time = now(); }
        }
        return { entry: w, message: "已保存" };
      }
      if (editM && method === "DELETE") {
        store.wiki = store.wiki.filter((x) => x.id !== editM[1]);
        return { message: "已删除" };
      }

      if (path === "/api/collect" && method === "POST") {
        const kw = (body.keywords || "示例关键词").slice(0, 20);
        const results = [
          { url: "https://example.gov.cn/policy/flexible-retirement", title: `关于「${kw}」的政策解读（公开页面）`, status: "已入库", chunks: 4, reason: "" },
          { url: "https://example-news.com/paywall-article", title: "-", status: "跳过", chunks: 0, reason: "检测到登录墙，按合规要求跳过" },
          { url: "https://example-forum.com/topic/123", title: "-", status: "跳过", chunks: 0, reason: "robots.txt 不允许抓取" }
        ];
        const item = { name: `「${kw}」公开资料（模拟采集）.html`, chunks: 4, store: "external", type: "公开网络采集" };
        store.externalDocs.unshift(item);
        store.wiki.unshift({
          id: uid("wk"), knowledge_title: `「${kw}」公开资料要点`,
          knowledge_content: `关于${kw}的公开网络资料已采集入库，要点详见原文。该信息来源于公开网络，仅供参考。`,
          source_type: "external", source_reference: item.name,
          create_time: now(), status: "待审核"
        });
        const summary = {
          task_id: uid("col"), keywords: kw, total: 3, collected: 1, skipped: 2, time: now()
        };
        store.collectHistory.unshift({ summary, results });
        return { task_id: summary.task_id, results, summary };
      }
      if (path === "/api/collect/history") return store.collectHistory;
      if (path === "/api/collect/external-docs") return store.externalDocs;

      throw new Error("Mock 未实现: " + method + " " + path);
    }
  };

  function wikiStats() {
    return {
      total: store.wiki.length,
      "待审核": store.wiki.filter((w) => w.status === "待审核").length,
      "已生效": store.wiki.filter((w) => w.status === "已生效").length,
      internal: store.wiki.filter((w) => w.source_type === "internal").length,
      external: store.wiki.filter((w) => w.source_type === "external").length
    };
  }
})();
