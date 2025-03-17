$(document).ready(() => {
    // Load the compound table with clickable links.
    const qid = $("#compound-container").data("qid");
    $.getJSON(`/get_compounds/${qid}`, data => {
        console.log(data);
        document.getElementById("loading_compound").style.display = "none";
        const tableBody = $("#compound_table tbody").empty();
        data.forEach(option => {
            const encodedSMILES = encodeURIComponent(option.SMILES);
            compoundMapping[option.SMILES] = { term: option.Term, url: `/compound/${option.ID}`, target: "_blank" };
            if (option.cid && option.cid !== "nan") {
                compoundMapping[option.cid] = {
                    cid: option.cid,
                    url: `https://pubchem.ncbi.nlm.nih.gov/compound/${option.cid}`,
                    target: "_blank"
                };
            } else {
                compoundMapping[option.cid] = {
                    cid: option.cid,
                    url: "",
                };
            }
            tableBody.append(`
                <tr>
                    <td>
                        <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi=${encodedSMILES}" 
                             alt="${option.SMILES}" />
                        <p><a href="${compoundMapping[option.SMILES].url}" class="compound-link" target="_blank">${option.Term}</a></p> 
                        <p>PubChem ID: <a href="${compoundMapping[option.cid].url}" class="cid-link" target="_blank">${compoundMapping[option.cid].cid}</a></p>
                    </td>
                </tr>
            `);
        });
    });

    // Enable row selection to filter the Cytoscape network by compound.
    $("#compound_table").on("click", "tbody tr", function (e) {
        if ($(e.target).is("a") || $(e.target).is("button")) return; // Prevent row click when clicking on a link or button
        if (!fetched_preds) return;

        const compoundLink = $(this).find(".compound-link"); // Select the compound-link element.
        if (compoundLink.length) {
            console.log('compoundLink', compoundLink);
            compoundLink.toggleClass("selected"); // Toggle the 'selected' class on the compound-link element.

            const compoundName = compoundLink.text().trim(); // Get the compound name from the link text.
            if (compoundName) {
                const cyNode = cy.nodes(`[label="${compoundName}"]`); // Find the Cytoscape node with the same label.
                if (cyNode.length) {
                    console.log(cyNode);
                    cyNode.toggleClass("selected"); // Toggle the 'selected' class on the Cytoscape node.
                } else {
                    console.log('no cy node');
                }
            }
        }

        updateCytoscapeSubset();
        positionNodes(cy);
    });

    // Handle compound link
    $("#compound_table").on("click", ".compound-link", function (e) {
        const url = $(this).attr("href");
        $("#compound-frame").attr("src", url);
        positionNodes(cy);
    });
});

// function to collect all cids
function getAllCIDs() {
    const cids = [];
    $("#compound_table tbody tr").each((_, tr) => {
        const cidLink = $(tr).find(".cid-link");
        if (cidLink.length) {
            const cid = cidLink.text().trim();
            if (cid) {
                cids.push(cid);
            }
        }
    });
    console.log('retrieved cids', cids);
    return cids;
}

function updateCytoscapeSubset() {
    const selectedCompounds = [];

    // Collect the names of compounds that are selected in the table.
    $("#compound_table tbody tr").each(function () {
        const compoundLink = $(this).find(".compound-link");
        if (compoundLink.hasClass("selected")) {
            const compoundName = compoundLink.text().trim();
            if (compoundName) {
                selectedCompounds.push(compoundName);
            }
        }
    });

    console.log("Selected compounds:", selectedCompounds);

    if (!selectedCompounds.length) {
        cy.elements().show();
        cy.fit(cy.elements(), 50);
        return;
    }

    const visited = new Set();
    let activated = cy.collection();

    // Breadth-first search function to traverse outgoing edges.
    function bfs(startNode) {
        const queue = [startNode];
        while (queue.length > 0) {
            const node = queue.shift();
            if (visited.has(node.id())) continue;
            visited.add(node.id());
            activated = activated.union(node);

            node.outgoers('edge').forEach(edge => {
                const target = edge.target();
                if (!visited.has(target.id())) {
                    queue.push(target);
                }
            });
        }
    }

    // Start BFS from selected chemical nodes.
    selectedCompounds.forEach(compoundName => {
        const node = cy.nodes(`[label="${compoundName}"]`);
        if (!node.empty() && node.hasClass("chemical-node")) {
            bfs(node);
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
