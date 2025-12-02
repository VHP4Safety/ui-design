/**
 * Glossary Term Highlighter
 * Fetches OWL glossary from GitHub and highlights matching terms in the page
 * with Bootstrap tooltips showing term definitions
 */

(function() {
  'use strict';

  const GLOSSARY_URL = 'https://raw.githubusercontent.com/VHP4Safety/glossary/refs/heads/main/glossary.owl';
  
  // Cache for glossary terms
  let glossaryTerms = [];
  let isProcessing = false;

  /**
   * Parse OWL Turtle format and extract term information
   */
  function parseOWLGlossary(turtleText) {
    const terms = [];
    
    // Split into individual term blocks (each URI section)
    // Match pattern: <URI> \n properties \n .
    const termBlockRegex = /<([^>]+)>\s*\n([\s\S]*?)(?=\n<|$)/g;
    let match;
    
    while ((match = termBlockRegex.exec(turtleText)) !== null) {
      const uri = match[1];
      const properties = match[2];
      
      // Skip if not a glossary term (must have rdf:type owl:Class)
      if (!properties.includes('rdf:type') || !properties.includes('owl:Class')) {
        continue;
      }
      
      const term = { uri };
      
      // Extract rdfs:label
      const labelMatch = properties.match(/rdfs:label\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
      if (!labelMatch) continue; // Skip if no label
      term.label = labelMatch[1].trim();
      
      // Skip "nan" entries
      if (term.label === 'nan') continue;
      
      // Extract dc:description (definition)
      const descMatch = properties.match(/dc:description\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
      term.definition = descMatch ? descMatch[1].trim() : '';
      
      // Extract ncit:C42610 (abbreviation/synonym)
      const synonymMatch = properties.match(/ncit:C42610\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
      term.synonyms = [];
      if (synonymMatch && synonymMatch[1].trim() && synonymMatch[1].trim() !== '') {
        term.synonyms.push(synonymMatch[1].trim());
      }
      
      // Only add terms with meaningful content
      if (term.label && term.label.length > 1) {
        terms.push(term);
      }
    }

    console.log(`Parsed ${terms.length} glossary terms`);
    return terms;
  }

  /**
   * Convert GitHub glossary URI to website URL
   */
  function getGlossaryUrl(uri) {
    // Convert https://vhp4safety.github.io/glossary#VHP0000133 
    // to https://glossary.vhp4safety.nl/#VHP0000133
    if (uri && uri.includes('#')) {
      const fragment = uri.split('#')[1];
      return `https://glossary.vhp4safety.nl/#${fragment}`;
    }
    // Fallback to main glossary page
    return 'https://glossary.vhp4safety.nl/';
  }

  /**
   * Create tooltip content for a term
   */
  function createTooltipContent(term) {
    let content = `<strong>${escapeHtml(term.label)}</strong>`;
    
    if (term.definition) {
      content += `<br><small>${escapeHtml(term.definition)}</small>`;
    }
    
    if (term.synonyms && term.synonyms.length > 0) {
      content += `<br><small class="text-muted">Synonyms: ${escapeHtml(term.synonyms.join(', '))}</small>`;
    }
    
    content += `<br><small class="text-muted"><i class="bi bi-box-arrow-up-right"></i> Click to view full definition</small>`;
    
    return content;
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Check if a node should be processed for highlighting
   */
  function shouldProcessNode(node) {
    if (node.nodeType !== Node.TEXT_NODE) return false;
    if (!node.textContent.trim()) return false;
    
    // Skip script, style, and already highlighted elements
    let parent = node.parentElement;
    while (parent) {
      const tagName = parent.tagName.toLowerCase();
      if (['script', 'style', 'noscript', 'iframe', 'object'].includes(tagName)) {
        return false;
      }
      if (parent.classList.contains('glossary-term')) {
        return false;
      }
      parent = parent.parentElement;
    }
    
    return true;
  }

  /**
   * Highlight terms in text nodes
   */
  function highlightTermsInNode(node, terms) {
    if (!shouldProcessNode(node)) return;

    const text = node.textContent;
    let matches = [];

    // Find all matches for all terms
    terms.forEach(term => {
      const labels = [term.label, ...(term.synonyms || [])];
      
      labels.forEach(label => {
        // Create case-insensitive word boundary regex
        // Use \b for word boundaries, but also handle hyphenated terms
        const regex = new RegExp(`\\b${label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
        let match;
        
        while ((match = regex.exec(text)) !== null) {
          matches.push({
            start: match.index,
            end: match.index + match[0].length,
            text: match[0],
            term: term
          });
        }
      });
    });

    // Sort matches by position and remove overlaps
    matches.sort((a, b) => a.start - b.start);
    matches = removeOverlappingMatches(matches);

    if (matches.length === 0) return;

    // Create new nodes with highlights
    const fragment = document.createDocumentFragment();
    let lastIndex = 0;

    matches.forEach(match => {
      // Add text before match
      if (match.start > lastIndex) {
        fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.start)));
      }

      // Create clickable link
      const link = document.createElement('a');
      link.href = getGlossaryUrl(match.term.uri);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.className = 'glossary-term';
      link.textContent = match.text;
      link.setAttribute('data-bs-toggle', 'tooltip');
      link.setAttribute('data-bs-html', 'true');
      link.setAttribute('data-bs-placement', 'top');
      link.setAttribute('title', createTooltipContent(match.term));
      
      fragment.appendChild(link);
      lastIndex = match.end;
    });

    // Add remaining text
    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
    }

    // Replace original node
    node.parentNode.replaceChild(fragment, node);
  }

  /**
   * Remove overlapping matches (keep first occurrence)
   */
  function removeOverlappingMatches(matches) {
    const filtered = [];
    let lastEnd = -1;

    matches.forEach(match => {
      if (match.start >= lastEnd) {
        filtered.push(match);
        lastEnd = match.end;
      }
    });

    return filtered;
  }

  /**
   * Walk through all text nodes in the document body
   */
  function walkTextNodes(node, callback) {
    if (node.nodeType === Node.TEXT_NODE) {
      callback(node);
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      // Process children
      const children = Array.from(node.childNodes);
      children.forEach(child => walkTextNodes(child, callback));
    }
  }

  /**
   * Process the entire document body
   */
  function highlightAllTerms() {
    if (isProcessing || glossaryTerms.length === 0) return;
    
    isProcessing = true;
    console.log('Highlighting glossary terms...');
    // Find all text nodes in body
    const textNodes = [];
    walkTextNodes(document.body, node => {
      if (shouldProcessNode(node)) {
        textNodes.push(node);
        console.log(node);
      }
    });

    console.log(`Found ${textNodes.length} text nodes to process`);

    // Process nodes
    textNodes.forEach(node => {
      try {
        highlightTermsInNode(node, glossaryTerms);
      } catch (error) {
        console.error('Error highlighting node:', error);
      }
    });

    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
      const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
      [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
      console.log(`Initialized ${tooltipTriggerList.length} tooltips`);
    }

    isProcessing = false;
  }

  /**
   * Fetch and process the glossary
   */
  async function fetchGlossary() {
    try {
      console.log('Fetching glossary from:', GLOSSARY_URL);
      const response = await fetch(GLOSSARY_URL);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const xmlText = await response.text();
      glossaryTerms = parseOWLGlossary(xmlText);
      
      if (glossaryTerms.length > 0) {
        highlightAllTerms();
      } else {
        console.warn('No glossary terms found in OWL file');
      }
    } catch (error) {
      console.error('Error fetching glossary:', error);
    }
  }

  /**
   * Initialize when DOM is ready
   */
  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fetchGlossary);
    } else {
      fetchGlossary();
    }
  }

  // Start the process
  init();

})();
