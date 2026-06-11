/* Cytoscape graph renderer — Stamped Energy / Forge Industrial palette */
window.FOSGraph = (function () {
  const instances = {};

  const PAL = {
    primary: "#f75440",
    secondary: "#051f13",
    tertiary: "#00666b",
    surface: "#ffffff",
    surfaceLow: "#f1f4f0",
    onSurface: "#191c1a",
    onSurfaceVariant: "#5a403c",
    outline: "#8f706b",
    outlineVariant: "#e3beb8",
    inversePrimary: "#ffb4a8",
    inverseSurface: "#2d312e",
  };

  const STYLES = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "text-valign": "bottom",
        "text-halign": "center",
        "text-margin-y": 6,
        "font-size": 10,
        "font-family": "Inter, sans-serif",
        color: PAL.onSurfaceVariant,
        "background-color": PAL.surfaceLow,
        width: 36,
        height: 36,
        "border-width": 2,
        "border-color": PAL.outlineVariant,
      },
    },
    {
      selector: "node[type='founder']",
      style: {
        "background-color": PAL.secondary,
        color: "#fff",
        width: 52,
        height: 52,
        "font-weight": 600,
        "border-color": PAL.secondary,
      },
    },
    {
      selector: "node[type='supervisor']",
      style: {
        "background-color": PAL.primary,
        color: "#fff",
        width: 48,
        height: 48,
        "font-weight": 600,
        "border-color": PAL.primary,
      },
    },
    {
      selector: "node[type='specialist']",
      style: {
        "background-color": PAL.surface,
        "border-color": PAL.secondary,
        width: 44,
        height: 44,
      },
    },
    {
      selector: "node[status='busy']",
      style: {
        "border-width": 3,
        "border-color": PAL.primary,
      },
    },
    {
      selector: "node[type='tool']",
      style: {
        width: 28,
        height: 28,
        "font-size": 8,
        shape: "round-rectangle",
        "background-color": PAL.surface,
        "border-color": PAL.tertiary,
      },
    },
    {
      selector: "node[type='company']",
      style: { "background-color": PAL.tertiary, width: 46, height: 46, color: "#fff" },
    },
    {
      selector: "node[type='world_root']",
      style: {
        "background-color": PAL.secondary,
        "border-color": PAL.primary,
        "border-width": 3,
        width: 56,
        height: 56,
        shape: "round-rectangle",
        color: "#fff",
      },
    },
    {
      selector: "node[type='world_child']",
      style: {
        "background-color": PAL.surface,
        "border-color": PAL.primary,
        "border-width": 2,
        width: 48,
        height: 48,
        shape: "round-rectangle",
      },
    },
    {
      selector: "node[kind='project']",
      style: { "border-color": PAL.primary },
    },
    {
      selector: "node[kind='idea']",
      style: { "border-color": PAL.inversePrimary },
    },
    {
      selector: "node[kind='research']",
      style: { "border-color": PAL.tertiary },
    },
    {
      selector: "node.fos-world-active",
      style: {
        "border-width": 4,
        "border-color": PAL.primary,
        "background-color": PAL.surfaceLow,
      },
    },
    {
      selector: "node.fos-world-inspect",
      style: {
        "overlay-opacity": 0.1,
        "overlay-color": PAL.primary,
        "overlay-padding": 8,
      },
    },
    {
      selector: "node[type='goal']",
      style: { "border-color": "#03904a", shape: "round-rectangle" },
    },
    {
      selector: "node[type='alert']",
      style: { "border-color": PAL.primary, "border-width": 2 },
    },
    {
      selector: "node[type='collection']",
      style: {
        "background-color": PAL.surface,
        "border-color": PAL.primary,
        width: 40,
        height: 40,
        shape: "hexagon",
      },
    },
    {
      selector: "node[type='memory_chunk']",
      style: {
        width: 20,
        height: 20,
        "font-size": 7,
        "background-color": PAL.surface,
        "border-color": PAL.outline,
      },
    },
    {
      selector: "node[type='person']",
      style: { "border-color": PAL.tertiary },
    },
    {
      selector: "node[type='empty']",
      style: { "background-color": PAL.surfaceLow, "border-color": PAL.outline },
    },
    {
      selector: "edge",
      style: {
        width: 1.5,
        "line-color": PAL.outline,
        "line-style": "dashed",
        "line-dash-pattern": [6, 4],
        "target-arrow-color": PAL.outline,
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        label: "data(label)",
        "font-size": 8,
        color: PAL.onSurfaceVariant,
        "text-rotation": "autorotate",
      },
    },
    {
      selector: ":selected",
      style: {
        "border-width": 3,
        "border-color": PAL.primary,
      },
    },
  ];

  const LAYOUT = {
    name: "cose",
    animate: true,
    animationDuration: 280,
    nodeRepulsion: 8000,
    idealEdgeLength: 90,
    padding: 24,
  };

  const HIERARCHY_LAYOUT = {
    name: "breadthfirst",
    directed: true,
    animate: true,
    animationDuration: 320,
    padding: 48,
    spacingFactor: 1.35,
    nodeDimensionsIncludeLabels: true,
  };

  function render(containerId, graphData, opts = {}) {
    const el = document.getElementById(containerId);
    if (!el || typeof cytoscape === "undefined") return null;

    if (instances[containerId]) {
      instances[containerId].destroy();
      delete instances[containerId];
    }

    const elements = [
      ...(graphData?.nodes || []),
      ...(graphData?.edges || []),
    ];
    if (!elements.length) return null;

    const cy = cytoscape({
      container: el,
      elements,
      style: STYLES,
      layout: opts.layout || LAYOUT,
      minZoom: 0.2,
      maxZoom: 2.5,
      wheelSensitivity: 0.3,
    });

    instances[containerId] = cy;

    if (opts.onSelect) {
      cy.on("tap", "node", (evt) => {
        opts.onSelect(evt.target.data());
      });
    }

    return cy;
  }

  function update(containerId, graphData) {
    const cy = instances[containerId];
    if (!cy) return render(containerId, graphData);
    cy.elements().remove();
    cy.add([...(graphData?.nodes || []), ...(graphData?.edges || [])]);
    cy.layout(LAYOUT).run();
    return cy;
  }

  function destroy(containerId) {
    if (instances[containerId]) {
      instances[containerId].destroy();
      delete instances[containerId];
    }
  }

  function getCy(containerId) {
    return instances[containerId] || null;
  }

  function highlightWorld(containerId, worldId, activeWorldId) {
    const cy = instances[containerId];
    if (!cy) return;
    cy.nodes().removeClass("fos-world-active fos-world-inspect");
    cy.nodes().forEach((n) => {
      const wid = n.data("world_id");
      if (!wid) return;
      if (wid === activeWorldId) n.addClass("fos-world-active");
      if (wid === worldId) n.addClass("fos-world-inspect");
    });
  }

  return { render, update, destroy, getCy, highlightWorld, HIERARCHY_LAYOUT, LAYOUT };
})();
