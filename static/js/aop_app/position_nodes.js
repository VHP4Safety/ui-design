function positionNodes(cy) {
    const canvas = document.getElementById("cy");
    const canvasWidth = canvas.clientWidth;
    const canvasHeight = canvas.clientHeight;
    const mieNodes = cy.nodes().filter(node => node.data("is_mie"));
    const aoNodes = cy.nodes().filter(node => node.data("is_ao"));
    const otherNodes = cy.nodes().filter(node => !node.data("is_mie") && !node.data("is_ao") && !node.connectedEdges().some(edge => aoNodes.contains(edge.target())));
    const uniprotNodes = cy.nodes().filter(node => node.data("type") === "uniprot");
    const ensemblNodes = cy.nodes().filter(node => node.data("type") === "ensembl");

    let x = 250;
    let y = 0;
    const mieNodeCount = mieNodes.length;
    const yIncrement = 300;
    mieNodes.forEach(node => {
        node.position({ x: x, y: y });
        y += yIncrement;
    });

    x = 630;
    y = 0;
    const visited = new Set();
    const queue = [...mieNodes];

    while (queue.length > 0) {
        const node = queue.shift();
        if (visited.has(node.id())) continue;
        visited.add(node.id());

        const connectedEdges = node.connectedEdges().filter(edge => edge.source().id() === node.id());
        let yOffset = 0;

        connectedEdges.forEach(edge => {
            const targetNode = edge.target();
            if (!visited.has(targetNode.id())) {
                targetNode.position({ x: x + 200, y: y + yOffset });
                queue.push(targetNode);
                yOffset += 300;
            }
        });

        x += 200;
    }

    x = canvasWidth - 10;
    y = 100;
    aoNodes.forEach(node => {
        node.position({ x: x, y: y });
        x += 0;
        y -= 300;
    });

    // Position compound nodes close to their connected MIE node
    const compoundNodes = cy.nodes().filter(node => node.is(".chemical-node"));
    x = 400;
    y = 200;
    compoundNodes.forEach(node => {
        const connectedMIE = node.connectedEdges().filter(edge => edge.target().data("is_mie")).map(edge => edge.target())[0];
        if (connectedMIE) {
            node.position({ x: x, y: y });
            y += 200;
        }
    });

    // Position UniProt nodes to the left of MIE nodes
    uniprotNodes.forEach(node => {
        node.position({ x: 100, y: y });
        y += 160
    });

    // Position Ensembl nodes to the left of UniProt nodes
    y = 0;
    ensemblNodes.forEach(node => {
        node.position({ x:0 - 200, y: y});
        y+= 160
    });

    cy.fit();
}
