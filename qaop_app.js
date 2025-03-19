// Define JSON objects for compound and gene data
let compound_json = [];
let gene_json = [];

// Function to populate a table from a JSON object
function populateTable(tableId, data) {
    const table = document.getElementById(tableId);
    table.innerHTML = ''; // Clear existing rows

    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        Object.values(row).forEach(value => {
            const td = document.createElement('td');
            td.textContent = value;
            tr.appendChild(td);
        });

        // Add edit and delete buttons
        const actionTd = document.createElement('td');
        actionTd.innerHTML = `
            <button onclick="editRow('${tableId}', ${index})">Edit</button>
            <button onclick="deleteRow('${tableId}', ${index})">Delete</button>
        `;
        tr.appendChild(actionTd);

        table.appendChild(tr);
    });
}

// Automatically refresh tables when data changes
function refreshTables() {
    populateTable('compound_table', compound_json);
    populateTable('gene_table', gene_json);
}

// Function to add a new row to a JSON object and update the table
function addRow(tableId, newRow) {
    if (tableId === 'compound_table') {
        compound_json.push(newRow);
    } else if (tableId === 'gene_table') {
        gene_json.push(newRow);
    }
    refreshTables();
}

// Function to edit a row in a JSON object and update the table
function editRow(tableId, index) {
    const newValue = prompt('Enter new value (comma-separated for multiple columns):');
    if (!newValue) return;

    const values = newValue.split(',');
    if (tableId === 'compound_table') {
        compound_json[index] = { ...compound_json[index], ...Object.fromEntries(values.map((v, i) => [Object.keys(compound_json[index])[i], v])) };
    } else if (tableId === 'gene_table') {
        gene_json[index] = { ...gene_json[index], ...Object.fromEntries(values.map((v, i) => [Object.keys(gene_json[index])[i], v])) };
    }
    refreshTables();
}

// Function to delete a row from a JSON object and update the table
function deleteRow(tableId, index) {
    if (tableId === 'compound_table') {
        compound_json.splice(index, 1);
    } else if (tableId === 'gene_table') {
        gene_json.splice(index, 1);
    }
    refreshTables();
}

// Example initialization
document.addEventListener('DOMContentLoaded', () => {
    // Example data
    compound_json = [
        { id: 1, name: 'Compound A', property: 'Property 1' },
        { id: 2, name: 'Compound B', property: 'Property 2' }
    ];
    gene_json = [
        { id: 1, name: 'Gene X', function: 'Function 1' },
        { id: 2, name: 'Gene Y', function: 'Function 2' }
    ];

    // Initial table population
    refreshTables();
});
