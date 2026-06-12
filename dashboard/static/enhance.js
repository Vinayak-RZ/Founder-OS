/** Load after deferred GSAP / Cytoscape — init motion + redraw graphs. */
(function () {
  function run() {
    if (window.FOSMotion) {
      FOSMotion.init?.();
      FOSMotion.runShell?.();
      FOSMotion.ensureContentVisible?.();
    }
    if (typeof drawGraphs === "function") drawGraphs();
    if (typeof drawDashboardCharts === "function" && currentView === "dashboard") {
      try { drawDashboardCharts(); } catch (e) { console.error(e); }
    }
  }
  if (document.readyState === "complete") run();
  else window.addEventListener("load", run);
})();
