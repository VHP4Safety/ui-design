function positionNodes(cy, fontSizeMultiplier = 1) {
    cy.layout({
        //animate: true,
        name: 'breadthfirst',
        directed: true,
        padding: 30,
        //rankDir: "RL"
    }).run();
    cy.style([
        {
            selector: "node",
            style: {
                "width": `${270 * fontSizeMultiplier}px`,
                "height": `${200 * fontSizeMultiplier}px`,
                "background-color": ele =>
                    ele.data("is_mie") ? "#ccffcc" :
                        ele.data("is_ao") ? "#ffe6e6" :
                            ele.data("is_uniprot") ? "#ffff99" :
                                ele.data("is_ensembl") ? "#ffcc99" : "#ffff99",
                "label": "data(label)",
                "text-wrap": "wrap",
                "text-max-width": `${250 * fontSizeMultiplier}px`,
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000",
                "font-size": `${40 * fontSizeMultiplier}px`,
                "border-width": "2px",
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
                "text-max-width": `${200 * fontSizeMultiplier}px`,
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000",
                "font-size": `${40 * fontSizeMultiplier}px`,
                "border-width": 2,
                "border-color": "#000"
            }
        },
        {
            selector: "edge[ker_label]",
            style: {
                "curve-style": "unbundled-bezier",
                "width": `${40 * fontSizeMultiplier}px`,
                "line-color": "#93d5f6",
                "opacity": 0.8,
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#93d5f6",
                "label": "data(ker_label)",
                "text-margin-y": 1,
                "text-rotation": "autorotate",
                "font-size": `${40 * fontSizeMultiplier}px`,
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
                "font-size": `${45 * fontSizeMultiplier}px`,
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
                "font-size": `${45 * fontSizeMultiplier}px`,
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
                "font-size": `${40 * fontSizeMultiplier}px`,
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
                "font-size": `${50 * fontSizeMultiplier}px`,
                "text-wrap": "none"
            }
        }
    ]).update();
}

// Add event listener for font size slider
document.getElementById('font-size-slider').addEventListener('input', function() {
    const fontSizeMultiplier = parseFloat(this.value);
    console.log(fontSizeMultiplier);
    positionNodes(cy, fontSizeMultiplier);
});