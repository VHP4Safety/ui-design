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
            layout: { name: "cose", animate: true },
            style: [
            { selector: "node", style: {
                "width": 150, "height": 150,
                "background-color": ele => ele.data("is_mie") ? "#ccffcc" : ele.data("is_ao") ? "#ffe6e6" : "#ffff99",
                "label": "data(label)", "text-wrap": "wrap", "text-max-width": "120px",
                "text-valign": "center", "text-halign": "center", "color": "#000",
                "font-size": "18px", "border-width": 2, "border-color": "#000"
            }},
            { selector: "edge", style: {
                "curve-style": "bezier", "width": 3, "line-color": "#000",
                "opacity": 0.8, "target-arrow-shape": "triangle", "target-arrow-color": "#000",
                "label": "data(ker_label)", "text-margin-y": -15, "text-rotation": "autorotate",
                "font-size": "30px", "font-weight": "bold", "color": "#000"
            }}
            ]
        });

    }

    const mies = document.getElementById("compound-container").dataset.mies;
    fetchAOPData(mies).then(data => renderAOPNetwork(data));
    
    $("#reset_layout").on("click", function () {
        cy.animate({ fit: { padding: 30 }, duration: 500 });
        cy.layout({ name: "cose", animate: true }).run();
    });
});
