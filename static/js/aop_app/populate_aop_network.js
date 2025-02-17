document.addEventListener("DOMContentLoaded", function () {
    let boundingBoxesVisible = false;
    let genesVisible = false;
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
        document.getElementById("loading_aop").style.display = "none";
        //document.getElementById("cy").style.backgroundColor = "#FFFFFF";

        // Create Cytoscape instance.
        cy = cytoscape({
            container: document.getElementById("cy"),
            elements: elements.map(ele => ({
                data: {
                    id: ele.id,
                    ...ele.data
                }
            })),
            //layout: { name: "cose" }
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
            } else if (node.hasClass("bounding-box")) {
                window.open(node.data("aop"), "_blank");
            }
        });

        // Log when nodes are added.
        cy.on("add", "node", function (evt) {
            console.debug(`Node added: ${evt.target.id()}`);
            positionNodes(cy);
        });

        function loadAndShowGenes() {
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
                                console.debug(`Processing row - MIE ID: ${mieId}, UniProt ID: ${uniprotId}, Ensembl ID: ${ensemblId}`);

                                if (mieId && uniprotId && ensemblId && cy.getElementById(mieId).length > 0) {
                                    const uniprotNodeId = `uniprot_${uniprotId}`;
                                    const ensemblNodeId = `ensembl_${ensemblId}`;

                                    if (cy.getElementById(uniprotNodeId).empty()) {
                                        geneElements.push({
                                            data: { id: uniprotNodeId, label: uniprotId, type: "uniprot" },
                                            classes: "uniprot-node"
                                        });
                                    }

                                    if (cy.getElementById(ensemblNodeId).empty()) {
                                        geneElements.push({
                                            data: { id: ensemblNodeId, label: ensemblId, type: "ensembl" },
                                            classes: "ensembl-node"
                                        });
                                    }

                                    const edgeMieUniId = `edge_${mieId}_${uniprotNodeId}`;
                                    if (cy.getElementById(edgeMieUniId).empty()) {
                                        geneElements.push({
                                            data: { id: edgeMieUniId, source: mieId, target: uniprotNodeId, label: "part of" }
                                        });
                                    }

                                    const edgeUniEnsId = `edge_${uniprotNodeId}_${ensemblNodeId}`;
                                    if (cy.getElementById(edgeUniEnsId).empty()) {
                                        geneElements.push({
                                            data: { id: edgeUniEnsId, source: uniprotNodeId, target: ensemblNodeId, label: "translates to" }
                                        });
                                    }
                                } else {
                                    console.warn(`Skipping row due to missing data or parent node: ${JSON.stringify(row)}`);
                                }
                            });

                            console.debug("Adding gene elements:", geneElements);
                            cy.add(geneElements);
                            cy.elements(".uniprot-node, .ensembl-node").show();
                            $("#see_genes").text("Hide Genes");
                            genesVisible = true;
                        }
                    });
                    positionNodes(cy);
                },
                error: (jqXHR, textStatus, errorThrown) => {
                    console.error("Error loading CSV data:", textStatus, errorThrown);
                }
            });
        }

        // Hide Genes button functionality.
        $("#see_genes").on("click", function () {
            if (genesVisible) {
                console.debug('Hiding genes');
                cy.elements(".uniprot-node, .ensembl-node").hide();
                $(this).text("See Genes");
                genesVisible = false;
                positionNodes(cy);
            } else {
                loadAndShowGenes();
            }
        });

        // Toggle Bounding Boxes (AOP boxes) button functionality.
        $("#toggle_bounding_boxes").on("click", function () {
            if (boundingBoxesVisible) {
                console.debug("Removing bounding boxes");
                cy.nodes().forEach(node => {
                    if (node.isChild()) {
                        node.move({ parent: null });
                    }
                });
                cy.elements(".bounding-box").remove();
                boundingBoxesVisible = false;
            } else {
                console.debug("Adding bounding boxes");
                const aopGroups = {};
                cy.nodes().forEach(node => {
                    const aop = node.data("aop");
                    const aopTitle = node.data("aop_title");
                    if (aop) {
                        const aopList = Array.isArray(aop) ? aop : [aop];
                        aopList.forEach(aopItem => {
                            if (!aopGroups[aopItem]) {
                                aopGroups[aopItem] = { nodes: [], title: aopTitle };
                            }
                            aopGroups[aopItem].nodes.push(node);
                        });
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
                });

                cy.add(boundingBoxes);
                boundingBoxesVisible = true;

                // Assign nodes as children of the bounding boxes.
                cy.nodes().forEach(node => {
                    const aop = node.data("aop");
                    console.log("TYPE OF AOP", typeof aop, aop);
                    if (aop) {
                        const aopList = Array.isArray(aop) ? aop : [aop];
                        aopList.forEach(aopItem => {
                            const parentId = `bounding-box-${aopItem}`;
                            if (cy.getElementById(parentId).length > 0) {
                                node.move({ parent: parentId });
                            }
                        });
                    }
                });
                // Assign genes and UniProts connected to MIEs to the bounding boxes.
                cy.nodes().forEach(node => {
                    if (
                        node.hasClass("uniprot-node") ||
                        node.hasClass("ensembl-node") ||
                        node.hasClass("chemical-node")
                    ) {
                        const connectedMIEs = node.connectedEdges().filter(edge => edge.target().data("is_mie"));
                        connectedMIEs.forEach(edge => {
                            const mieNode = edge.target();
                            const aop = mieNode.data("aop");
                            if (aop) {
                                const aopList = Array.isArray(aop) ? aop : [aop];
                                aopList.forEach(aopItem => {
                                    const parentId = `bounding-box-${aopItem}`;
                                    if (cy.getElementById(parentId).length > 0) {
                                        node.move({ parent: parentId });
                                    }
                                });
                            }
                        });
                    }
                });
            }
        });

        // Update the style for bounding boxes (if dynamic changes are needed).
        positionNodes(cy);
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
        positionNodes(cy);
    });
});
