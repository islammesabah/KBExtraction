// ui/static/js/cytoscape_theme.js
// Centralizes: Bootstrap theme extraction + Cytoscape style + Cytoscape creation.

function getCssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function getBootstrapTheme() {
  // Bootstrap 5 defaults as fallbacks (only used if CSS vars missing)
  const bsPrimary = getCssVar("--bs-primary", "#0d6efd");
  const bsSecondary = getCssVar("--bs-secondary", "#6c757d");
  const bsLight = getCssVar("--bs-light", "#f8f9fa");
  const bsWarning = getCssVar("--bs-warning", "#ffc107");

  // We'll unify highlight using bsWarning (Bootstrap's yellow highlighter vibe)
  const highlight = bsWarning;

  return {
    bsPrimary,
    bsSecondary,
    bsLight,
    bsWarning,
    highlight,
  };
}

export function buildCytoscapeStyle(theme) {
  const { bsPrimary, bsSecondary, bsLight, highlight } = theme;

  return [
    {
      selector: "node",
      style: {
        "background-color": bsPrimary,
        "label": "data(label)",
        "text-valign": "center",
        "text-halign": "center",
        "color": "#fff",
        "text-outline-width": 2,
        "text-outline-color": bsPrimary,
        "font-size": "12px",
        "width": "50px",
        "height": "50px",
      },
    },
    {
      selector: "edge",
      style: {
        "width": 2,
        "line-color": bsSecondary,
        "target-arrow-color": bsSecondary,
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        "label": "data(label)",
        "font-size": "10px",
        "text-rotation": "none",
        "text-background-opacity": 1,
        "text-background-color": bsLight,
        "text-background-padding": 2,
        "text-wrap": "wrap",
        "text-max-width": 80,
      },
    },

    // ✅ Node glow + ring (use the SAME highlight color as edges)
    {
      selector: ".highlighted-node",
      style: {
        "shadow-blur": 18,
        "shadow-color": highlight,
        "shadow-opacity": 0.9,
        "shadow-offset-x": 0,
        "shadow-offset-y": 0,

        "border-width": 6,
        "border-color": highlight,
        "border-opacity": 0.9,

        "transition-property": "shadow-blur, shadow-opacity, border-width, border-opacity",
        "transition-duration": "0.2s",
      },
    },

    // ✅ Edge highlight (same highlight color)
    {
      selector: ".highlighted-edge",
      style: {
        "width": 4,
        "line-color": highlight,
        "target-arrow-color": highlight,

        // optional aura for edges too
        "shadow-blur": 12,
        "shadow-color": highlight,
        "shadow-opacity": 0.8,
        "shadow-offset-x": 0,
        "shadow-offset-y": 0,

        "transition-property": "width, line-color, target-arrow-color, shadow-blur, shadow-opacity",
        "transition-duration": "0.2s",
      },
    },

    {
      selector: ".faded",
      style: {
        "opacity": 0.1,
        "text-opacity": 0,
      },
    },
  ];
}

export function createStyledCytoscape(containerEl, layoutOverrides = {}) {
  const theme = getBootstrapTheme();

  const cy = cytoscape({
    container: containerEl,
    style: buildCytoscapeStyle(theme),
    layout: {
      name: "cose",
      animate: true,
      idealEdgeLength: 180,
      nodeRepulsion: 10000,
      edgeElasticity: 80,
      gravity: 0.8,
      numIter: 1000,
      ...layoutOverrides,
    },
  });

  return { cy, theme };
}