let compoundMapping = {};

$(document).ready(() => {
    // Load the compound table with clickable links.
    const qid = $("#compound-container").data("qid");
    $.getJSON(`/get_compounds/${qid}`, data => {
        const tableBody = $("#compound_table tbody").empty();
        data.forEach(option => {
            const encodedSMILES = encodeURIComponent(option.SMILES);
            compoundMapping[option.SMILES] = { term: option.Term, url: `/compound/${option.ID}` };
            tableBody.append(`
        <tr>
          <td><a href="/compound/${option.ID}">${option.Term}</a></td>
          <td rowspan="1">
            <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=1&annotate=cip&r=0&smi=${encodedSMILES}" 
                 alt="${option.SMILES}" />
          </td>
        </tr>
      `);
        });
    });

    // Enable row selection to filter the Cytoscape network.
    $("#compound_table").on("click", "tbody tr", function (e) {
        if ($(e.target).is("a")) return;
        $(this).toggleClass("selected");
        updateCytoscapeSubset();
    });

    // Fetch predictions and update the table and Cytoscape.
    $("#fetch_predictions").on("click", () => {
        const smilesList = [];
        const mieQuery = $("#compound-container").data("mie-query");

        $.ajax({
            url: "/get_case_mie_model",
            type: "GET",
            data: { mie_query: mieQuery },
            success: modelToMIE => {
                console.log("Model to MIE Mapping:", modelToMIE);
                $("#compound_table tbody tr").each((_, tr) => {
                    const img = $(tr).find("td:eq(1) img");
                    const smiles = img.attr("alt") && img.attr("alt").trim();
                    if (smiles) smilesList.push(smiles);
                });
                console.log("Extracted SMILES List:", smilesList);

                const models = Object.keys(modelToMIE);
                if (!models.length) return alert("Error: No models available for prediction.");

                const requestData = { smiles: smilesList, models, metadata: {}, threshold: 6.5 };
                console.log("REQUEST DATA:", requestData);

                $.ajax({
                    url: "/get_predictions",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify(requestData),
                    success: response => {
                        console.log("API Response:", response);
                        const table = $("#compound_table");
                        const tableHead = table.find("thead").empty();
                        const tableBody = table.find("tbody").empty();

                        tableHead.append(`
              <tr>
                <th>Compound</th>
                <th>SMILES</th>
                <th>Model</th>
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
                                tableBody.append(`
                  <tr>
                    <td>${compoundCell}</td>
                    <td>
                      <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=1&annotate=cip&r=0&smi=${encodeURIComponent(smiles)}" 
                           alt="${smiles}" />
                    </td>
                    <td></td>
                    <td></td>
                  </tr>
                `);

                                predictions.forEach(prediction => {
                                    Object.entries(prediction).forEach(([model, value]) => {
                                        if (model !== "smiles" && parseFloat(value) >= 6.5) {
                                            tableBody.append(`
                        <tr>
                          <td></td>
                          <td></td>
                          <td>${model}</td>
                          <td>${value}</td>
                        </tr>
                      `);
                                            if (typeof cy !== "undefined") {
                                                const targetNodeId = `https://identifiers.org/aop.events/${modelToMIE[model]}`;
                                                const compoundId = compound ? compound.term : smiles;
                                                cyElements.push(
                                                    { data: { id: compoundId, label: compoundId, type: "chemical" }, classes: "chemical-node" },
                                                    { data: { id: `${compoundId}-${targetNodeId}`, source: compoundId, target: targetNodeId, type: "interaction", label: `pChEMBL: ${value} (${model})` } }
                                                );
                                            } else {
                                                console.error("Cytoscape instance (cy) is not initialized yet.");
                                            }
                                        }
                                    });
                                });
                            });

                            if (typeof cy !== "undefined" && cyElements.length) {
                                cy.add(cyElements);
                                cy.style()
                                    .selector(".chemical-node")
                                    .style({
                                        shape: "triangle",
                                        "background-color": "#a9d3f5",
                                        label: "data(label)",
                                        "text-wrap": "wrap",
                                        "text-max-width": "100px",
                                        "text-valign": "center",
                                        "text-halign": "center",
                                        color: "#000",
                                        "font-size": "18px",
                                        "border-width": 2,
                                        "border-color": "#000"
                                    })
                                    .update();
                                cy.style()
                                    .selector('edge[type="interaction"]')
                                    .style({
                                        label: "data(label)",
                                        "text-rotation": "autorotate",
                                        "text-margin-y": -10,
                                        "font-size": "12px",
                                        color: "#000"
                                    })
                                    .update();
                                cy.layout({ name: "cose", animate: true }).run();
                            }
                        } else {
                            console.error("Unexpected API response format:", response);
                            alert("Error: Unexpected response format from server.");
                        }
                    },
                    error: () => alert("Error fetching predictions.")
                });
            },
            error: () => alert("Error fetching model to MIE mapping.")
        });
    });

    function updateCytoscapeSubset() {
        if (typeof cy === "undefined") return;
        const selectedRows = $("#compound_table tbody tr.selected");
        if (!selectedRows.length) {
            cy.elements().show();
            cy.fit(cy.elements(), 50);
            return;
        }
        let selectedCompoundIds = [];
        selectedRows.each(function () {
            const compoundId = $(this).find("td:first").text().trim();
            if (compoundId) selectedCompoundIds.push(compoundId);
        });
        let subsetNodes = cy.collection();
        selectedCompoundIds.forEach(compoundId => {
            const node = cy.getElementById(compoundId);
            if (node.nonempty()) {
                let visited = cy.collection();
                const queue = [node];
                while (queue.length) {
                    const current = queue.shift();
                    if (!visited.contains(current)) {
                        visited = visited.union(current);
                        current.outgoers("node").forEach(n => {
                            if (!visited.contains(n)) queue.push(n);
                        });
                    }
                }
                subsetNodes = subsetNodes.union(visited);
            }
        });
        const subsetEdges = cy.edges().filter(edge => {
            return subsetNodes.contains(edge.source()) && subsetNodes.contains(edge.target());
        });
        cy.elements().hide();
        subsetNodes.show();
        subsetEdges.show();
        cy.fit(subsetNodes, 50);
    }
});
