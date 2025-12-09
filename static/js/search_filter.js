/**
 * Search and Filter Module
 * Provides reusable search and filter functionality for catalog pages (data, methods, tools)
 * 
 * Usage:
 * SearchFilter.init({
 *   filterTypes: ['case-study', 'flow-step', 'reg-question'], // Filter categories
 *   multiSelect: false, // Whether to allow multiple selections per category
 *   initialFilters: { 'case-study': 'Kidney', ... }, // Initial filter values from server
 *   formElementIds: { // Optional: Override default element IDs
 *     form: 'search-form',
 *     filterToggle: 'filter-toggle-btn',
 *     filterPanel: 'filter-panel',
 *     applyBtn: 'apply-filter-btn',
 *     clearBtn: 'clear-filter-btn',
 *     filterTags: 'filter-tags',
 *     selectedFilters: 'selected-filters'
 *   },
 *   filterFieldMap: { // Map filter types to hidden form field IDs
 *     'case-study': 'filter_case_study',
 *     'flow-step': 'filter_flow_step',
 *     'reg-question': 'filter_regulatory_question'
 *   },
 *   filterLabels: { // Human-readable labels for filter types
 *     'case-study': 'Case Study',
 *     'flow-step': 'Flow Step',
 *     'reg-question': 'Reg. Question'
 *   },
 *   badgeClass: 'badge rounded-pill text-bg-vhpteal', // CSS class for filter tags
 *   initTooltips: true, // Whether to initialize Bootstrap tooltips
 *   tooltipSelector: '[data-bs-toggle="tooltip"]' // Selector for tooltips
 * });
 */

(function(window) {
  'use strict';

  const SearchFilter = {
    config: null,
    elements: null,
    selectedFilters: {},

    /**
     * Initialize the search and filter functionality
     */
    init(options) {
      // Set default configuration
      this.config = {
        filterTypes: options.filterTypes || [],
        multiSelect: options.multiSelect !== undefined ? options.multiSelect : false,
        multipleInputs: options.multipleInputs || false, // Create separate input for each value
        initialFilters: options.initialFilters || {},
        formElementIds: {
          form: 'search-form',
          filterToggle: 'filter-toggle-btn',
          filterPanel: 'filter-panel',
          applyBtn: 'apply-filter-btn',
          clearBtn: 'clear-filter-btn',
          filterTags: 'filter-tags',
          selectedFilters: 'selected-filters',
          ...(options.formElementIds || {})
        },
        filterFieldMap: options.filterFieldMap || {},
        filterLabels: options.filterLabels || {},
        badgeClass: options.badgeClass || 'badge rounded-pill text-bg-vhpteal',
        initTooltips: options.initTooltips !== undefined ? options.initTooltips : true,
        tooltipSelector: options.tooltipSelector || '[data-bs-toggle="tooltip"]',
        showFilterPanel: options.showFilterPanel || false,
        onFormSubmit: options.onFormSubmit || null // Optional callback before form submission
      };

      // Get DOM elements
      this.elements = {
        form: document.getElementById(this.config.formElementIds.form),
        filterToggle: document.getElementById(this.config.formElementIds.filterToggle),
        filterPanel: document.getElementById(this.config.formElementIds.filterPanel),
        applyBtn: document.getElementById(this.config.formElementIds.applyBtn),
        clearBtn: document.getElementById(this.config.formElementIds.clearBtn),
        filterTags: document.getElementById(this.config.formElementIds.filterTags),
        selectedFiltersContainer: document.getElementById(this.config.formElementIds.selectedFilters)
      };

      // Validate required elements exist
      if (!this.elements.form) {
        console.error('[SearchFilter] Form element not found:', this.config.formElementIds.form);
        return;
      }

      // Initialize selected filters
      this.initializeFilters();

      // Set up event listeners
      this.setupEventListeners();

      // Initialize tooltips if enabled
      if (this.config.initTooltips) {
        this.initializeTooltips();
      }

      // Show filter panel if filters are active
      if (this.config.showFilterPanel && this.elements.filterPanel) {
        this.elements.filterPanel.style.display = 'block';
      }

      // Update display
      this.updateFilterDisplay();
    },

    /**
     * Initialize filter selections from server-provided values
     */
    initializeFilters() {
      this.config.filterTypes.forEach(type => {
        const initialValue = this.config.initialFilters[type];
        
        if (this.config.multiSelect) {
          // Multi-select: expect array
          this.selectedFilters[type] = Array.isArray(initialValue) ? [...initialValue] : 
                                        (initialValue ? [initialValue] : []);
        } else {
          // Single select: expect string
          this.selectedFilters[type] = initialValue || '';
        }
      });
    },

    /**
     * Set up event listeners for filter interactions
     */
    setupEventListeners() {
      // Filter toggle button
      if (this.elements.filterToggle && this.elements.filterPanel) {
        this.elements.filterToggle.addEventListener('click', () => {
          const isVisible = this.elements.filterPanel.style.display !== 'none';
          this.elements.filterPanel.style.display = isVisible ? 'none' : 'block';
        });
      }

      // Dropdown item clicks
      document.querySelectorAll('.dropdown-item[data-filter-type]').forEach(item => {
        item.addEventListener('click', (e) => {
          e.preventDefault();
          if (this.config.multiSelect) {
            e.stopPropagation(); // Keep dropdown open for multi-select
          }
          
          const filterType = item.dataset.filterType;
          const filterValue = item.dataset.filterValue;
          
          if (filterType && filterValue) {
            if (this.config.multiSelect) {
              this.toggleFilter(filterType, filterValue);
            } else {
              this.setFilter(filterType, filterValue);
            }
          }
        });
      });

      // Apply filter button
      if (this.elements.applyBtn) {
        this.elements.applyBtn.addEventListener('click', (e) => {
          e.preventDefault();
          this.applyFilters();
        });
      }

      // Form submission handler
      if (this.elements.form) {
        this.elements.form.addEventListener('submit', (e) => {
          e.preventDefault();
          this.applyFilters();
        });
      }

      // Clear filter button
      if (this.elements.clearBtn) {
        this.elements.clearBtn.addEventListener('click', () => {
          this.clearFilters();
        });
      }

      // Make removeFilter accessible globally for onclick handlers in badges
      window.removeFilterTag = (type, value) => {
        if (this.config.multiSelect) {
          this.removeFilterMulti(type, value);
        } else {
          this.removeFilterSingle(type);
        }
      };
    },

    /**
     * Initialize Bootstrap tooltips
     */
    initializeTooltips() {
      if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) {
        console.warn('[SearchFilter] Bootstrap Tooltip not available');
        return;
      }

      const tooltipElements = document.querySelectorAll(this.config.tooltipSelector);
      tooltipElements.forEach(el => {
        // Validate title attribute
        const title = el.getAttribute('data-bs-title') || el.getAttribute('title');
        if (title && title.trim() !== '' && title !== 'None' && title !== 'null') {
          new bootstrap.Tooltip(el);
        }
      });
    },

    /**
     * Set a single filter (single-select mode)
     */
    setFilter(type, value) {
      if (!this.selectedFilters.hasOwnProperty(type)) return;
      this.selectedFilters[type] = value;
      this.updateFilterDisplay();
    },

    /**
     * Remove a single filter (single-select mode)
     */
    removeFilterSingle(type) {
      if (!this.selectedFilters.hasOwnProperty(type)) return;
      this.selectedFilters[type] = '';
      this.updateFilterDisplay();
    },

    /**
     * Toggle a filter on/off (multi-select mode)
     */
    toggleFilter(type, value) {
      if (!this.selectedFilters.hasOwnProperty(type)) return;
      
      const index = this.selectedFilters[type].indexOf(value);
      if (index > -1) {
        this.selectedFilters[type].splice(index, 1);
      } else {
        this.selectedFilters[type].push(value);
      }
      
      this.updateFilterDisplay();
      this.updateDropdownVisuals();
    },

    /**
     * Remove a specific filter value (multi-select mode)
     */
    removeFilterMulti(type, value) {
      if (!this.selectedFilters.hasOwnProperty(type)) return;
      
      const index = this.selectedFilters[type].indexOf(value);
      if (index > -1) {
        this.selectedFilters[type].splice(index, 1);
      }
      
      this.updateFilterDisplay();
      this.updateDropdownVisuals();
    },

    /**
     * Update visual indication of selected items in dropdowns (multi-select)
     */
    updateDropdownVisuals() {
      if (!this.config.multiSelect) return;

      document.querySelectorAll('.dropdown-item[data-filter-type]').forEach(item => {
        const filterType = item.dataset.filterType;
        const filterValue = item.dataset.filterValue;
        
        if (this.selectedFilters[filterType] && 
            this.selectedFilters[filterType].includes(filterValue)) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    },

    /**
     * Update the filter display with selected tags
     */
    updateFilterDisplay() {
      if (!this.elements.filterTags || !this.elements.selectedFiltersContainer) return;

      // Clear current tags
      this.elements.filterTags.innerHTML = '';

      // Count active filters
      const totalFilters = this.countActiveFilters();

      // Show/hide container
      if (totalFilters === 0) {
        this.elements.selectedFiltersContainer.style.display = 'none';
        return;
      }

      this.elements.selectedFiltersContainer.style.display = 'flex';

      // Create tags for each filter type
      this.config.filterTypes.forEach(type => {
        if (this.config.multiSelect) {
          // Multi-select: show each value as separate tag
          this.selectedFilters[type].forEach(value => {
            this.createFilterTag(type, value);
          });
        } else {
          // Single-select: show one tag per type
          if (this.selectedFilters[type]) {
            this.createFilterTag(type, this.selectedFilters[type]);
          }
        }
      });
    },

    /**
     * Count the total number of active filters
     */
    countActiveFilters() {
      if (this.config.multiSelect) {
        return this.config.filterTypes.reduce((count, type) => {
          return count + (this.selectedFilters[type]?.length || 0);
        }, 0);
      } else {
        return this.config.filterTypes.reduce((count, type) => {
          return count + (this.selectedFilters[type] ? 1 : 0);
        }, 0);
      }
    },

    /**
     * Create a filter tag badge
     */
    createFilterTag(type, value) {
      const tag = document.createElement('span');
      tag.className = `${this.config.badgeClass} d-inline-flex align-items-center text-wrap`;
      
      const label = this.config.filterLabels[type] || type;
      const removeHandler = this.config.multiSelect ? 
        `removeFilterTag('${type}', '${value.replace(/'/g, "\\'")}')` :
        `removeFilterTag('${type}')`;
      
      tag.innerHTML = `
        ${label}: ${value}
        <button class="btn-close btn-close-white ms-2" onclick="${removeHandler}" aria-label="Remove filter"></button>
      `;
      
      this.elements.filterTags.appendChild(tag);
    },

    /**
     * Apply filters by updating form fields and submitting
     */
    applyFilters() {
      if (this.config.multiSelect && this.config.multipleInputs) {
        // Multi-select with multiple inputs mode: create separate input for each value
        this.applyFiltersMultipleInputs();
      } else {
        // Standard mode: update hidden form fields
        Object.keys(this.config.filterFieldMap).forEach(filterType => {
          const fieldId = this.config.filterFieldMap[filterType];
          const fieldElement = document.getElementById(fieldId);
          
          if (fieldElement) {
            if (this.config.multiSelect) {
              // Multi-select: join values with commas
              fieldElement.value = this.selectedFilters[filterType]?.join(',') || '';
            } else {
              // Single-select: set value directly
              fieldElement.value = this.selectedFilters[filterType] || '';
            }
          }
        });
      }

      // Submit the form
      this.elements.form.submit();
    },

    /**
     * Apply filters using multiple hidden inputs (expects repeated params)
     */
    applyFiltersMultipleInputs() {
      // Remove existing dynamic filter inputs
      Object.values(this.config.filterFieldMap).forEach(paramName => {
        document.querySelectorAll(`input[name="${paramName}"]:not([id])`).forEach(input => {
          input.remove();
        });
        
        // Also remove template hidden inputs
        const templateInput = document.getElementById(this.getFieldId(paramName));
        if (templateInput) {
          templateInput.remove();
        }
      });

      // Create new hidden inputs for each selected value
      Object.keys(this.config.filterFieldMap).forEach(filterType => {
        const paramName = this.config.filterFieldMap[filterType];
        const values = this.selectedFilters[filterType] || [];
        
        values.forEach(value => {
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = paramName;
          input.value = value;
          this.elements.form.appendChild(input);
        });
      });
    },

    /**
     * Get field ID from filter field map
     */
    getFieldId(paramName) {
      for (const [filterType, fieldParam] of Object.entries(this.config.filterFieldMap)) {
        if (fieldParam === paramName) {
          // Try to find corresponding element ID from formElementIds or construct it
          return `filter_${paramName}`;
        }
      }
      return null;
    },

    /**
     * Clear all filters
     */
    clearFilters() {
      // Reset all filters
      this.config.filterTypes.forEach(type => {
        if (this.config.multiSelect) {
          this.selectedFilters[type] = [];
        } else {
          this.selectedFilters[type] = '';
        }
      });

      this.updateFilterDisplay();
      
      if (this.config.multiSelect) {
        this.updateDropdownVisuals();
      }
    }
  };

  // Export to global scope
  window.SearchFilter = SearchFilter;

})(window);
