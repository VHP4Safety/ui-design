$(document).ready(function () {
    $("#fetch_predictions").on("click", function () {
        const smilesList = [];
        const modelToMIE = {
            "Q13224_RF_Model": "https://identifiers.org/aop.events/388",
            "P31644_RF_Model": "https://identifiers.org/aop.events/2039",
            "P41594_Allosteric_RF_Model": "https://identifiers.org/aop.events/2036",
            "P41594_Orthosteric_RF_Model": "https://identifiers.org/aop.events/2036",
            "Q13255_Allosteric_RF_Model": "https://identifiers.org/aop.events/2036",
            "P10827_RF_Model": "https://identifiers.org/aop.events/1656",
            "P10828_RF_Model": "https://identifiers.org/aop.events/1656"
        };

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

        const requestData = {
            smiles: smilesList,
            models: [ "P31644_RF_Model",
                "P41594_Allosteric_RF_Model", "P41594_Orthosteric_RF_Model",
                "Q13224_RF_Model", "Q13255_Allosteric_RF_Model"
            ],
            metadata: {}, threshold: 6.5
        };
        
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
                    response.forEach(prediction => {
                        Object.entries(prediction).forEach(([model, value]) => {
                            if (model !== "smiles" && parseFloat(value) >= 6.5) {
                                const smiles = prediction.smiles;
                                const compoundName = compoundMapping[smiles] || smiles; // Get compound name

                                tableBody.append(`
                                    <tr>
                                        <td>${compoundName}</td>
                                        <td>${model}</td>
                                        <td>${value}</td>
                                    </tr>
                                `);
                                // Add new chemical nodes and edges
                                if (cy) {
                                    cy.add([
                                        { data: { id: compoundName, label: compoundName, type: "chemical" }, classes: "chemical-node" }, // Use compound name instead of SMILES
                                        { data: { id: `${compoundName}-${modelToMIE[model]}`, source: compoundName, target: modelToMIE[model], type: "interaction" } }
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
                                    cy.layout({ name: "cose", animate: true }).run();
                                } else {
                                    console.error("Cytoscape instance (cy) is not initialized yet.");
                                }
                            }
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
    });
});
