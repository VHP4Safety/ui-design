/**
 * VHP4Safety TTL/OWL Parser
 * Reusable module for parsing Turtle/OWL glossary files
 */

(function(window) {
  'use strict';

  const TTLParser = {
    /**
     * Extract a property value from TTL properties string
     */
    extractProperty(props, pattern) {
      const match = props.match(pattern);
      return match ? match[1].trim() : '';
    },

    /**
     * Extract relation IRI from properties
     */
    extractRelation(props) {
      const match = props.match(/dct:relation\s+<([^>]+)>/);
      return match ? match[1].trim() : '';
    },

    /**
     * Parse OWL/Turtle glossary text and extract all terms
     * @param {string} turtleText - The raw TTL/OWL text
     * @param {Object} options - Parsing options
     * @returns {Array} Array of term objects
     */
    parseGlossary(turtleText, options = {}) {
      const {
        requireLabel = true,
        requireClass = true,
        minLabelLength = 2,
        extractRelations = false
      } = options;

      const termBlockRegex = /<([^>]+)>\s*\n([\s\S]*?)(?=\n<|$)/g;
      const terms = [];
      let match;
      
      while ((match = termBlockRegex.exec(turtleText)) !== null) {
        const [, uri, props] = match;
        
        // Check if it's an owl:Class
        if (requireClass && (!props.includes('rdf:type') || !props.includes('owl:Class'))) {
          continue;
        }
        
        // Extract label
        const label = this.extractProperty(props, /rdfs:label\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
        if (requireLabel && (!label || label === 'nan' || label.length < minLabelLength)) {
          continue;
        }
        
        // Extract other properties
        const definition = this.extractProperty(props, /dc:description\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
        const synonym = this.extractProperty(props, /ncit:C42610\s+"([^"]+)"(?:@[a-zA-Z-]+)?/);
        
        const term = {
          uri,
          label,
          definition,
          synonyms: synonym ? [synonym] : []
        };

        // Extract relation if requested
        if (extractRelations) {
          const relation = this.extractRelation(props);
          if (relation) {
            term.relation = relation;
          }
        }
        
        terms.push(term);
      }
      
      return terms;
    },

    /**
     * Parse glossary and filter terms that have a dct:relation
     * @param {string} turtleText - The raw TTL/OWL text
     * @returns {Array} Array of terms with relations
     */
    parseTermsWithRelations(turtleText) {
      const allTerms = this.parseGlossary(turtleText, { extractRelations: true });
      return allTerms.filter(term => term.relation);
    },

    /**
     * Fetch and parse glossary from URL
     * @param {string} url - URL to glossary file
     * @param {Object} options - Parsing options
     * @returns {Promise<Array>} Promise resolving to array of terms
     */
    async fetchAndParse(url, options = {}) {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const text = await response.text();
        return this.parseGlossary(text, options);
      } catch (error) {
        console.error('[TTLParser] Error fetching glossary:', error);
        throw error;
      }
    },

    /**
     * Fetch and parse glossary terms with relations
     * @param {string} url - URL to glossary file
     * @returns {Promise<Array>} Promise resolving to array of terms with relations
     */
    async fetchTermsWithRelations(url) {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const text = await response.text();
        return this.parseTermsWithRelations(text);
      } catch (error) {
        console.error('[TTLParser] Error fetching glossary:', error);
        throw error;
      }
    },

    /**
     * Build a map of terms by URI for quick lookup
     * @param {Array} terms - Array of term objects
     * @returns {Object} Map of URI to term object
     */
    buildTermMap(terms) {
      const map = {};
      terms.forEach(term => {
        map[term.uri] = term;
      });
      return map;
    },

    /**
     * Get glossary URL for a term URI
     * @param {string} uri - Term URI
     * @param {string} baseUrl - Base glossary website URL
     * @returns {string} Full URL to term on glossary website
     */
    getGlossaryUrl(uri, baseUrl = 'https://glossary.vhp4safety.nl/') {
      if (uri?.includes('#')) {
        return `${baseUrl}#${uri.split('#')[1]}`;
      }
      return baseUrl;
    }
  };

  // Export to global scope
  window.TTLParser = TTLParser;

})(window);
