/* ============================================================================
   Dynamic search results- Fuse.js
   ============================================================================ */

//This script uses fuse.js to generate a dynamic searchbar that shows live-dropdown suggestions with inclusion of typo tolerance and matches. Important settings of Fuse.js include: 
// keys: ["title"]: searches page titles
// threshold: 0.4: At what point does the match algorithm give up.
// minMatchCharLength: at least 2 characters needed to search
// IncludeScore: will include the score for each match in the search results
// IncludeMatches: will include the matches and their positions within the search results
// ignoreLocation:  match anywhere in the title
//Explanation:
// The script starts off by creating an array with the platform's pages as the entrypoint for Fuse.js. Next fuse.js is initialised and the javascript is connected to the HTML to integrate the searchinput, resultscontainer and search button so that when users type input into the searchbar, results are shown dynamically underneath it (dropdown) and for no results, a message appears. The matched typed text will be shown as highlighted pink and each result is clickable. So when users click on the result in the dropdown, it will take them to the page URL. In addition, every time the user clicks outside the search area, the dropdown disappears which keeps the UI organized (additional step).


//Step 1:Pages array with titles and URLs as entrypoint for fuse.js
const pages = [

  { title: "Tools Home", url: "/tools" },
  { title: "AOP Builder", url: "/tools/aop-builder" },
  { title: "AOP Suite", url: "/tools/aopsuite" },
  { title: "AOP Wiki API", url: "/tools/aopwikiapi" },
  { title: "AOP Wiki", url: "/tools/aopwiki" },
  { title: "ArrayAnalysis", url: "/tools/arrayanalysis" },
  { title: "BioModels", url: "/tools/biomodels" },
  { title: "Biotransformer", url: "/tools/biotransformer" },
  { title: "BMDExpress 3", url: "/tools/bmdexpress_3" },
  { title: "BridgeDb", url: "/tools/bridgedb" },
  { title: "CDK Depict", url: "/tools/cdkdepict" },
  { title: "CellDesigner", url: "/tools/celldesigner" },
  { title: "Chemistry Development Kit", url: "/tools/cdk"},
  { title: "CompTox", url: "/tools/comptox" },
  { title: "COPASI", url: "/tools/copasi" },
  { title: "CPLogD", url: "/tools/cplogd" },
  { title: "Decimer", url: "/tools/decimer" },
  { title: "EMA Documents", url: "/tools/ema_documents" },
  { title: "FairdomHub", url: "/tools/fairdomhub" },
  { title: "Fairspace", url: "/tools/fairspace" },
  { title: "Farmacokompas", url: "/tools/farmacokompas" },
  { title: "Flame", url: "/tools/flame" },
  { title: "GScholar", url: "/tools/gscholar" },
  { title: "Google", url: "/tools/google" },
  { title: "JRC Data Catalogue", url: "/tools/jrc_data_catalogue" },
  { title: "LLEMY", url: "/tools/llemy" },
  { title: "MCT8 Dock", url: "/tools/mct8-dock" },
  { title: "MolAOP Analyser", url: "/tools/MolAOP analyser" },
  { title: "DSLD", url: "/tools/dsld" },
  { title: "OQT Assistant", url: "/tools/oqt_assistant" },
  { title: "OntoX Physiological Maps", url: "/tools/ontox_physiological_maps" },
  { title: "OP PBK Model", url: "/tools/oppbk_model"},
  { title: "Opsin", url: "/tools/opsin" },
  { title: "qAOP-App", url: "/tools/qaop_app" },
  { title: "QSPred", url: "/tools/qspred" },
  { title: "R-ODAF Shiny", url: "/tools/r_odaf"},
  { title: "Sombie", url: "/tools/sombie" },
  { title: "Sysrev", url: "/tools/sysrev" },
  { title: "OECD QSAR Toolbox", url: "/tools/oecd_qsar_toolbox" },
  { title: "ToxTemp Assistant", url: "/tools/toxtemp_assistant" },
  { title: "TXG Mapr", url: "/tools/txg_mapr" },
  { title: "VHP Glossary", url: "/tools/vhp_glossary" },
  { title: "Wikibase", url: "/tools/wikibase" },
  { title: "Wikibase User Interface", url: "/tools/kb" },
  { title: "WikiPathways AOP", url: "/tools/wikipathways_aop" },
  { title: "Xplore AOP", url: "/tools/xploreaop" },

  // Case Studies
  { title: "Case Studies", url: "/casestudies" },
  { title: "Thyroid Case Study", url: "/casestudies/thyroid" },
  { title: "Parkinson Case Study", url: "/casestudies/parkinson" },
  { title: "Kidney Case Study", url: "/casestudies/kidney" },

  // Data & Home
  { title: "Data", url: "/data" },
  { title: "Home", url: "/" }
];


//Step 2: Initialization of Fuse.js and connection between Fuse and HTML
const fuse = new Fuse(pages, {
  keys: ["title"],
  threshold: 0.4,       // Setting for typo tolerance
  distance: 100,  //determines how close the match is to the fuzzy location. Default is 100
  minMatchCharLength: 2, //Minimum length of characters needed to search
  IncludeMatches: true, 
  ignoreLocation: true //To match anywhere in the title
});

const searchInput = document.getElementById("searchInput");
const resultsContainer = document.getElementById("results");
const searchBtn = document.getElementById("searchBtn");

//Step 3: render dropdown results and highlight matching text
function renderResults(results, query) {
  if (!results.length) {
    resultsContainer.innerHTML = `<li class="list-group-item">No results found for "${query}"</li>`;
    return;
  }

  resultsContainer.innerHTML = results
    .map(r => {
      const regex = new RegExp(`(${query})`, "gi");
      const highlightedTitle = r.item.title.replace(regex, `<mark>$1</mark>`);
      return `<li class="list-group-item">
                <a href="${r.item.url}" style="text-decoration:none; color:inherit;">
                  ${highlightedTitle}
                </a>
              </li>`;
    })
    .join("");
}

//Step 4: enable live search (dynamically seeing results when user is typing)
searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim();
  if (!query) {
    resultsContainer.innerHTML = "";
    return;
  }
  const results = fuse.search(query);
  renderResults(results, query);
});

//Step 5: redirect to first match when clicking search button
searchBtn.addEventListener("click", () => {
  const query = searchInput.value.trim();
  if (!query) return;

  const results = fuse.search(query);
  if (results.length > 0) {
    window.location.href = results[0].item.url;
  } else {
    alert(`No results found for "${query}"`);
  }
});

//Additional step to remove dropdown if user clicks outside search bar
document.addEventListener("click", (e) => {
  if (!e.target.closest(".d-flex")) {
    resultsContainer.innerHTML = "";
  }
});
