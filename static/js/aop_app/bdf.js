// BioDataFuse functionalities
async function addBdfOT(cids) {
    try {
        const queryString = new URLSearchParams({ cids: cids.join(',') }).toString();
        const response = await fetch(`/add_bdf_opentargets?${queryString}`, {
            method: 'GET',
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
        }
        const text = await response.text();
        const cleanText = text.replace(/NaN/g, 'null');
        const data = JSON.parse(cleanText);
        console.log(data);
        populateBdfTableOT(data);
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
    }
}

document.getElementById('query_opentargets').addEventListener('click', async () => {
    cids = getAllCIDs();
    await addBdfOT(cids);
});

function populateBdfTableOT(data) {
    console.log('data', data);
    const table = $("#compound_table");
    const tableHead = table.find("thead tr");
    const tableBody = table.find("tbody");

    if (!tableHead.find("th:contains('Therapeutic Areas')").length) {
        tableHead.append(`
            <th>Therapeutic Areas</th>
        `);
    }

    const matchedRows = new Set();

    data.forEach(row => {
        const compoundRow = tableBody.find("tr").filter(function () {
            return $(this).find(".cid-link").text().trim() === row.identifier;
        });

        if (compoundRow.length) {
            matchedRows.add(row.identifier);

            const therapeuticAreas = (row.OpenTargets_diseases || [])
                .flatMap(diseaseObj => {
                    const areas = diseaseObj.therapeutic_areas || "";
                    return areas.split(",").map(area => {
                        const [id, name] = area.split(":").map(part => part.trim());
                        return id
                            ? `<a href="https://purl.obolibrary.org/onto/${id}" title="${name || ''}" target="_blank" style="position: relative; z-index: 10;">${name || id}</a>`
                            : null; //TODO map curies to uris
                    });
                })
                .filter(area => area)
                .join(", ");

            compoundRow.append(`
                <td>${therapeuticAreas}</td>
            `);
        }
    });

    tableBody.find("tr").each(function () {
        const cid = $(this).find(".cid-link").text().trim();
        if (!matchedRows.has(cid)) {
            $(this).append(`
                <td></td>
            `);
        }
    });
}

