// BioDataFuse functionalities
async function addBdfMolmedb(cids) {
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
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
    }
}

document.getElementById('query_opentargets').addEventListener('click', async () => {
    cids = getAllCIDs();
    await addBdfMolmedb(cids);
});

