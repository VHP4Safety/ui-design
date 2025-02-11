$(document).ready(function () {
    $("#fetch_predictions").on("click", function () {
        const smilesList = [];
        const mieQuery = $("#compound-container").data("mie-query");

        $.ajax({
            url: "/get_case_mie_model",
            type: "GET",
            data: { mie_query: mieQuery },
            success: function (modelToMIE) {
                console.log("Model to MIE Mapping:", modelToMIE);
                $("#compound_table tbody tr").each(function () {
                    const imgElement = $(this).find("td:eq(1) img");
                    if (imgElement.length) {
                        const smiles = imgElement.attr("alt").trim();
                        if (smiles) {
                            smilesList.push(smiles);
                        }
                    }
                });

                console.log("Extracted SMILES List:", smilesList);

                const models = Object.keys(modelToMIE);
                if (models.length === 0) {
                    alert("Error: No models available for prediction.");
                    return;
                }

                const requestData = {
                    smiles: smilesList,
                    models: models,
                    metadata: {}, 
                    threshold: 6.5
                };
                console.log("REQUEST DATA:");
                console.log(requestData);

                $.ajax({
                    url: "/get_predictions",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify(requestData),
                    success: function (response) {
                        console.log("API Response:", response);
                        const tableBody = $("#predictions_table tbody");
                        tableBody.empty();

                        if (Array.isArray(response)) {
                            const groupedPredictions = response.reduce((acc, prediction) => {
                                const smiles = prediction.smiles;
                                if (!acc[smiles]) {
                                    acc[smiles] = [];
                                }
                                acc[smiles].push(prediction);
                                return acc;
                            }, {});

                            Object.entries(groupedPredictions).forEach(([smiles, predictions]) => {
                                predictions.forEach(prediction => {
                                    Object.entries(prediction).forEach(([model, value]) => {
                                        if (model !== "smiles" && parseFloat(value) >= 6.5) {
                                            const compoundName = compoundMapping[smiles] || smiles; // Get compound name

                                            tableBody.append(`
                                                <tr>
                                                    <td>${compoundName}</td>
                                                    <td><a href="https://example.com">${model}</a></td>
                                                    <td>${value}</td>
                                                </tr>
                                            `);
                                            // Add new chemical nodes and edges
                                            if (cy) {
                                                const targetNodeId = `https://identifiers.org/aop.events/${modelToMIE[model]}`;
                                                cy.add([
                                                    { data: { id: compoundName, label: compoundName, type: "chemical" }, classes: "chemical-node" }, // Use compound name instead of SMILES
                                                    { data: { id: `${compoundName}-${targetNodeId}`, source: compoundName, target: targetNodeId, type: "interaction", label: `pChEMBL: ${value} (${model})` } }
                                                ]);
                                                cy.style()
                                                    .selector(".chemical-node")
                                                    .style({
                                                        "shape": "triangle",  // Make chemical nodes triangular
                                                        "background-color": "#a9d3f5", // Blue color
                                                        "label": "data(label)",
                                                        "text-wrap": "wrap",  // Wrap text inside node
                                                        "text-max-width": "100px", // Keep text readable
                                                        "text-valign": "center",
                                                        "text-halign": "center",
                                                        "color": "#000",
                                                        "font-size": "18px",
                                                        "border-width": 2,
                                                        "border-color": "#000"
                                                    })
                                                    .update();
                                                cy.style()
                                                    .selector('edge[type="interaction"]')
                                                    .style({
                                                        "label": "data(label)",
                                                        "text-rotation": "autorotate",
                                                        "text-margin-y": -10,  // Adjust the position of the label
                                                        "font-size": "12px",
                                                        "color": "#000"
                                                    })
                                                    .update();
                                                cy.layout({ name: "cose", animate: true }).run();
                                            } else {
                                                console.error("Cytoscape instance (cy) is not initialized yet.");
                                            }
                                        }
                                    });
                                });
                            });

                            cy.layout({ name: "cose", animate: true }).run();
                        } else {
                            console.error("Unexpected API response format:", response);
                            alert("Error: Unexpected response format from server.");
                        }
                    },
                    error: function () {
                        alert("Error fetching predictions.");
                    }
                });
            },
            error: function () {
                alert("Error fetching model to MIE mapping.");
            }
        });
    });
});
