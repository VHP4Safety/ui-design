document.addEventListener("DOMContentLoaded", function () {
    function fetchAOPData(mies) {
        return fetch(`/get_aop_network?mies=${encodeURIComponent(mies)}`)
            .then(response => response.json())
            .catch(error => {
                console.error("Error fetching AOP data:", error);
                return [];
            });
    }

    function renderAOPNetwork(elements) {
        document.getElementById("loading").style.display = "none";
        document.getElementById("cy").style.backgroundColor = "#FFFFFF";

        cy = cytoscape({
            container: document.getElementById("cy"),
            elements: elements.map(ele => ({
            data: {
                id: ele.id,
                ...ele.data
            }
            })),
            layout: { name: "cose" }, 
            style: [
            { selector: "node", style: {
                "width": 150, "height": 150,
                "background-color": ele => ele.data("is_mie") ? "#ccffcc" : ele.data("is_ao") ? "#ffe6e6" : ele.data("is_uniprot") ? "#ffff99" : ele.data("is_ensembl") ? "#ffcc99" : "#ffff99",
                "label": "data(label)", "text-wrap": "wrap", "text-max-width": "120px",
                "text-valign": "center", "text-halign": "center", "color": "#000",
                "font-size": "18px", "border-width": 2, "border-color": "#000"
            }},
            { selector: "edge[ker_label]", style: {
                "curve-style": "bezier", "width": 3, "line-color": "#000",
                "opacity": 0.8, "target-arrow-shape": "triangle", "target-arrow-color": "#000",
                "label": "data(ker_label)", "text-margin-y": -15, "text-rotation": "autorotate",
                "font-size": "30px", "font-weight": "bold", "color": "#000"
            }},
            { selector: ".uniprot-node", style: {
                "shape": "rectangle",
                "background-opacity": 0,
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000000",
                "font-size": "25px",
                "font-weight": "bold",
                "border-width": 0,
                "border-color": "transparent"
            }},
            { selector: ".ensembl-node", style: {
                "shape": "ellipse",
                "background-opacity": 0,
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000000",
                "font-size": "25px",
                "font-weight": "bold", 
                "border-width": 0,
                "border-color": "transparent"
            }},
            { selector: "edge[label]", style: {
                "label": "data(label)",
                "text-rotation": "autorotate",
                "text-margin-y": -10,
                "font-size": "22px",
                "color": "#000"
            }}
            ]
        });

        positionNodes(cy);

        // Add click event listener to nodes
        cy.on('tap', 'node', function(evt) {
            const node = evt.target;
            const url = node.id();
            if (node.hasClass('uniprot-node')) {
                window.open(`https://www.uniprot.org/uniprotkb/${url.replace('uniprot_', '')}`, '_blank');
            } else if (node.hasClass('ensembl-node')) {
                window.open(`https://identifiers.org/ensembl/${url.replace('ensembl_', '')}`, '_blank');
            } else if (url) {
                window.open(url, '_blank');
            }
        });

        // Call positionNodes every time nodes are added or removed
        cy.on('add', 'node', function() {
            positionNodes(cy);
        });

        // Add functionality to the "See Genes" button
        $("#see_genes").on("click", function () {
            $.ajax({
                url: "/static/data/caseMieModel.csv",
                dataType: "text",
                success: data => {
                    console.log("CSV data loaded successfully");
                    Papa.parse(data, {
                        header: true,
                        skipEmptyLines: true,
                        complete: results => {
                            console.log("CSV data parsed successfully");
                            const geneElements = [];
                            results.data.forEach(row => {
                                const mieId = "https://identifiers.org/aop.events/" + row["MIE/KE identifier in AOP wiki"];
                                const uniprotId = row["uniprot ID inferred from qspred name"];
                                const ensemblId = row["Ensembl"];
                                const proteinName = row["protein name uniprot"];
                                console.log(`MIE ID: ${mieId}, UniProt ID: ${uniprotId}, Ensembl ID: ${ensemblId}, Protein Name: ${proteinName}`);

                                if (mieId && uniprotId && ensemblId && cy.getElementById(mieId).length > 0) {
                                    console.log(`Processing MIE: ${mieId}, UniProt: ${uniprotId}, Ensembl: ${ensemblId}`);
                                    const uniprotNodeId = `uniprot_${uniprotId}`;
                                    const ensemblNodeId = `ensembl_${ensemblId}`;

                                    // Add UniProt node
                                    geneElements.push({
                                        data: {
                                            id: uniprotNodeId,
                                            label: uniprotId,
                                            type: "uniprot"
                                        },
                                        classes: "uniprot-node"
                                    });

                                    // Add Ensembl node
                                    geneElements.push({
                                        data: {
                                            id: ensemblNodeId,
                                            label: ensemblId,
                                            type: "ensembl"
                                        },
                                        classes: "ensembl-node"
                                    });

                                    // Add edge from MIE to UniProt
                                    geneElements.push({
                                        data: {
                                            id: `edge_${mieId}_${uniprotNodeId}`,
                                            source: mieId,
                                            target: uniprotNodeId,
                                            label: "part of"
                                        }
                                    });

                                    // Add edge from UniProt to Ensembl
                                    geneElements.push({
                                        data: {
                                            id: `edge_${uniprotNodeId}_${ensemblNodeId}`,
                                            source: uniprotNodeId,
                                            target: ensemblNodeId,
                                            label: "translates to"
                                        }
                                    });
                                }
                            });

                            cy.add(geneElements);
                            console.log(geneElements);
                        positionNodes(cy);
                            console.log("Gene elements added to Cytoscape");
                        }
                    });
                },
                error: (jqXHR, textStatus, errorThrown) => {
                    console.error("Error loading CSV data:", textStatus, errorThrown);
                }
            });
        });
    }

    const mies = document.getElementById("compound-container").dataset.mies;
    fetchAOPData(mies).then(data => renderAOPNetwork(data));
    
    $("#reset_layout").on("click", function () {
        cy.layout({ name: "cose" }).run();
        positionNodes(cy);
    });
});
