document.addEventListener('DOMContentLoaded', function() {
    handleDataTypeChange();
});

function handleDataTypeChange() {
    var selectedValue = document.getElementById('data-type-dropdown').value;
    var dataSections = document.getElementsByClassName('data-section');
    
    for (var i = 0; i < dataSections.length; i++) {
        dataSections[i].style.display = 'none';
    }
    
    if (selectedValue === 'qsprpred_opt') {
        document.getElementById('qsprpred').style.display = 'block';
        return;
    } else if (selectedValue === 'qaop_div') {
        document.getElementById('qaop_div').style.display = 'block';
        return;
    }
    // Add more conditions here for other data types
}
