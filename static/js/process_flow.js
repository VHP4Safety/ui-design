/**
 * Process Flow Page - Dynamic loading of Process Flow Steps
 * Fetches the glossary OWL and extracts terms that have a dct:relation.
 */

(function () {
  'use strict';

  const GLOSSARY_URL = 'https://raw.githubusercontent.com/VHP4Safety/glossary/refs/heads/main/glossary.owl';

  /** Desired display order for process flow steps. */
  const STEP_ORDER = [
    'Exposure',
    'Chemical Characteristics and Hazard Identification',
    'Toxicokinetics',
    'Toxicodynamics',
    'Adverse Outcome',
  ];

  /** Remove the "(Process Flow Step)" suffix from a label. */
  const cleanLabel = (label) => label.replace(/\s*\(Process Flow Step\)\s*$/i, '').trim();

  // ── Parsing ────────────────────────────────────────────────────────────────

  function parseTermsWithRelations(turtleText) {
    const rx = /<([^>]+)>\s*\n([\s\S]*?)(?=\n<|$)/g;
    const prop = (block, p) => { const m = block.match(p); return m ? m[1].trim() : ''; };
    const terms = [];
    let m;

    while ((m = rx.exec(turtleText)) !== null) {
      const [, uri, block] = m;
      if (!block.includes('rdf:type') || !block.includes('owl:Class')) continue;

      const label = prop(block, /rdfs:label\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
      if (!label || label === 'nan' || label.length < 2) continue;

      const relMatch = block.match(/dct:relation\s+<([^>]+)>/);
      if (!relMatch) continue;

      terms.push({
        uri,
        label,
        definition: prop(block, /dc:description\s+"([^"]+)"(?:@[a-zA-Z-]+)?/),
        relation: relMatch[1].trim(),
      });
    }
    return terms;
  }

  // ── Rendering ──────────────────────────────────────────────────────────────

  function createAccordionItem(term, index) {
    const id = `about-${index}`;
    const title = cleanLabel(term.label);
    const body = term.definition || 'No definition available.';

    return `
  <div class="accordion-item">
    <h2 class="accordion-header" id="${id}-heading">
      <button class="accordion-button collapsed" type="button"
              data-bs-toggle="collapse" data-bs-target="#${id}-collapse"
              aria-expanded="false" aria-controls="${id}-collapse">
        ${title}
      </button>
    </h2>
    <div id="${id}-collapse" class="accordion-collapse collapse" aria-labelledby="${id}-heading">
      <div class="accordion-body" style="text-align: justify;">
        <p>${body}</p>
      </div>
    </div>
  </div>`;
  }

  // ── Main ───────────────────────────────────────────────────────────────────

  async function loadProcessFlowSteps() {
    const container = document.getElementById('process-flow-accordion');
    if (!container) return;

    container.innerHTML =
      '<div class="text-center py-4"><div class="spinner-border text-primary" role="status">' +
      '<span class="visually-hidden">Loading...</span></div></div>';

    try {
      const resp = await fetch(GLOSSARY_URL);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const terms = parseTermsWithRelations(await resp.text());
      if (terms.length === 0) {
        container.innerHTML = '<p class="text-muted">No process flow steps found.</p>';
        return;
      }

      // Sort by STEP_ORDER; unrecognised terms go to the end
      terms.sort((a, b) => {
        const ai = STEP_ORDER.indexOf(cleanLabel(a.label));
        const bi = STEP_ORDER.indexOf(cleanLabel(b.label));
        return (ai === -1 ? STEP_ORDER.length : ai) - (bi === -1 ? STEP_ORDER.length : bi);
      });

      container.innerHTML = terms.map(createAccordionItem).join('');
    } catch (err) {
      console.error('[Process Flow]', err);
      container.innerHTML =
        '<div class="alert alert-warning" role="alert">' +
        '<strong>Unable to load process flow steps.</strong><br>' +
        'Please try refreshing the page or check back later.</div>';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadProcessFlowSteps);
  } else {
    loadProcessFlowSteps();
  }
})();
