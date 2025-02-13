function positionNodes(cy) {


    cy.layout({
        name: 'cose',
        animate: true
    }).run();
    cy.fit();
}


