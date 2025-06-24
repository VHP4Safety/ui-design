// casestudies.js
// JavaScript for Thyroid Case Study page

// --- State management ---
let currentQuestion = 1; // Default to question 1
let currentProcessStep = "Kinetics"; // Default process step

// --- Step 1 content for each question ---
const step1Contents = {
  top: `
    <h1>Thyroid Case Study</h1>
    <p>
      Description about how there are two regulatory questions for the thyroid case study. The user can either choose one of the two questions to explore or scroll down to read the overview of the case study.
    </p>
    <div class="step-buttons">
      <button class="btn step1" onclick="selectQuestion(1)">
        <b>Question 1: Compound Information</b><br />What information about a
        compound do we need to advise women in their early pregnancy to decide
        whether the compound can be used?
      </button>
      <button class="btn step1" onclick="selectQuestion(2)">
        <b>Question 2: Fetal Brain Development</b><br />Does compound Z
        influence the thyroid-mediated brain development in the fetus
        resulting in cognitive impairment in children?
      </button>
    </div>
  `,
  bottom: `
    <h2>Case Study Overview</h2>
    <p>
      This will go over all the information that is relevant to the thyroid case study as a whole. It will include a description of the case study, the regulatory questions, and how the case study is structured. It will also contain additonal details such as the people who worked on the case study, the tools used, and any other relevant information. This information will be structured to emphasize relevant details and provide a clear overview of the case study by using different layouts instead of plain text.
    </p>
  `,
};

// --- Step 2 and 3 content for each question ---
const processSteps = [
  "Chemical Characteristics",
  "External Exposure",
  "Kinetics",
  "AOP",
  "Adverse Outcome",
];

// Helper function to render step buttons for step 2
function renderStepButtons(steps, btnClass, onClickFn) {
  return `
    <div class="step-buttons">
      ${steps
        .map(
          (step) =>
            `<button class="btn ${btnClass}" onclick="${onClickFn}('${step}')"><b>${step}</b></button>`
        )
        .join("")}
    </div>
  `;
}

const step2Contents = {
  1: {
    top: `
      <h1>Process Flow Steps (Q1)</h1>
      <p>This regulatory question has been researched using the following process flow steps. The user will be able to click on one of the buttons below to find out more about the step or scroll down to learn more about this specific regulatory question. Not every regulatory question will use each step from the general process flow, only the ones used will be presented here for now. I might update it to show all </p>
      ${renderStepButtons(processSteps, "step2", "selectProcessStep")}
    `,
    bottom: `
      <h2>Thyroid-related Regulatory Question 1</h2>
      <p>
      This is where the content for regulatory question 1 will go. It will include a description of the regulatory question, the tools used, and any other relevant information. This information will be structured to emphasize relevant details and provide a clear overview of the regulatory question by using different layouts instead of plain text.
    </p>
    `,
  },
  2: {
    top: `
      <h1>Process Flow Steps (Q2)</h1>
      <p>This regulatory question has been researched using the following process flow steps. The user will be able to click on one of the buttons below to find out more about the step or scroll down to learn more about this specific regulatory question. Not every regulatory question will use each step from the general process flow, only the ones used will be presented here for now. I might update it to show all </p>
      ${renderStepButtons(processSteps, "step2", "selectProcessStep")}
    `,
    bottom: `
      <h2>Thyroid-related Regulatory Question 2</h2>
      <p>
      This is where the content for regulatory question 1 will go. It will include a description of the regulatory question, the tools used, and any other relevant information. This information will be structured to emphasize relevant details and provide a clear overview of the regulatory question by using different layouts instead of plain text.
    </p>
    `,
  },
};

// Step 3 content: [question][processStep]
const step3Contents = {
  1: {
    "Chemical Characteristics": {
      top: `
        <h1><span class="kinetics-bold">Chemical Characteristics</span> - Tools and Workflow (Q1)</h1>
        <p class="step-desc">For regulatory question 1, the chemical characteristics of the compound are analyzed to determine its properties relevant to use in early pregnancy. Tools such as chemical structure viewers and property calculators were used.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>Structure Viewer</b><br />Visualizes the molecular structure of the compound.</button>
          <button class="btn step3"><b>Property Calculator</b><br />Calculates key chemical properties like logP, solubility, and molecular weight.</button>
        </div>
      `,
      bottom: `
        <h2>Chemical Characteristics Workflow for Regulatory Question 1</h2>
        <p>This section describes how chemical characteristics were assessed for Q1, including the tools used and the rationale for their selection. The results inform the safety assessment for pregnant women.</p>
      `,
    },
    "External Exposure": {
      top: `
        <h1><span class="kinetics-bold">External Exposure</span> - Tools and Workflow (Q1)</h1>
        <p class="step-desc">For regulatory question 1, external exposure estimation tools were used to model how much of the compound women might be exposed to during early pregnancy.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>Exposure Model</b><br />Estimates daily intake based on use scenarios.</button>
        </div>
      `,
      bottom: `
        <h2>External Exposure Workflow for Regulatory Question 1</h2>
        <p>This section explains the approach to estimating external exposure, including assumptions and data sources. The exposure estimates are used in the risk assessment process.</p>
      `,
    },
    Kinetics: {
      top: `
        <h1><span class="kinetics-bold">Kinetics</span> - Tools and Workflow (Q1)</h1>
        <p class="step-desc">The kinetics aspect of regulatory question 1 of the Thyroid case study has been researched using the following tools. Select one to learn more or scroll down to read more about the kinetics research process.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>PBPK Model</b><br />Simulates absorption, distribution, metabolism, and excretion in pregnant women.</button>
        </div>
      `,
      bottom: `
        <h2>Kinetics Workflow for Regulatory Question 1</h2>
        <p>This is where the process of the kinetics research will be described for regulatory question 1. It will include the tools used, how they have been used, any assumptions made, why choices have been made, etc. It will also link to any other relevant pages or resources that are relevant to the kinetics research for regulatory question 1.</p>
      `,
    },
    AOP: {
      top: `
        <h1><span class="kinetics-bold">AOP</span> - Tools and Workflow (Q1)</h1>
        <p class="step-desc">For regulatory question 1, Adverse Outcome Pathways (AOPs) were mapped to understand the biological mechanisms affected by the compound.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>AOP Mapper</b><br />Visualizes the pathway from molecular interaction to adverse outcome.</button>
        </div>
      `,
      bottom: `
        <h2>AOP Workflow for Regulatory Question 1</h2>
        <p>This section describes the AOPs relevant to Q1 and how they inform the risk assessment for pregnant women.</p>
      `,
    },
    "Adverse Outcome": {
      top: `
        <h1><span class="kinetics-bold">Adverse Outcome</span> - Tools and Workflow (Q1)</h1>
        <p class="step-desc">For regulatory question 1, the potential adverse outcomes for the mother and fetus were evaluated using literature review and expert input.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>Outcome Database</b><br />Summarizes known adverse outcomes associated with the compound.</button>
        </div>
      `,
      bottom: `
        <h2>Adverse Outcome Workflow for Regulatory Question 1</h2>
        <p>This section summarizes the adverse outcomes considered for Q1 and how they were integrated into the overall assessment.</p>
      `,
    },
  },
  2: {
    "Chemical Characteristics": {
      top: `
        <h1><span class="kinetics-bold">Chemical Characteristics</span> - Tools and Workflow (Q2)</h1>
        <p class="step-desc">For regulatory question 2, the chemical characteristics of compound Z were analyzed to assess its potential to disrupt thyroid-mediated brain development.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>Structure Viewer</b><br />Visualizes the molecular structure of compound Z.</button>
        </div>
      `,
      bottom: `
        <h2>Chemical Characteristics Workflow for Regulatory Question 2</h2>
        <p>This section describes the chemical analysis for Q2 and its relevance to fetal brain development.</p>
      `,
    },
    "External Exposure": {
      top: `
        <h1><span class="kinetics-bold">External Exposure</span> - Tools and Workflow (Q2)</h1>
        <p class="step-desc">For regulatory question 2, external exposure models were used to estimate fetal exposure to compound Z.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>Exposure Model</b><br />Estimates fetal exposure based on maternal intake and placental transfer.</button>
        </div>
      `,
      bottom: `
        <h2>External Exposure Workflow for Regulatory Question 2</h2>
        <p>This section explains the approach to estimating fetal exposure for Q2, including key assumptions and data sources.</p>
      `,
    },
    Kinetics: {
      top: `
        <h1><span class="kinetics-bold">Kinetics</span> - Tools and Workflow (Q2)</h1>
        <p class="step-desc">The kinetics aspect of regulatory question 2 of the Thyroid case study has been researched using the following tools. Select one to learn more or scroll down to read more about the kinetics research process.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>PBPK Model</b><br />Simulates maternal-fetal transfer and metabolism of compound Z.</button>
        </div>
      `,
      bottom: `
        <h2>Kinetics Workflow for Regulatory Question 2</h2>
        <p>This is where the process of the kinetics research will be described for regulatory question 2. It will include the tools used, how they have been used, any assumptions made, why choices have been made, etc. It will also link to any other relevant pages or resources that are relevant to the kinetics research for regulatory question 2.</p>
      `,
    },
    AOP: {
      top: `
        <h1><span class="kinetics-bold">AOP</span> - Tools and Workflow (Q2)</h1>
        <p class="step-desc">For regulatory question 2, AOPs were mapped to understand how compound Z may affect thyroid hormone signaling and brain development.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>AOP Mapper</b><br />Visualizes the pathway from thyroid disruption to cognitive impairment.</button>
        </div>
      `,
      bottom: `
        <h2>AOP Workflow for Regulatory Question 2</h2>
        <p>This section describes the AOPs relevant to Q2 and their implications for fetal brain development.</p>
      `,
    },
    "Adverse Outcome": {
      top: `
        <h1><span class="kinetics-bold">Adverse Outcome</span> - Tools and Workflow (Q2)</h1>
        <p class="step-desc">For regulatory question 2, the potential adverse outcomes for the fetus were evaluated, focusing on cognitive development.</p>
        <div class="step-buttons">
          <button class="btn step3"><b>Outcome Database</b><br />Summarizes known neurodevelopmental outcomes associated with thyroid disruption.</button>
        </div>
      `,
      bottom: `
        <h2>Adverse Outcome Workflow for Regulatory Question 2</h2>
        <p>This section summarizes the adverse outcomes considered for Q2 and their relevance to the risk assessment.</p>
      `,
    },
  },
};

// --- Content update functions ---
function updateStep1Content() {
  document.getElementById("step1-content").innerHTML = step1Contents.top;
  document.getElementById("step1-bottom-content").innerHTML =
    step1Contents.bottom;
}
function updateStep2Content() {
  document.getElementById("step2-content").innerHTML =
    step2Contents[currentQuestion].top;
  document.getElementById("step2-bottom-content").innerHTML =
    step2Contents[currentQuestion].bottom;
}
function updateStep3Content() {
  document.getElementById("step3-content").innerHTML =
    step3Contents[currentQuestion][currentProcessStep].top;
  document.getElementById("step3-bottom-content").innerHTML =
    step3Contents[currentQuestion][currentProcessStep].bottom;
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
function updateBreadcrumb(step) {
  const el = document.getElementById("breadcrumbs");
  if (step === 2) {
    el.innerHTML = `<a href="#" onclick="goToStep(1); return false;">Thyroid Case Study</a> <span> &rarr; </span> <span>Regulatory Question ${currentQuestion}</span>`;
    el.classList.add("visible");
  } else if (step === 3) {
    el.innerHTML = `<a href=\"#\" onclick=\"goToStep(1); return false;\">Thyroid Case Study</a> <span>&rarr;</span> <a href=\"#\" onclick=\"goToStep(2); return false;\">Regulatory Question ${currentQuestion}</a> <span>&rarr;</span> <span>${currentProcessStep}</span>`;
    el.classList.add("visible");
  } else {
    el.innerHTML = "";
    el.classList.remove("visible");
  }
}

// Horizontal scroll navigation (snap to step)
function goToStep(step) {
  const wrapper = document.getElementById("stepsWrapper");
  // const slider = document.getElementById("progressSlider");
  const width = window.innerWidth;
  const scrollAmount = width * (step - 1);

  // Improved smooth scroll with easeInOutCubic and shorter duration
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

  // Update breadcrumb
  updateBreadcrumb(step);
  // Update content if needed
  if (step === 2) updateStep2Content();
  if (step === 3) updateStep3Content();
}

// On load, ensure correct breadcrumb and content is shown
document.addEventListener("DOMContentLoaded", function () {
  updateStep1Content();
  updateBreadcrumb(1);
  updateStep2Content();
  updateStep3Content();
});
