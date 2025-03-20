// async function to collect all genes
async function getAllGenes() {
    var cy = window.cy;

    if (!genesVisible) {
        console.log("Showing genes");
        await toggleGeneView(cy);
        await positionNodes(cy);
    }

    const genes = [];
    cy.nodes('.ensembl-node').forEach(node => {
        const geneLabel = node.data('label');
        if (!genes.includes(geneLabel)) {
            genes.push(geneLabel);
        }
    });

    console.log('retrieved genes', genes);
    return genes;
}

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

                // Populate the gene table
                populateGeneTable(cy);
            } catch (error) {
                console.warn("Error processing elements:", error);
            }
        })
        .catch(error => {
            console.warn("Error fetching genes data:", error);
        });
}

// Function to populate the gene table with Ensembl nodes
function populateGeneTable(cy) {
    const tableBody = $("#gene_table tbody").empty();
    cy.nodes(".ensembl-node").forEach(node => {
        const geneLabel = node.data("label");
        tableBody.append(`
            <tr data-gene="${geneLabel}">
                <td>${geneLabel}</td>
                <td class="gene-expression-cell"></td>
            </tr>
        `);
    });
    console.log("Gene table populated with Ensembl nodes.");
}