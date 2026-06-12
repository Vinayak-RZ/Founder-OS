/** Load after deferred GSAP / Cytoscape — init motion + redraw graphs. */
(function () {
  function run() {
    if (window.FOSMotion) {
      FOSMotion.init?.();
      FOSMotion.runShell?.();
    }
    if (typeof drawGraphs === "function") drawGraphs();
  }
  if (document.readyState === "complete") run();
  else window.addEventListener("load", run);
})();
