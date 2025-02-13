document.addEventListener("DOMContentLoaded", function () {
    let boundingBoxesVisible = false;

    // A stub for positionNodes – replace with your own logic as needed.
    function positionNodes(cyInstance) {
        console.debug("Positioning nodes...");
        // For example, you might want to run a layout or update positions here.
        // cyInstance.fit();
    }

    // Fetch data for the AOP network.
    function fetchAOPData(mies) {
        console.debug(`Fetching AOP network data for: ${mies}`);
        return fetch(`/get_aop_network?mies=${encodeURIComponent(mies)}`)
            .then(response => response.json())
            .catch(error => {
                console.error("Error fetching AOP data:", error);
                return [];
            });
    }

    function renderAOPNetwork(elements) {
        console.debug("Rendering AOP network with elements:", elements);
        document.getElementById("loading").style.display = "none";
        document.getElementById("cy").style.backgroundColor = "#FFFFFF";

        // Create Cytoscape instance.
        cy = cytoscape({
            container: document.getElementById("cy"),
            elements: elements.map(ele => ({
                data: {
                    id: ele.id,
                    ...ele.data
                }
            })),
            layout: { name: "cose" },
            style: [
                {
                    // Apply fixed width/height only to non-compound nodes.
                    selector: "node:not(.bounding-box)",
                    style: {
                        "width": 150,
                        "height": 150,
                        "background-color": ele =>
                            ele.data("is_mie") ? "#ccffcc" :
                                ele.data("is_ao") ? "#ffe6e6" :
                                    ele.data("is_uniprot") ? "#ffff99" :
                                        ele.data("is_ensembl") ? "#ffcc99" : "#ffff99",
                        "label": "data(label)",
                        "text-wrap": "wrap",
                        "text-max-width": "120px",
                        "text-valign": "center",
                        "text-halign": "center",
                        "color": "#000",
                        "font-size": "18px",
                        "border-width": 2,
                        "border-color": "#000"
                    }
                },
                {
                    selector: "edge[ker_label]",
                    style: {
                        "curve-style": "bezier",
                        "width": 3,
                        "line-color": "#000",
                        "opacity": 0.8,
                        "target-arrow-shape": "triangle",
                        "target-arrow-color": "#000",
                        "label": "data(ker_label)",
                        "text-margin-y": -15,
                        "text-rotation": "autorotate",
                        "font-size": "30px",
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
                        "font-size": "25px",
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
                        "font-size": "25px",
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
                        "text-margin-y": -10,
                        "font-size": "22px",
                        "color": "#000"
                    }
                },
                {
                    // Bounding boxes (compound nodes) should auto-size based on their children.
                    selector: ".bounding-box",
                    style: {
                        "shape": "roundrectangle",
                        "background-opacity": 0.1,
                        "border-width": 2,
                        "border-color": "#000",
                        "label": "data(label)",
                        "text-valign": "top",
                        "text-halign": "center",
                        "font-size": "14px",
                        "padding": "10px",
                        "compound-sizing-wrt-labels": "include"
                    }
                }
            ]
        });

        console.debug("Cytoscape instance created with elements:", cy.elements());
        positionNodes(cy);

        // Node click event.
        cy.on("tap", "node", function (evt) {
            const node = evt.target;
            const url = node.id();
            console.debug(`Node tapped: ${node.id()}, data:`, node.data());
            if (node.hasClass("uniprot-node")) {
                window.open(`https://www.uniprot.org/uniprotkb/${url.replace("uniprot_", "")}`, "_blank");
            } else if (node.hasClass("ensembl-node")) {
                window.open(`https://identifiers.org/ensembl/${url.replace("ensembl_", "")}`, "_blank");
            } else if (url) {
                window.open(url, "_blank");
            }
        });

        // Log when nodes are added.
        cy.on("add", "node", function (evt) {
            console.debug(`Node added: ${evt.target.id()}`);
            positionNodes(cy);
        });

        // "See Genes" button functionality.
        $("#see_genes").on("click", function () {
            console.debug('Loading CSV data for "See Genes"');
            $.ajax({
                url: "/static/data/caseMieModel.csv",
                dataType: "text",
                success: data => {
                    console.debug("CSV data loaded successfully");
                    Papa.parse(data, {
                        header: true,
                        skipEmptyLines: true,
                        complete: results => {
                            console.debug("CSV data parsed successfully", results);
                            const geneElements = [];
                            results.data.forEach(row => {
                                const mieId = "https://identifiers.org/aop.events/" + row["MIE/KE identifier in AOP wiki"];
                                const uniprotId = row["uniprot ID inferred from qspred name"];
                                const ensemblId = row["Ensembl"];
                                const proteinName = row["protein name uniprot"];
                                console.debug(`Processing row - MIE ID: ${mieId}, UniProt ID: ${uniprotId}, Ensembl ID: ${ensemblId}, Protein Name: ${proteinName}`);

                                if (mieId && uniprotId && ensemblId && cy.getElementById(mieId).length > 0) {
                                    console.debug(`Valid row found for MIE: ${mieId}`);
                                    const uniprotNodeId = `uniprot_${uniprotId}`;
                                    const ensemblNodeId = `ensembl_${ensemblId}`;

                                    if (cy.getElementById(uniprotNodeId).empty()) {
                                        geneElements.push({
                                            data: {
                                                id: uniprotNodeId,
                                                label: uniprotId,
                                                type: "uniprot"
                                            },
                                            classes: "uniprot-node"
                                        });
                                    } else {
                                        console.debug(`UniProt node ${uniprotNodeId} already exists`);
                                    }

                                    if (cy.getElementById(ensemblNodeId).empty()) {
                                        geneElements.push({
                                            data: {
                                                id: ensemblNodeId,
                                                label: ensemblId,
                                                type: "ensembl"
                                            },
                                            classes: "ensembl-node"
                                        });
                                    } else {
                                        console.debug(`Ensembl node ${ensemblNodeId} already exists`);
                                    }

                                    const edgeMieUniId = `edge_${mieId}_${uniprotNodeId}`;
                                    if (cy.getElementById(edgeMieUniId).empty()) {
                                        geneElements.push({
                                            data: {
                                                id: edgeMieUniId,
                                                source: mieId,
                                                target: uniprotNodeId,
                                                label: "part of"
                                            }
                                        });
                                    } else {
                                        console.debug(`Edge ${edgeMieUniId} already exists`);
                                    }

                                    const edgeUniEnsId = `edge_${uniprotNodeId}_${ensemblNodeId}`;
                                    if (cy.getElementById(edgeUniEnsId).empty()) {
                                        geneElements.push({
                                            data: {
                                                id: edgeUniEnsId,
                                                source: uniprotNodeId,
                                                target: ensemblNodeId,
                                                label: "translates to"
                                            }
                                        });
                                    } else {
                                        console.debug(`Edge ${edgeUniEnsId} already exists`);
                                    }
                                } else {
                                    console.warn(`Skipping row due to missing data or parent node: ${JSON.stringify(row)}`);
                                }
                            });

                            console.debug("Adding gene elements:", geneElements);
                            cy.add(geneElements);
                            console.debug("Gene elements added to Cytoscape");
                            positionNodes(cy);
                        }
                    });
                },
                error: (jqXHR, textStatus, errorThrown) => {
                    console.error("Error loading CSV data:", textStatus, errorThrown);
                }
            });
        });

        // "Toggle Bounding Boxes" button functionality.
        $("#toggle_bounding_boxes").on("click", function () {
            if (boundingBoxesVisible) {
                console.debug("Removing bounding boxes");
                cy.elements(".bounding-box").remove();
                boundingBoxesVisible = false;
            } else {
                console.debug("Adding bounding boxes");
                const aopGroups = {};
                cy.nodes().forEach(node => {
                    const aop = node.data("aop");
                    const aopTitle = node.data("aop_title");
                    if (aop) {
                        if (!aopGroups[aop]) {
                            aopGroups[aop] = { nodes: [], title: aopTitle };
                        }
                        aopGroups[aop].nodes.push(node);
                    } else {
                        console.warn(`Node ${node.id()} is missing aop data`);
                    }
                });

                const boundingBoxes = [];
                Object.keys(aopGroups).forEach(aop => {
                    const group = aopGroups[aop];
                    const nodes = group.nodes;
                    const aopTitle = group.title;
                    // Compute bounding box for the group.
                    const boundingBox = cy.collection(nodes).boundingBox();
                    console.debug(`Bounding box for AOP ${aop}:`, boundingBox);
                    const parentId = `bounding-box-${aop}`;
                    boundingBoxes.push({
                        group: "nodes",
                        data: { id: parentId, label: `${aopTitle}\n${aop}` },
                        classes: "bounding-box"
                    });
                    cy.add(boundingBoxes);
                    boundingBoxesVisible = true;
                    // Assign nodes as children of the bounding box.
                    nodes.forEach(node => {
                        console.debug(`Assigning node ${node.id()} to AOP bounding box ${parentId}`);
                        node.move({ parent: parentId });
                        
                    });
                });

                

                // Re-run the layout so the compound nodes update.
                cy.layout({
                    name: "cose",
                    animate: true
                }).run();
            }
        });

        // Update the style for bounding boxes (if dynamic changes are needed).
        cy.style()
            .selector(".bounding-box")
            .style({
                "shape": "roundrectangle",
                "background-opacity": 0.1,
                "border-width": 2,
                "border-color": "#000",
                "padding": "10px",
                "compound-sizing-wrt-labels": "include"
            })
            .update();

        // Run final layout and fit view to container.
        cy.layout({ name: "cose", animate: true }).run();
        cy.fit();
        console.debug("Final layout complete. Cytoscape view fitted to container.");
    }

    // Retrieve the "mies" data.
    const compoundContainer = document.getElementById("compound-container");
    const mies = compoundContainer ? compoundContainer.dataset.mies : null;
    if (mies) {
        fetchAOPData(mies).then(data => {
            console.debug("Fetched AOP data:", data);
            renderAOPNetwork(data);
        });
    } else {
        console.error("No 'mies' data found in compound-container");
    }

    // Reset layout button functionality.
    $("#reset_layout").on("click", function () {
        console.debug("Resetting layout...");
        cy.layout({ name: "cose", animate: true }).run();
        positionNodes(cy);
    });
});
