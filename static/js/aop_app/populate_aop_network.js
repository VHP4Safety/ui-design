let boundingBoxesVisible = false;
let genesVisible = false;
document.addEventListener("DOMContentLoaded", function () {
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
            } else {
                window.open(`${url}`);
            }
        });
        
        cy.on("tap", "edge", function(evt) {
            const edge = evt.target;
            if (edge.data("ker_label")) {
                window.open(`https://identifiers.org/aop.relationships/${edge.data("ker_label")}`);
            }
        });

        // Log when nodes are added.
        cy.on("add", "node", function (evt) {
            console.debug(`Node added: ${evt.target.id()}`);
            positionNodes(cy);
        });

        // Hide Genes button functionality.
        $("#see_genes").on("click", function () {
            if (genesVisible) {
                console.log("Hiding ", cy.elements(".ensembl-node"));
                cy.elements(".ensembl-node").hide();
                $(this).text("See Genes");
                genesVisible = false;
                positionNodes(cy);
                return
            } if (!genesVisible) {
                loadAndShowGenes();
                genesVisible = true;
                return
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

    // Add "Download Cytoscape Network" button functionality.
    $("#download_network").on("click", function () {
        const cyJson = cy.json();
        console.log(cyJson);
        const blob = new Blob([JSON.stringify(cyJson)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "cytoscape_network.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
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
                    //console.debug("CSV data parsed successfully", results);
                    const geneElements = [];
                    results.data.forEach(row => {
                        const mieId = "https://identifiers.org/aop.events/" + row["MIE/KE identifier in AOP wiki"];
                        const uniprotId = row["uniprot ID inferred from qspred name"];
                        const ensemblId = row["Ensembl"];
                        //console.debug(`Processing row - MIE ID: ${mieId}, UniProt ID: ${uniprotId}, Ensembl ID: ${ensemblId}`);

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
                                    data: { id: edgeMieUniId, source: uniprotNodeId, target: mieId, label: "part of" }
                                });
                            }

                            const edgeUniEnsId = `edge_${uniprotNodeId}_${ensemblNodeId}`;
                            if (cy.getElementById(edgeUniEnsId).empty()) {
                                geneElements.push({
                                    data: { id: edgeUniEnsId, source: uniprotNodeId, target: ensemblNodeId, label: "translates to" }
                                });
                            }
                        } else {
                            //console.warn(`Skipping row due to missing data or parent node: ${JSON.stringify(row)}`);
                        }
                    });

                    //console.debug("Adding gene elements:", geneElements);
                    cy.add(geneElements);
                    cy.elements(".uniprot-node, .ensembl-node").show();
                    $("#see_genes").text("Hide Genes");
                    
                }
            });
            positionNodes(cy);
        },
        error: (jqXHR, textStatus, errorThrown) => {
            console.error("Error loading CSV data:", textStatus, errorThrown);
        }
    });
}

function updateCytoscapeSubset() {
    // Get the selected compound IDs from the table.
    const selectedIds = $("#compound_table tbody tr.selected")
        .map((_, row) => $(row).find("td:first").text().trim())
        .get();

    if (!selectedIds.length) {
        cy.elements().show();
        cy.fit(cy.elements(), 50);
        return;
    }

    const visited = new Set();
    let activated = cy.collection();

    // Depth-first search function, recursively traverse outgoing edges.
    function dfs(node) {
        if (visited.has(node.id())) return;
        visited.add(node.id());
        activated = activated.union(node);

        node.outgoers('edge').forEach(edge => {
            const target = edge.target();
            // If target is a chemical node not in the selection, add it but don't traverse further.
            if (target.hasClass('chemical-node') && !selectedIds.includes(target.id())) {
                activated = activated.union(target);
            } else {
                dfs(target);
            }
        });
    }

    // Start depth-first search only from selected chemical nodes.
    selectedIds.forEach(id => {
        const node = cy.getElementById(id);
        if (!node.empty() && node.hasClass('chemical-node')) {
            dfs(node);
        }
    });

    // Keep only edges connecting activated nodes.
    const activatedEdges = cy.edges().filter(edge =>
        activated.contains(edge.source()) && activated.contains(edge.target())
    );

    cy.elements().hide();
    activated.show();
    activatedEdges.show();
    cy.fit(activated, 50);
    positionNodes(cy);
}

function populateQsprPredMies(cy, compoundMapping, modelToProteinInfo, modelToMIE, response) {
    const table = $("#compound_table");
    const tableHead = table.find("thead").empty();
    const tableBody = table.find("tbody").empty();

    tableHead.append(`
            <tr>
                <th>Compound</th>
                <th>Target</th>
                <th>Predicted pChEMBL</th>
            </tr>
        `);

    if (Array.isArray(response)) {
        const grouped = response.reduce((acc, pred) => {
            const s = pred.smiles;
            (acc[s] = acc[s] || []).push(pred);
            return acc;
        }, {});

        const cyElements = [];
        Object.entries(grouped).forEach(([smiles, predictions]) => {
            const compound = compoundMapping[smiles];
            const compoundCell = compound ? `<a href="${compound.url}">${compound.term}</a>` : smiles;
            const targetCells = [];
            const pChEMBLCells = [];

            predictions.forEach(prediction => {
                Object.entries(prediction).forEach(([model, value]) => {
                    if (parseFloat(value) >= 6.5) {
                        const proteinInfo = modelToProteinInfo[model] || { proteinName: "Unknown Protein", uniprotId: "" };
                        const proteinLink = proteinInfo.uniprotId ? `<a href="https://www.uniprot.org/uniprotkb/${proteinInfo.uniprotId}" target="_blank">${proteinInfo.proteinName}</a>` : proteinInfo.proteinName;
                        targetCells.push(`${proteinLink} (${model})`);
                        pChEMBLCells.push(value);

                        const targetNodeId = `https://identifiers.org/aop.events/${modelToMIE[model]}`;
                        const compoundId = compound ? compound.term : smiles;
                        cyElements.push(
                            { data: { id: compoundId, label: compoundId, type: "chemical", smiles: smiles }, classes: "chemical-node" },
                            { data: { id: `${compoundId}-${targetNodeId}-${model}`, source: compoundId, target: `uniprot_${proteinInfo.uniprotId}`, value: value, type: "interaction", label: `pChEMBL: ${value} (${model})` } }
                        );
                    }
                });
            });

            tableBody.append(`
                <tr>
                    <td>
                        <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=.4&annotate=cip&r=0&smi=${encodeURIComponent(smiles)}" 
                             alt="${smiles}" />
                        <br />
                        ${compoundCell}
                    </td>
                    <td>${targetCells.join('<br>')}</td>
                    <td>${pChEMBLCells.join('<br>')}</td>
                </tr>
            `);
        });

        if (cyElements.length) {
            cy.add(cyElements);
            positionNodes(cy);
        }
    } else {
        console.error("Unexpected API response format:", response);
        alert("Error: Unexpected response format from server.");
    }
}
