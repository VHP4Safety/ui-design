function positionNodes(cy) {
    cy.layout({
        name: 'cose',
        idealEdgeLength: 100,
        gravity: 2,
        nodeRepulsion: 100,
        animate: false,
    }).run();
    cy.fit();
}