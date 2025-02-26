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
                const cyElements = cy.elements().jsons();

                $.ajax({
                    url: `/add_aop_bounding_box?aop=true`,
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({ cy_elements: cyElements }),
                    success: updatedCyElements => {
                        cy.elements().remove();
                        cy.add(updatedCyElements);
                        console.log("debug");
                        boundingBoxesVisible = true;
                        positionNodes(cy);
                    },
                    error: (jqXHR, textStatus, errorThrown) => {
                        console.error("Error adding bounding boxes:", textStatus, errorThrown);
                        alert(`Error adding bounding boxes: ${textStatus} - ${errorThrown}`);
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

function populateQaopTable(cy) {
    const table = $("#qaop_table");
    document.getElementById("loading_qaop_table").style.display = "none";
    const tableBody = table.find("tbody").empty();
    cy.edges().forEach(edge => {
        if (edge.data('ker_label')) {
            tableBody.append(`
                <tr>
                    <td><a href="${edge.source().data('id')}" target="_blank">${edge.source().data('label')}</a></td>
                    <td>${edge.data('curie')}</td>
                    <td><a href="${edge.target().data('id')}" target="_blank">${edge.target().data('label')}</a></td>
                </tr>
            `);
        }
    });
}

// Event listener for data-type-dropdown option value "qaop_table".
$("#data-type-dropdown").on("change", function () {
    const selectedValue = $(this).val();
    if (selectedValue === "qaop_div") {
        populateQaopTable(cy);
    }
});

$("#see_genes").on("click", function () {
    if (genesVisible) {
        console.log("Hiding ", cy.elements(".ensembl-node"));
        cy.elements(".ensembl-node").hide();
        $(this).text("See Genes");
        genesVisible = false;
    } else {
        console.log("Showing genes");
        toggleGeneView(cy);
        positionNodes(cy);
    }
});


function toggleGeneView(cy) {
    const mieNodeIds = cy.nodes().filter(node => node.data("is_mie")).map(node => node.id()).join(",");
    fetch(`/load_and_show_genes?mies=${encodeURIComponent(mieNodeIds)}`)
        .then(response => response.json())
        .then(data => {
            try {
                data.forEach(element => {
                    try {
                        cy.add(element);
                    } catch (error) {
                        console.warn("Skipping element");
                    }
                });
                console.log(cy.elements(".uniprot-node, .ensembl-node"));
                cy.elements(".uniprot-node, .ensembl-node").show();
                $("#see_genes").text("Hide Genes");
                genesVisible = true;
            } catch (error) {
                console.warn("Error processing elements:", error);
            }
        })
        .catch(error => {
            console.warn("Error fetching genes data:", error);
        });
}