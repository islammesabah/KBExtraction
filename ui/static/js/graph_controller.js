/**
 * Graph controller:
 * - creates the Cytoscape instance
 * - updates graph elements when new payload arrives
 */

export function createGraphController(containerId = "cy") {
  const cy = cytoscape({
    container: document.getElementById(containerId),
    style: [
      {
        selector: "node",
        style: {
          "background-color": "#3f51b5",
          "label": "data(label)",
          "text-valign": "center",
          "text-halign": "center",
          "color": "#fff",
          "text-outline-width": 2,
          "text-outline-color": "#3f51b5",
          "font-size": "12px",
          "width": "50px",
          "height": "50px"
        }
      },
      {
        selector: "edge",
        style: {
            'width': 2,
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-background-opacity': 1,
            'text-background-color': '#ffffff',
            'text-background-padding': 2,
            'text-wrap': 'wrap',
            'text-max-width': 80
        }
      },
      {
        selector: ".highlighted",
        style: {
          "background-color": "#f50057",
          "line-color": "#f50057",
          "target-arrow-color": "#f50057",
          "transition-property": "background-color, line-color, target-arrow-color",
          "transition-duration": "0.5s"
        }
      },
      {
        selector: ".faded",
        style: {
          "opacity": 0.1,
          "text-opacity": 0
        }
      }
    ],
    layout: {
        name: "cose",
        animate: true,
        // fit: true,
        // padding: 150, // adds space between the graph and the viewport border when fitting/zooming.

        idealEdgeLength: 180,
        nodeRepulsion: 10000,
        edgeElasticity: 80,
        gravity: 0.8,
        numIter: 1000
     }
  });


  // // Node highlighting on click (very powerful)
  // // This will connect Stage 1 visualization to Stage 2 semantic filtering beautifully.
  // cy.on('tap', 'node', function(evt) {
  //   const node = evt.target;
  //   // update right panel with node.data('properties')
  // });

  function setGraph(elements) {
    // Clear current graph then add new elements
    cy.elements().remove();

    if (elements) {
      cy.add(elements);
      cy.layout({
        name: 'cose', animate: true
      }).run();
      cy.fit(undefined, 150);
    }
  }

  return { cy, setGraph };
}
