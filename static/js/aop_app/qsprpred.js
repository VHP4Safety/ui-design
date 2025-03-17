let compoundMapping = {};
let modelToProteinInfo = {};
let fetched_preds = false;
var cy = cytoscape({
    container: document.getElementById('cy')
});

// Load the model to protein name mapping
$.ajax({
    url: "/static/data/caseMieModel.csv",
    dataType: "text",
    success: data => {
        Papa.parse(data, {
            header: true,
            skipEmptyLines: true,
            complete: results => {
                results.data.forEach(row => {
                    const model = row["qsprpred_model"];
                    const proteinName = row["protein name uniprot"];
                    const uniprotId = row["uniprot ID inferred from qspred name"];
                    modelToProteinInfo[model] = { proteinName, uniprotId };
                });

            }
        });
    }
});

$(document).ready(() => {
    // Fetch predictions and update the table and Cytoscape.
    $("#fetch_predictions").on("click", () => {
        if (!genesVisible) {
            genesVisible = true;
            toggleGeneView(cy);
            positionNodes(cy);
        }
        //document.getElementById("loading_pred").style.display = "block";
        const smilesList = [];
        const mieQuery = $("#compound-container").data("mie-query");
        $.ajax({
            url: "/get_case_mie_model",
            type: "GET",
            data: { mie_query: mieQuery },
            success: modelToMIE => {
                $("#compound_table tbody tr").each((_, tr) => {
                    const img = $(tr).find("td img");
                    const smiles = img.attr("alt") && img.attr("alt").trim();
                    if (smiles) smilesList.push(smiles);
                });
                const models = Object.keys(modelToMIE);
                if (!models.length) return alert("Error: No models available for prediction.");
                const thresholdElement = document.getElementById("threshold_pchembl");
                const thresholdValue = parseFloat(thresholdElement ? thresholdElement.value : "6.5");
                const requestData = { smiles: smilesList, models, metadata: {}, threshold: thresholdValue };
                $.ajax({
                    url: "/get_predictions",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify(requestData),
                    success: response => {
                        //document.getElementById("loading_pred").style.display = "none";
                        populateQsprPredMies(cy, compoundMapping, modelToProteinInfo, modelToMIE, response);
                        if (fetched_preds === false) fetched_preds = true;
                    },
                    error: () => alert("Error fetching predictions.")
                });
            },
            error: () => alert("Error fetching model to MIE mapping.")
        });
    });
})

function populateQsprPredMies(cy, compoundMapping, modelToProteinInfo, modelToMIE, response) {
    const table = $("#compound_table");
    const tableHead = table.find("thead tr");
    const tableBody = table.find("tbody");

    console.log("populateQsprPredMies called with response:", response);

    if (!tableHead.find("th:contains('pChEMBL Target')").length) {
        tableHead.append(`
            <th>pChEMBL Target</th>
            <th>Predicted pChEMBL</th>
        `);
        console.log("Added new columns to table header.");
    }

    if (Array.isArray(response)) {
        const grouped = response.reduce((acc, pred) => {
            const s = pred.smiles;
            (acc[s] = acc[s] || []).push(pred);
            return acc;
        }, {});

        console.log("Grouped response by SMILES:", grouped);

        const matchedRows = new Set();
        const cyElements = [];

        Object.entries(grouped).forEach(([smiles, predictions]) => {
            console.log("Processing SMILES:", smiles, "with predictions:", predictions);

            const compound = compoundMapping[smiles];
            const compoundId = (compound ? compound.term : smiles).trim();

            console.log("Mapped compound:", compound, "Normalized Compound ID:", compoundId);

            const compoundRow = tableBody.find("tr").filter(function () {
                const rowSmiles = $(this).find("td img").attr("alt")?.trim();
                console.log("Checking row SMILES:", rowSmiles, "against SMILES:", smiles);
                return rowSmiles === smiles;
            });

            console.log("Found compoundRow for SMILES:", smiles, "Row:", compoundRow);

            const targetCells = [];
            const pChEMBLCells = [];

            predictions.forEach(prediction => {
                Object.entries(prediction).forEach(([model, value]) => {
                    console.log("Processing prediction model:", model, "value:", value);

                    if (parseFloat(value) >= 6.5) {
                        const proteinInfo = modelToProteinInfo[model] || { proteinName: "Unknown Protein", uniprotId: "" };
                        const proteinLink = proteinInfo.uniprotId ? `<a href="https://www.uniprot.org/uniprotkb/${proteinInfo.uniprotId}" target="_blank">${proteinInfo.proteinName}</a>` : proteinInfo.proteinName;

                        console.log("Protein info for model:", model, "Protein Info:", proteinInfo);

                        targetCells.push(`${proteinLink} (${model})`);
                        pChEMBLCells.push(value);

                        const targetNodeId = `https://identifiers.org/aop.events/${modelToMIE[model]}`;
                        cyElements.push(
                            { data: { id: compoundId, label: compoundId, type: "chemical", smiles: smiles }, classes: "chemical-node" },
                            { data: { id: `${compoundId}-${targetNodeId}-${model}`, source: compoundId, target: `uniprot_${proteinInfo.uniprotId}`, value: value, type: "interaction", label: `pChEMBL: ${value} (${model})` } }
                        );
                    }
                });
            });

            if (compoundRow.length) {
                matchedRows.add(smiles);
                console.log("Appending data to existing row for SMILES:", smiles);
                compoundRow.append(`
                    <td>${targetCells.join('<br>')}</td>
                    <td>${pChEMBLCells.join('<br>')}</td>
                `);
            } else {
                console.warn("No matching row found for SMILES:", smiles);
            }
        });

        tableBody.find("tr").each(function () {
            const rowSmiles = $(this).find("td img").attr("alt")?.trim();
            if (!matchedRows.has(rowSmiles)) {
                console.log("Appending empty columns for unmatched SMILES:", rowSmiles);
                $(this).append(`
                    <td></td>
                    <td></td>
                `);
            }
        });

        console.log("Final Cytoscape elements to add:", cyElements);

        const isMieNodes = cy.nodes().filter(node => node.data("is_mie")).toArray().map(node => node.id());

        $.ajax({
            url: `/add_qsprpred_compounds`,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ is_mie_nodes: isMieNodes, compound_mapping: compoundMapping, model_to_protein_info: modelToProteinInfo, model_to_mie: modelToMIE, response: response, cy_elements: cyElements }),
            success: updatedCyElements => {
                if (Array.isArray(updatedCyElements)) {
                    console.log("Successfully updated Cytoscape elements:", updatedCyElements);
                    cy.add(updatedCyElements);
                    positionNodes(cy);
                } else {
                    console.error("Unexpected API response format:", updatedCyElements);
                    alert("Error: Unexpected response format from server.");
                }
            },
            error: (jqXHR, textStatus, errorThrown) => {
                console.error("Error adding qsprpred compounds:", textStatus, errorThrown);
                alert(`Error adding qsprpred compounds: ${textStatus} - ${errorThrown}`);
            }
        });
    } else {
        console.error("Response is not an array:", response);
    }
}