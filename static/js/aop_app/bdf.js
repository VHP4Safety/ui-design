// Utility function to fetch data from endpoint
async function fetchData(endpoint, params) {
    try {
        const queryString = new URLSearchParams(params).toString();
        const response = await fetch(`${endpoint}?${queryString}`, { method: 'GET' });
        if (!response.ok) {
            throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
        }

        // Get raw response text and clean NaN values
        const text = await response.text();
        const cleanText = text.replace(/NaN/g, 'null');
        const data = JSON.parse(cleanText);

        return data;
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
        return null;
    }
}

// Function to fetch BridgeDb data
async function fetchBridgeDbXref(identifiers, inputSpecies = "Human", inputDatasource = "PubChem Compound", outputDatasource = "All") {
    try {
        const response = await fetch('/get_bridgedb_xref', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                identifiers,
                input_species: inputSpecies,
                input_datasource: inputDatasource,
                output_datasource: outputDatasource
            })
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch BridgeDb data: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        return data.bridgedb_df || [];
    } catch (error) {
        console.error('Error fetching BridgeDb data:', error);
        return [];
    }
}

// Function to handle OpenTargets query
async function addBdfOT(cids) {
    const data = await fetchData('/add_bdf_opentargets', { cids: cids.join(',') });
    if (data) {
        populateBdfTableBgee(data);
    }
}

// Function to handle OpenTargets query with BridgeDb data
async function addBdfOTWithBridgeDb(cids) {
    const bridgedbData = await fetchBridgeDbXref(cids, "Human", "PubChem Compound", "All");
    try {
        const params = new URLSearchParams({ bridgedb_data: JSON.stringify(bridgedbData) });
        const response = await fetch(`/add_bdf_opentargets?${params.toString()}`, { method: 'GET' });
        const text = await response.text(); // Get raw response text
        console.log("Raw response:", text); // Log raw response for debugging

        const sanitizedText = text.replace(/\bNaN\b/g, 'null'); // Replace NaN with null
        const data = JSON.parse(sanitizedText); // Parse sanitized JSON
        populateBdfTableOT(data);
    } catch (error) {
        console.error('Error fetching OpenTargets data:', error);
    }
}

// Function to handle Bgee query
async function addBdfBgee(genes) {
    const data = await fetchData('/add_bdf_bgee', { genes: genes.join(',') });
    if (data) {
        populateBdfTableBgee(data);
    }
}

// Function to handle Bgee query with BridgeDb data
async function addBdfBgeeWithBridgeDb(genes) {
    const bridgedbData = await fetchBridgeDbXref(genes, "Human", "Ensembl", "All");
    try {
        const response = await fetch('/add_bdf_bgee', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bridgedb_data: bridgedbData })
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch Bgee data: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        populateBdfTableBgee(data);
    } catch (error) {
        console.error('Error fetching Bgee data:', error);
    }
}

// Event listener for OpenTargets query button
document.getElementById('query_opentargets').addEventListener('click', async () => {
    const cids = getAllCIDs();
    await addBdfOTWithBridgeDb(cids);
});

// Event listener for Bgee query button
document.getElementById('query_bgee').addEventListener('click', async () => {
    const genes = await getAllGenes();
    await addBdfBgeeWithBridgeDb(genes);
});

// Function to populate the OpenTargets table
function populateBdfTableOT(data) {
    const table = $("#compound_table");
    const tableHead = table.find("thead tr");
    const tableBody = table.find("tbody");

    // Add header if not already present
    if (!tableHead.find("th:contains('Therapeutic Areas')").length) {
        tableHead.append('<th>Therapeutic Areas</th>');
    }

    const matchedRows = new Set();

    data.forEach(row => {
        const compoundRow = findCompoundRow(tableBody, row.identifier);
        if (compoundRow.length) {
            matchedRows.add(row.identifier);
            const therapeuticAreas = formatTherapeuticAreas(row.OpenTargets_diseases || []);
            compoundRow.append(`<td>${therapeuticAreas}</td>`);
        }
    });

    // Add empty cells for unmatched rows
    addEmptyCellsForUnmatchedRows(tableBody, matchedRows);
}

// Function to populate the Bgee table
function populateBdfTableBgee(data) {
    const tableBody = $("#gene_table tbody");

    data.forEach(row => {
        const geneRow = tableBody.find(`tr[data-gene="${row.identifier}"]`);
        if (geneRow.length) {
            const geneExpressionLevs = formatGeneExpressionLevs(row.Bgee_gene_expression_levels || []);
            geneRow.find(".gene-expression-cell").html(geneExpressionLevs);
        }
    });

    console.log("Bgee data populated in the gene table.");
}

// Helper function to find a compound row by identifier
function findCompoundRow(tableBody, identifier) {
    return tableBody.find("tr").filter(function () {
        return $(this).find(".cid-link").text().trim() === identifier;
    });
}

// Helper function to format therapeutic areas
function formatTherapeuticAreas(diseases) {
    return diseases
        .flatMap(diseaseObj => {
            const areas = diseaseObj.therapeutic_areas || "";
            return areas.split(",").map(area => {
                const [id, name] = area.split(":").map(part => part.trim());
                return id
                    ? `<a href="https://purl.obolibrary.org/onto/${id}" title="${name || ''}" target="_blank" style="position: relative; z-index: 10;">${name || id}</a>`
                    : null;
            });
        })
        .filter(area => area)
        .join(", ");
}

// Helper function to format gene expression levels
function formatGeneExpressionLevs(data) {
    return data
        .map(entry => {
            const prettyJson = JSON.stringify(entry, null, 2);
            return `<div class="gene-expression-entry"><pre>${prettyJson}</pre></div>`;
        })
        .join("");
}

// Helper function to add empty cells for unmatched rows
function addEmptyCellsForUnmatchedRows(tableBody, matchedRows) {
    tableBody.find("tr").each(function () {
        const cid = $(this).find(".cid-link").text().trim();
        if (!matchedRows.has(cid)) {
            $(this).append('<td></td>');
        }
    });
}

