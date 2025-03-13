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
});

// function to collect al cids
function getAllCIDs() {
    const cids = [];
    for (const key in compoundMapping) {
        if (compoundMapping[key].cid) {
            cids.push(compoundMapping[key].cid);
        }
    }
    console.log('retrieved cids', cids);
    return cids;
}
