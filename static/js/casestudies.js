// casestudies.js
// JavaScript for Thyroid Case Study page

// --- State management ---
let currentQuestion = "Q1"; // Default to question Q1
let currentProcessStep = "Kinetics"; // Default process step

// --- Content storage ---
let step1Contents = {};
let step2Contents = {};
let step3Contents = {};
let contentLoaded = false;

// Helper to render step buttons from array
function renderStepButtons(steps, btnClass, onClickFn) {
  return (
    `<div class="step-buttons">` +
    steps
      .map(
        (step) =>
          `<button class="btn ${btnClass}" onclick="${onClickFn}('${
            step.value
          }')"><b>${step.label}</b>${
            step.description ? "<br />" + step.description : ""
          }</button>`
      )
      .join("") +
    `</div>`
  );
}

function renderToolButtons(tools) {
  return (
    `<div class="step-buttons">` +
    tools
      .map(
        (tool) =>
          `<button class="btn step3"><b>${tool.label}</b>${
            tool.description ? "<br />" + tool.description : ""
          }</button>`
      )
      .join("") +
    `</div>`
  );
}

// --- Content update functions ---
function updateStep1Content() {
  if (!contentLoaded) return;
  document.getElementById("step1-content").innerHTML =
    `<h1>${step1Contents.navTitle}</h1><p>${step1Contents.navDescription}</p>` +
    renderStepButtons(step1Contents.questions, "step1", "selectQuestion");
  document.getElementById("step1-bottom-content").innerHTML =
    step1Contents.content;
}
function updateStep2Content() {
  if (!contentLoaded) return;
  const nav = step2Contents[currentQuestion];
  document.getElementById("step2-content").innerHTML =
    `<h1>${nav.navTitle}</h1><p>${nav.navDescription}</p>` +
    renderStepButtons(nav.steps, "step2", "selectProcessStep");
  document.getElementById("step2-bottom-content").innerHTML = nav.content;
}
function updateStep3Content() {
  if (!contentLoaded) return;
  const step = step3Contents[currentQuestion][currentProcessStep];
  document.getElementById("step3-content").innerHTML =
    `<h1><span class='kinetics-bold'>${step.navTitle}</span></h1><p class='step-desc'>${step.navDescription}</p>` +
    renderToolButtons(step.tools);
  document.getElementById("step3-bottom-content").innerHTML = step.content;
}

// --- Navigation logic ---
function selectQuestion(q) {
  currentQuestion = q;
  currentProcessStep = "Kinetics";
  updateStep2Content();
  updateStep3Content();
  goToStep(2);
}
function selectProcessStep(step) {
  currentProcessStep = step;
  updateStep3Content();
  goToStep(3);
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

function loadCaseStudyContent() {
  const caseStudy = getCaseStudyNameFromUrl();
  fetch(`/static/data/${caseStudy}_content.json`)
    .then((res) => res.json())
    .then((content) => {
      step1Contents = content.step1Contents;
      step2Contents = content.step2Contents;
      step3Contents = content.step3Contents;
      contentLoaded = true;
      currentQuestion = "Q1";
      updateStep1Content();
      updateBreadcrumb(1);
      updateStep2Content();
      updateStep3Content();
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
  if (step === 2) {
    el.innerHTML = `<a href="#" onclick="goToStep(1); return false;">${caseStudyName}</a> <span> &rarr; </span> <span>Regulatory Question ${currentQuestion}</span>`;
    el.classList.add("visible");
  } else if (step === 3) {
    el.innerHTML = `<a href=\"#\" onclick=\"goToStep(1); return false;\">${caseStudyName}</a> <span>&rarr;</span> <a href=\"#\" onclick=\"goToStep(2); return false;\">Regulatory Question ${currentQuestion}</a> <span>&rarr;</span> <span>${currentProcessStep}</span>`;
    el.classList.add("visible");
  } else {
    el.innerHTML = "";
    el.classList.remove("visible");
  }
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
  if (step === 2) updateStep2Content();
  if (step === 3) updateStep3Content();
}

// --- Load content from JSON and initialize ---
document.addEventListener("DOMContentLoaded", function () {
  loadCaseStudyContent();
});
