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
                console.log("Model to Protein Info Mapping:", modelToProteinInfo);
            }
        });
    }
});

$(document).ready(() => {
    // Load the compound table with clickable links.
    const qid = $("#compound-container").data("qid");
    $.getJSON(`/get_compounds/${qid}`, data => {
        document.getElementById("loading_compound").style.display = "none";
        const tableBody = $("#compound_table tbody").empty();
        data.forEach(option => {
            const encodedSMILES = encodeURIComponent(option.SMILES);
            compoundMapping[option.SMILES] = { term: option.Term, url: `/compound/${option.ID}`, target: "_blank" };
            tableBody.append(`
                <tr>
                    <td>
                        <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi=${encodedSMILES}" 
                             alt="${option.SMILES}" />
                        <br />
                        <a href="${compoundMapping[option.SMILES].url}" class="compound-link" target="_blank">${option.Term}</a>
                    </td>
                </tr>
            `);
        });
    });

    // Enable row selection to filter the Cytoscape network by compound.
    $("#compound_table").on("click", "tbody tr", function (e) {
        if ($(e.target).is("a") || $(e.target).is("button")) return; // Prevent row click when clicking on a link or button
        if (fetched_preds == false) return;
        $(this).toggleClass("selected");
        updateCytoscapeSubset();
        positionNodes(cy);
    });

    // Handle compound link
    $("#compound_table").on("click", ".compound-link", function (e) {
        const url = $(this).attr("href");
        $("#compound-frame").attr("src", url);
        positionNodes(cy);
    });

    // Fetch predictions and update the table and Cytoscape.
    $("#fetch_predictions").on("click", () => {
        if (!genesVisible) {
            genesVisible = true;
            loadAndShowGenes();
        }
        document.getElementById("loading_pred").style.display = "block";
        const smilesList = [];
        const mieQuery = $("#compound-container").data("mie-query");
        $.ajax({
            url: "/get_case_mie_model",
            type: "GET",
            data: { mie_query: mieQuery },
            success: modelToMIE => {
                console.log("Model to MIE Mapping:", modelToMIE);
                $("#compound_table tbody tr").each((_, tr) => {
                    const img = $(tr).find("td img");
                    const smiles = img.attr("alt") && img.attr("alt").trim();
                    if (smiles) smilesList.push(smiles);
                });
                console.log("Extracted SMILES List:", smilesList);

                const models = Object.keys(modelToMIE);
                if (!models.length) return alert("Error: No models available for prediction.");

                const thresholdElement = document.getElementById("threshold_pchembl");
                const thresholdValue = parseFloat(thresholdElement ? thresholdElement.value : "6.5");
                const requestData = { smiles: smilesList, models, metadata: {}, threshold: thresholdValue };
                console.log("REQUEST DATA:", requestData);

                $.ajax({
                    url: "/get_predictions",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify(requestData),
                    success: response => {
                        document.getElementById("loading_pred").style.display = "none";
                        console.log("API Response:", response);
                        populateQsprPredMies(cy, compoundMapping, modelToProteinInfo, modelToMIE, response);
                        if (fetched_preds === false) fetched_preds = true;
                    },
                    error: () => alert("Error fetching predictions.")
                });
            },
            error: () => alert("Error fetching model to MIE mapping.")
        });
    });
});

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