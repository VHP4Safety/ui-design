let compoundMapping = {};

document.addEventListener("DOMContentLoaded", function () {
    const qid = document.getElementById("compound-container").dataset.qid; // Get qid from data attribute
    $.getJSON(`/get_compounds/${qid}`, function (data) {
        const tableBody = $("#compound_table tbody");
        tableBody.empty();
        data.forEach((option) => {
            const encodedSMILES = encodeURIComponent(option.SMILES);
            compoundMapping[option.SMILES] = option.Term;
            tableBody.append(`
                <tr>
                    <td><a href="/compound/${option.ID}">${option.Term}</a></td>
                    <td><img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=1&annotate=cip&r=0&smi=${encodedSMILES}" 
                         alt="${option.SMILES}" /></td>
                </tr>
            `);
        });
    });
});
