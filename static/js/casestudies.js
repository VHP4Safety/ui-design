// casestudies.js
// JavaScript for Individual Case Study pages

// --- State management ---
let currentStep1Value = "Q1";
let currentStep2Value = "Kinetics";
let currentStep3Value = "Oral";
let currentStep4Value = "";
let currentStep5Value = "";
let currentStep6Value = "";

// --- Content storage ---
let step1Contents = {};
let step2Contents = {};
let step3Contents = {};
let step4Contents = {};
let step5Contents = {};
let step6Contents = {};

let contentLoaded = false;

function stepTypeToColor(type) {
  color = "card-button-vhpblue"
  if (type == "workflow step" || type == "workflow-step") {
    color = "card-button-vhplight-green"
  } else if (type == "workflow substep" || type == "workflow-substep") {
    color = "card-button-vhplight-purple"
  } else if (type == "process flow step" || type == "process-flow-step") {
    color = "card-button-vhpblue"
  } else if (type == "regulatory question" || type == "regulatory-question") {
    color = "card-button-vhppink"
  } else if (type == "tool") {
    color = "card-button-vhplight-blue"
  } else {
    console.log("UNKNOWN STEP TYPE: " + type)
  }
  return color
}

// Helper to render step buttons from array
function renderStepButtons(steps, btnClass, onClickFn) {
  return (
    `<div class="row py-3">` +
    steps
      .map(
        (step) =>
        `
        <div class="col-md pb-2">
        <div class="card card-button ${ stepTypeToColor(step.type) }${
            step.state && step.state == "disabled" ? " opacity-25" : ""
          }">
        <div class="card-body text-center${
            step.state && step.state == "disabled" ? " nav-link disabled" : ""
          }" onclick="${onClickFn}('${
            step.value
          }')"><b>${step.label}</b>${
            step.description ? "<br />" + step.description : ""
          }</div>
          </div>
          </div>
          `
      )
      .join("") +
    `</div>`
  );
}

function renderToolButtons(tools) {
  return (
    `<div class="row py-3">` +
    tools
      .map(
        (tool) =>
        `
        <div class="col-md pb-2">
        <div class="card card-button ${ stepTypeToColor(tool.type) }">
          <div class="card-body text-center"><b>${tool.label}</b>${
            tool.description ? "<br />" + tool.description : ""
          }${
            tool.id ? "<br /><a href=\"https://cloud.vhp4safety.nl/service/" + tool.id + ".html\">more info</a>" : ""
          }</div>
          </div>
          </div>`
      )
      .join("") +
    `</div>`
  );
}
// --- Content update functions ---
function updateStep1Content() {
  if (!contentLoaded) return;
  document.getElementById("step1-content").innerHTML =
    `<h1 class="text-vhpblue">${step1Contents.navTitle}</h1><p>${step1Contents.navDescription}</p>` +
    renderStepButtons(step1Contents.questions, "step1", "selectQuestion");
  document.getElementById("step1-bottom-content").innerHTML =
    buildAccordionHTML(step1Contents.content);
}
function updateStep2Content() {
  if (!contentLoaded) return;
  const nav = step2Contents[currentStep1Value];
  document.getElementById("step2-content").innerHTML =
    `<h1 class="text-vhpblue">${nav.navTitle}</h1><p>${nav.navDescription}</p>` +
    renderStepButtons(nav.steps, "step2", "selectProcessStep");
  document.getElementById("step2-bottom-content").innerHTML = buildAccordionHTML(nav.content);
}
function updateStep3Content() {
  if (!contentLoaded) return;
  if (!step3Contents[currentStep1Value]) return;
  const step = step3Contents[currentStep1Value][currentStep2Value];
  if (step.steps) {
    document.getElementById("step3-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderStepButtons(step.steps, "step3", "selectCaseStudyStep");
  } else if (step.tools) {
    document.getElementById("step3-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderToolButtons(step.tools);
  }
  document.getElementById("step3-bottom-content").innerHTML = buildAccordionHTML(step.content);
}
function updateStep4Content() {
  if (!contentLoaded) return;
  if (!step4Contents) return;
  if (!step4Contents[currentStep1Value]) return;
  if (!step4Contents[currentStep1Value][currentStep2Value]) return;
  if (!step4Contents[currentStep1Value][currentStep2Value][currentStep3Value]) return;
  const step = step4Contents[currentStep1Value][currentStep2Value][currentStep3Value];
  if (step.tools) {
    document.getElementById("step4-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderToolButtons(step.tools);
  } else if (step.steps) {
    document.getElementById("step4-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderStepButtons(step.steps);
  } else {
    document.getElementById("step4-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>`;
  }
  document.getElementById("step4-bottom-content").innerHTML = buildAccordionHTML(step.content);
}
function updateStep5Content() {
  if (!contentLoaded) return;
  if (!step5Contents) return;
  if (!step5Contents[currentQuestion]) return;
  if (!step5Contents[currentQuestion][currentProcessStep]) return;
  if (!step5Contents[currentQuestion][currentProcessStep][currentCaseStudyStep]) return;
  const step = step5Contents[currentQuestion][currentProcessStep][currentCaseStudyStep];
  if (step.tools) {
    document.getElementById("step5-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderToolButtons(step.tools);
  } else if (step.steps) {
    document.getElementById("step5-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderStepButtons(step.steps);
  } else {
    document.getElementById("step5-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>`;
  }
  document.getElementById("step5-bottom-content").innerHTML = buildAccordionHTML(step.content);
}
function updateStep6Content() {
  if (!contentLoaded) return;
  if (!step6Contents) return;
  if (!step6Contents[currentQuestion]) return;
  if (!step6Contents[currentQuestion][currentProcessStep]) return;
  if (!step6Contents[currentQuestion][currentProcessStep][currentCaseStudyStep]) return;
  const step = step6Contents[currentQuestion][currentProcessStep][currentCaseStudyStep];
  if (step.tools) {
    document.getElementById("step6-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderToolButtons(step.tools);
  } else if (step.steps) {
    document.getElementById("step6-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
      renderStepButtons(step.steps);
  } else {
    document.getElementById("step6-content").innerHTML =
      `<h1 class="text-vhpblue"><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>`;
  }
  document.getElementById("step6-bottom-content").innerHTML = buildAccordionHTML(step.content);
}

// --- Navigation logic ---
function selectQuestion(q) {
  currentStep1Value = q;
  currentStep2Value = "Kinetics";
  currentStep3Value = "Oral";
  updateStep2Content();
  updateStep3Content();
  updateStep4Content();
  goToStep(2);
}
function selectProcessStep(step) {
  currentStep2Value = step;
  updateStep3Content();
  goToStep(3);
}
function selectCaseStudyStep(step) {
  currentStep3Value = step;
  updateStep4Content();
  goToStep(4);
}

// Breadcrumb logic
toTitleCase = (str) => str.charAt(0).toUpperCase() + str.slice(1);

function getCaseStudyNameFromUrl() {
  // Assumes URL like /casestudies/<casestudy>
  const path = window.location.pathname;
  // Try to extract the case study name from the path
  // e.g. /casestudies/kidney or /casestudies/thyroid
  const match = path.match(/\/casestudies\/(thyroid|kidney|parkinson)/);
  if (match && match[1]) {
    return match[1];
  }
  // fallback: try query param ?case=xxx
  const params = new URLSearchParams(window.location.search);
  if (params.has("case")) {
    return params.get("case");
  }
  // fallback: default to 'thyroid'
  return "thyroid";
}

function getCaseStudyVersionFromUrl() {
  // Assumes URL like /casestudies/<casestudy>
  const params = new URLSearchParams(window.location.search);
  if (params.has("casestudybranch")) {
    return "refs/heads/" + params.get("casestudybranch");
  } else if (params.has("casestudycommit")) {
    return params.get("casestudycommit");
  }
  // fallback: default to 'thyroid'
  return "main";
}

function loadCaseStudyContent() {
  const caseStudy = getCaseStudyNameFromUrl();
  const caseStudyBranch = getCaseStudyVersionFromUrl();
  var data_url = `https://raw.githubusercontent.com/VHP4Safety/ui-casestudy-config/${caseStudyBranch}/${caseStudy}_content.json`;
  //var data_url_test = `https://raw.githubusercontent.com/johannehouweling/ui-casestudy-config/refs/heads/jh-content-structure/${caseStudy}_content.json`
  fetch(data_url)
    .then((res) => res.json())
    .then((content) => {
      step1Contents = content.step1Contents;
      step2Contents = content.step2Contents;
      step3Contents = content.step3Contents;
      step4Contents = content.step4Contents;
      contentLoaded = true;
      currentStep1Value = "Q1";
      updateStep1Content();
      updateBreadcrumb(1);
      updateStep2Content();
      updateStep3Content();
      updateStep4Content();
    });
}

function getCaseStudyDisplayName() {
  // Optionally, you could add a mapping here for pretty names
  const name = getCaseStudyNameFromUrl();
  if (step1Contents && step1Contents.navTitle) {
    return step1Contents.navTitle;
  }
  return toTitleCase(name) + " Case Study";
}

function updateBreadcrumb(step) {
  const el = document.getElementById("breadcrumbs");
  const caseStudyName = getCaseStudyDisplayName();

  // Reset breadcrumb
  el.innerHTML = "";

  // Helper to create items
  function addCrumb(label, onclick, isActive = false) {
    const li = document.createElement("li");
    li.classList.add("breadcrumb-item");

    if (isActive) {
      li.classList.add("active");
      li.classList.add("text-vhpblue")
      li.setAttribute("aria-current", "page");
      li.textContent = label;
    } else {
      const a = document.createElement("a");
      a.href = "#";
      a.textContent = label;
      a.onclick = function (e) {
        e.preventDefault();
        onclick();
      };
      li.appendChild(a);
    }

    el.appendChild(li);
  }

  // Build breadcrumb depending on step
  addCrumb("Case Studies", () => (window.location.href = "/casestudies"));
  if (step === 1) {
    addCrumb(caseStudyName, null, true);
  } else if (step === 2) {
    addCrumb(caseStudyName, () => goToStep(1));
    addCrumb(`Regulatory Question ${currentStep1Value}`, null, true);
  } else if (step === 3) {
    addCrumb(caseStudyName, () => goToStep(1));
    addCrumb(`Regulatory Question ${currentStep1Value}`, () => goToStep(2));
    addCrumb(currentStep2Value, null, true);
  } else if (step === 4) {
    addCrumb(caseStudyName, () => goToStep(1));
    addCrumb(`Regulatory Question ${currentStep1Value}`, () => goToStep(2));
    addCrumb(currentStep2Value, () => goToStep(3));
    addCrumb(currentStep3Value, null, true);
  }

  // Show/hide breadcrumb container
  const nav = el.closest("nav");
  if (step >= 2) {
    nav.classList.add("visible");
  } else {
    nav.classList.remove("visible");
  }
}

// Build Accordion HTML from JSON
function buildAccordionHTML(content) {
  if (!content || !Array.isArray(content)) return "";

  let html = `<div class="accordion" id="accordionMain">`;

  content.forEach((item, idx) => {
    const itemId = `accordionItem${idx}`;
    const isFirst = idx === 0;
    html += `
      <div class="accordion-item">
        <h2 class="accordion-header" id="heading${idx}">
          <button
            class="accordion-button ${!isFirst ? "collapsed" : ""}"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#${itemId}"
            aria-expanded="${isFirst}"
            aria-controls="${itemId}">
            ${item.section || `Section ${idx + 1}`}
          </button>
        </h2>
        <div
          id="${itemId}"
          class="accordion-collapse collapse ${isFirst ? "show" : ""}"
          aria-labelledby="heading${idx}"
          data-bs-parent="#accordionMain">
          <div class="accordion-body">
            ${item.description || ""}
          </div>
        </div>
      </div>`;
  });

  html += `</div>`;
  return html;
}

// Horizontal scroll navigation (snap to step)
function goToStep(step) {
  const wrapper = document.getElementById("stepsWrapper");
  const width = window.innerWidth;
  const scrollAmount = width * (step - 1);
  const duration = 1000; // ms
  const start = wrapper.scrollLeft;
  const change = scrollAmount - start;
  const startTime = performance.now();
  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }
  function animateScroll(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = easeInOutCubic(progress);
    wrapper.scrollLeft = start + change * ease;
    if (progress < 1) {
      requestAnimationFrame(animateScroll);
    }
  }
  requestAnimationFrame(animateScroll);
  updateBreadcrumb(step);
  if (step === 1) updateStep1Content();
  if (step === 2) updateStep2Content();
  if (step === 3) updateStep3Content();
  if (step === 4) updateStep4Content();
  if (step === 5) updateStep5Content();
  if (step === 6) updateStep6Content();
}

// --- Load content from JSON and initialize ---
document.addEventListener("DOMContentLoaded", function () {
  loadCaseStudyContent();
});
