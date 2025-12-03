/**
 * VHP4Safety Glossary Term Highlighter
 * Automatically highlights glossary terms in page content with interactive tooltips
 */

(function() {
  'use strict';

  // ============================================================================
  // CONFIGURATION - All tweakable parameters
  // ============================================================================
  const CONFIG = {
    // Source
    glossaryUrl: 'https://raw.githubusercontent.com/VHP4Safety/glossary/refs/heads/main/glossary.owl',
    glossaryWebsiteUrl: 'https://glossary.vhp4safety.nl/',
    
    // Tooltip behavior
    tooltipShowDelay: 0,           // ms before showing tooltip
    tooltipHideDelay: 2000,        // ms before hiding tooltip after unhover
    singleTooltipOnly: true,       // Only show one tooltip at a time
    
    // Highlighting
    caseSensitive: false,          // Match terms case-insensitively
    matchWholeWords: true,         // Only match whole words (use word boundaries, keep true, not working well otherwise)
    highlightClass: 'glossary-term',
    highlightType: 'bold',         // 'subtle' = dotted underline, 'bold' = bold text
    
    // Exclusions
    excludeTags: ['script', 'style', 'noscript', 'iframe', 'object'],
    excludeAttributes: ['data-no-vhp-glossary', 'data-vhp-glossary-skip'],
    excludeClassSubstrings: ['vhp-highlight', 'highlighted'],
    
    // CSS Styling - Leave null to use base.css styles, or customize here to override
    // Set these values to override the default CSS styles in base.css
    css: null,  // Set to object with custom styles to override, or null to use base.css
    
    // Example custom CSS configuration (uncomment and modify to override base.css):
    // css: {
    //   // Subtle highlight style
    //   subtle: {
    //     backgroundColor: 'rgba(48, 123, 191, 0.2)',
    //     borderBottom: '2px dotted #307bbf',
    //     color: 'inherit',
    //     hoverBackgroundColor: 'rgba(48, 123, 191, 0.35)',
    //     hoverBorderBottom: '2px solid #307bbf'
    //   },
    //   // Bold highlight style
    //   bold: {
    //     backgroundColor: 'transparent',
    //     fontWeight: '700',
    //     color: 'inherit',
    //     borderBottom: 'none',
    //     hoverBackgroundColor: 'rgba(48, 123, 191, 0.1)'
    //   },
    //   // Base styles for all highlights
    //   base: {
    //     cursor: 'help',
    //     padding: '2px 4px',
    //     borderRadius: '3px',
    //     display: 'inline'
    //   },
    //   // Tooltip styles
    //   tooltip: {
    //     fontSize: '0.875rem',
    //     maxWidth: '300px',
    //     backgroundColor: '#19b8a5', // var(--bs-vhpteal)
    //     textAlign: 'left',
    //     opacity: '1'
    //   }
    // },
    
    // Logging
    debug: true
  };

  // ============================================================================
  // STATE
  // ============================================================================
  let glossaryTerms = [];
  let isProcessing = false;
  const tooltipManager = {
    activeTooltip: null,
    hideTimer: null
  };

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================
  
  const log = (...args) => CONFIG.debug && console.log('[VHP Glossary]', ...args);
  const escapeHtml = text => { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; };
  const escapeRegex = str => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  
  const extractProperty = (props, pattern) => {
    const match = props.match(pattern);
    return match ? match[1].trim() : '';
  };
  
  const getGlossaryUrl = uri => {
    if (uri?.includes('#')) {
      return `${CONFIG.glossaryWebsiteUrl}#${uri.split('#')[1]}`;
    }
    return CONFIG.glossaryWebsiteUrl;
  };

  // ============================================================================
  // DYNAMIC STYLING
  // ============================================================================
  
  function injectCustomStyles() {
    // If CONFIG.css is null or undefined, use base.css styles instead
    if (!CONFIG.css) {
      log('Using base.css styles (CONFIG.css is null)');
      return;
    }
    
    // Remove any existing style element
    const existingStyle = document.getElementById('vhp-glossary-styles');
    if (existingStyle) existingStyle.remove();
    
    const style = document.createElement('style');
    style.id = 'vhp-glossary-styles';
    
    const { base, subtle, bold, tooltip } = CONFIG.css;
    
    style.textContent = `
      /* Base glossary term styles */
      .${CONFIG.highlightClass} {
        cursor: ${base.cursor} !important;
        padding: ${base.padding} !important;
        border-radius: ${base.borderRadius} !important;
        display: ${base.display} !important;
      }
      
      /* Subtle highlight style */
      .${CONFIG.highlightClass}-subtle {
        background-color: ${subtle.backgroundColor} !important;
        border-bottom: ${subtle.borderBottom} !important;
        color: ${subtle.color} !important;
      }
      
      .${CONFIG.highlightClass}-subtle:hover {
        background-color: ${subtle.hoverBackgroundColor} !important;
        border-bottom: ${subtle.hoverBorderBottom} !important;
      }
      
      /* Bold highlight style */
      .${CONFIG.highlightClass}-bold {
        background-color: ${bold.backgroundColor} !important;
        font-weight: ${bold.fontWeight} !important;
        color: ${bold.color} !important;
        border-bottom: ${bold.borderBottom} !important;
      }
      
      .${CONFIG.highlightClass}-bold:hover {
        background-color: ${bold.hoverBackgroundColor} !important;
      }
      
      /* Tooltip styles */
      .tooltip {
        font-size: ${tooltip.fontSize} !important;
        opacity: ${tooltip.opacity} !important;
      }
      
      .tooltip-inner {
        max-width: ${tooltip.maxWidth} !important;
        text-align: ${tooltip.textAlign} !important;
        background-color: ${tooltip.backgroundColor} !important;
        opacity: ${tooltip.opacity} !important;
      }
      
      .tooltip-arrow::before {
        border-top-color: ${tooltip.backgroundColor} !important;
      }
    `;
    
    document.head.appendChild(style);
    log('Custom styles injected');
  }

  // ============================================================================
  // PARSING
  // ============================================================================
  
  function parseOWLGlossary(turtleText) {
    // Use shared TTLParser if available, otherwise use embedded parser
    if (window.TTLParser) {
      log('Using shared TTLParser module');
      return window.TTLParser.parseGlossary(turtleText, {
        requireLabel: true,
        requireClass: true,
        minLabelLength: 2,
        extractRelations: false
      });
    }
    
    // Fallback: embedded parser (for backwards compatibility)
    log('Using embedded parser (TTLParser not loaded)');
    const termBlockRegex = /<([^>]+)>\s*\n([\s\S]*?)(?=\n<|$)/g;
    const terms = [];
    let match;
    
    while ((match = termBlockRegex.exec(turtleText)) !== null) {
      const [, uri, props] = match;
      
      // Must be an owl:Class with a label
      if (!props.includes('rdf:type') || !props.includes('owl:Class')) continue;
      
      const label = extractProperty(props, /rdfs:label\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
      if (!label || label === 'nan' || label.length < 2) continue;
      
      const definition = extractProperty(props, /dc:description\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
      const synonym = extractProperty(props, /ncit:C42610\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
      
      terms.push({
        uri,
        label,
        definition,
        synonyms: synonym ? [synonym] : []
      });
    }
    
    log(`Parsed ${terms.length} glossary terms`);
    return terms;
  }

  // ============================================================================
  // TOOLTIP CONTENT
  // ============================================================================
  
  function createTooltipContent(term) {
    const parts = [`<strong>${escapeHtml(term.label)}</strong>`];
    
    if (term.definition) {
      parts.push(`<br><small>${escapeHtml(term.definition)}</small>`);
    }
    
    if (term.synonyms?.length) {
      parts.push(`<br><small class="text-muted">Synonyms: ${escapeHtml(term.synonyms.join(', '))}</small>`);
    }
    
    const url = getGlossaryUrl(term.uri);
    parts.push(`<div class="mt-1"><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="text-white text-decoration-underline"><i class="bi bi-box-arrow-up-right"></i> View full definition</a></div>`);
    
    return parts.join('');
  }

  // ============================================================================
  // NODE FILTERING
  // ============================================================================
  
  function shouldProcessNode(node) {
    if (node.nodeType !== Node.TEXT_NODE || !node.textContent.trim()) return false;
    
    let parent = node.parentElement;
    while (parent) {
      // Check tag exclusions
      if (CONFIG.excludeTags.includes(parent.tagName.toLowerCase())) return false;
      
      // Check attribute exclusions
      if (CONFIG.excludeAttributes.some(attr => parent.hasAttribute(attr))) return false;
      
      // Check class exclusions
      if (parent.classList.contains(CONFIG.highlightClass)) return false;
      const classList = Array.from(parent.classList);
      if (CONFIG.excludeClassSubstrings.some(substr => 
        classList.some(cls => cls.toLowerCase().includes(substr))
      )) return false;
      
      parent = parent.parentElement;
    }
    
    return true;
  }
  
  function walkTextNodes(node, callback) {
    if (node.nodeType === Node.TEXT_NODE) {
      callback(node);
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      Array.from(node.childNodes).forEach(child => walkTextNodes(child, callback));
    }
  }

  // ============================================================================
  // HIGHLIGHTING
  // ============================================================================
  
  function findMatches(text, terms) {
    const matches = [];
    const flags = CONFIG.caseSensitive ? 'g' : 'gi';
    const boundary = CONFIG.matchWholeWords ? '\\b' : '';
    
    let totalAttempts = 0;
    terms.forEach(term => {
      [term.label, ...term.synonyms].forEach(label => {
        totalAttempts++;
        const pattern = `${boundary}${escapeRegex(label)}${boundary}`;
        const regex = new RegExp(pattern, flags);
        let match;
        
        while ((match = regex.exec(text)) !== null) {
          log(`MATCH FOUND: "${label}" in text`);
          matches.push({
            start: match.index,
            end: match.index + match[0].length,
            text: match[0],
            term
          });
        }
      });
    });
    
    if (matches.length === 0 && totalAttempts > 0) {
      log(`No matches found after trying ${totalAttempts} patterns in text: "${text.substring(0, 100)}..."`);
    }
    
    // Sort and remove overlaps (keep first match)
    matches.sort((a, b) => a.start - b.start);
    return matches.filter((match, i) => 
      i === 0 || match.start >= matches[i - 1].end
    );
  }
  
  function createHighlightSpan(match) {
    const span = document.createElement('span');
    // Apply both base class and type-specific class
    span.classList.add(CONFIG.highlightClass);
    span.classList.add(`${CONFIG.highlightClass}-${CONFIG.highlightType}`);
    span.textContent = match.text;
    span.setAttribute('data-bs-toggle', 'tooltip');
    span.setAttribute('data-bs-html', 'true');
    span.setAttribute('data-bs-placement', 'top');
    span.setAttribute('title', createTooltipContent(match.term));
    span.setAttribute('data-vhp-uri', match.term.uri);
    
    log(`Created highlight span with classes: ${span.className} for term: ${match.term.label}`);
    return span;
  }
  
  function highlightNode(node, terms) {
    if (!shouldProcessNode(node)) {
      log(`Skipping node: ${node.textContent.substring(0, 50)}...`);
      return;
    }
    
    const text = node.textContent;
    log(`Processing node with text: "${text.substring(0, 100)}..."`);
    const matches = findMatches(text, terms);
    if (!matches.length) return;
    
    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    
    matches.forEach(match => {
      if (match.start > lastIndex) {
        fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.start)));
      }
      fragment.appendChild(createHighlightSpan(match));
      lastIndex = match.end;
    });
    
    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
    }
    
    node.parentNode.replaceChild(fragment, node);
  }

  // ============================================================================
  // TOOLTIP MANAGEMENT
  // ============================================================================
  
  function initTooltips() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;
    
    const elements = document.querySelectorAll(`[data-bs-toggle="tooltip"]`);
    log(`Initializing ${elements.length} tooltips`);
    
    elements.forEach(el => {
      const tooltip = new bootstrap.Tooltip(el, {
        trigger: 'manual',
        delay: { show: CONFIG.tooltipShowDelay, hide: 0 },
        container: 'body',
        placement: 'bottom',
        customClass: 'vhp-glossary-tooltip-fixed'
      });
      
      const hideWithAnimation = (tooltipInstance) => {
        const tooltipEl = document.querySelector('.tooltip.show');
        if (tooltipEl) {
          tooltipEl.classList.add('hiding');
          tooltipEl.classList.remove('show');
          // Wait for animation to complete before actually hiding
          setTimeout(() => {
            tooltipInstance.hide();
            tooltipEl.classList.remove('hiding');
          }, 200); // Match animation duration
        } else {
          tooltipInstance.hide();
        }
      };
      
      const show = () => {
        if (CONFIG.singleTooltipOnly && tooltipManager.activeTooltip) {
          hideWithAnimation(tooltipManager.activeTooltip);
        }
        clearTimeout(tooltipManager.hideTimer);
        tooltipManager.activeTooltip = tooltip;
        tooltip.show();
      };
      
      const scheduleHide = () => {
        clearTimeout(tooltipManager.hideTimer);
        tooltipManager.hideTimer = setTimeout(() => {
          hideWithAnimation(tooltip);
          if (tooltipManager.activeTooltip === tooltip) {
            tooltipManager.activeTooltip = null;
          }
        }, CONFIG.tooltipHideDelay);
      };
      
      el.addEventListener('mouseenter', show);
      el.addEventListener('mouseleave', scheduleHide);
      
      el.addEventListener('shown.bs.tooltip', () => {
        const tooltipEl = document.querySelector('.tooltip.show');
        if (tooltipEl) {
          tooltipEl.onmouseenter = () => clearTimeout(tooltipManager.hideTimer);
          tooltipEl.onmouseleave = scheduleHide;
        }
      });
    });
  }

  // ============================================================================
  // MAIN PROCESS
  // ============================================================================
  
  function processDocument() {
    if (isProcessing || !glossaryTerms.length) return;
    
    isProcessing = true;
    log('Processing document for glossary terms...');
    
    const textNodes = [];
    walkTextNodes(document.body, node => {
      if (shouldProcessNode(node)) textNodes.push(node);
    });
    
    log(`Found ${textNodes.length} text nodes to process`);
    
    textNodes.forEach(node => {
      try {
        highlightNode(node, glossaryTerms);
      } catch (error) {
        console.error('[VHP Glossary] Error highlighting node:', error);
      }
    });
    
    initTooltips();
    isProcessing = false;
    log('Document processing complete');
  }
  
  async function fetchAndProcess() {
    try {
      log(`Fetching glossary from ${CONFIG.glossaryUrl}`);
      const response = await fetch(CONFIG.glossaryUrl);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const text = await response.text();
      glossaryTerms = parseOWLGlossary(text);
      
      if (glossaryTerms.length) {
        processDocument();
      } else {
        console.warn('[VHP Glossary] No terms found in glossary file');
      }
    } catch (error) {
      console.error('[VHP Glossary] Fetch error:', error);
    }
  }
  
  // ============================================================================
  // INITIALIZATION
  // ============================================================================
  
  function initialize() {
    injectCustomStyles();
    fetchAndProcess();
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }

})();
