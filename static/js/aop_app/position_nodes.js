function positionNodes(cy) {
    cy.layout({
        animate: true,
        name: 'cose',
        idealEdgeLength: 200,
        gravity: 0.1,
        nodeRepulsion: 400,
    }).run();
    cy.fit();
    cy.style([
        {
            selector: "node",
            style: {
                "width": 270,
                "height": 200,
                "background-color": ele =>
                    ele.data("is_mie") ? "#ccffcc" :
                        ele.data("is_ao") ? "#ffe6e6" :
                            ele.data("is_uniprot") ? "#ffff99" :
                                ele.data("is_ensembl") ? "#ffcc99" : "#ffff99",
                "label": "data(label)",
                "text-wrap": "wrap",
                "text-max-width": "250px",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000",
                "font-size": "40px",
                "border-width": 2,
                "border-color": "#000"
            }
        },
        {
            selector: ".chemical-node",
            style: {
                "shape": "triangle",
                "background-color": "#a9d3f5",
                "label": "data(label)",
                "text-wrap": "wrap",
                "text-max-width": "200px",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000",
                "font-size": "40px",
                "border-width": 2,
                "border-color": "#000"
            }
        },
        {
            selector: "edge[ker_label]",
            style: {
                "curve-style": "unbundled-bezier",
                "width": 3,
                "line-color": "#000",
                "opacity": 0.8,
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#000",
                "label": "data(ker_label)",
                "text-margin-y": -15,
                "text-rotation": "autorotate",
                "font-size": "40px",
                "font-weight": "bold",
                "color": "#000"
            }
        },
        {
            selector: ".uniprot-node",
            style: {
                "shape": "rectangle",
                "background-opacity": 0,
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000000",
                "font-size": "45px",
                "font-weight": "bold",
                "border-width": 0,
                "border-color": "transparent"
            }
        },
        {
            selector: ".ensembl-node",
            style: {
                "shape": "ellipse",
                "background-opacity": 0,
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000000",
                "font-size": "45px",
                "font-weight": "bold",
                "border-width": 0,
                "border-color": "transparent"
            }
        },
        {
            selector: "edge[label]",
            style: {
                "label": "data(label)",
                "text-rotation": "autorotate",
                "text-margin-y": -15,
                "font-size": "40px",
                "color": "#000",
                "curve-style": "unbundled-bezier",

            }
        },
        {
            // Bounding boxes (aop nodes) should auto-size based on their children.
            selector: ".bounding-box",
            style: {
                "shape": "roundrectangle",
                "background-opacity": 0.1,
                "border-width": 2,
                "border-color": "#000",
                "label": "data(label)",
                "text-valign": "top",
                "text-halign": "center",
                "font-size": "50px",
                "text-wrap": "none"
            }
        }
    ]).update();
}