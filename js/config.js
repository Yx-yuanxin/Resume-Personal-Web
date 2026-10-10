/* 全局配置：API 地址与模式探测开关 */
(function () {
  window.APP_CONFIG = {
    // 后端地址；一体化运行（python main.py 托管前端）时同源，留空即可
    apiBase: window.APP_API_BASE || "",
    // 探测 /api/health 失败 → 自动进入演示模式（内置 Mock 数据，GitHub Pages 可用）
    forceDemo: false,
    requestTimeout: 15000
  };
})();
