(function() {
    'use strict';

    /* Registry Description Widget Handler
     *
     * For each container with [data-registry-description-for], finds the paired <select> element and displays the
     * selected option's data-description. Updates on change events and re-initialises after htmx:afterSettle.
     */

    function updateDescription(selectEl, container) {
        var selected = selectEl.options[selectEl.selectedIndex];
        var description = selected ? selected.getAttribute('data-description') : '';

        if (description) {
            container.textContent = description;
            container.style.display = '';
        } else {
            container.textContent = '';
            container.style.display = 'none';
        }
    }

    function initRegistryDescriptions() {
        var containers = document.querySelectorAll('[data-registry-description-for]');

        containers.forEach(function(container) {
            var selectId = container.getAttribute('data-registry-description-for');
            var selectEl = document.getElementById(selectId);

            if (!selectEl) {
                return;
            }

            // Avoid double-binding
            if (selectEl.hasAttribute('data-registry-description-bound')) {
                // Still update in case the DOM was replaced (e.g.: with htmx)
                updateDescription(selectEl, container);
                return;
            }

            selectEl.setAttribute('data-registry-description-bound', 'true');

            // Set the initial description
            updateDescription(selectEl, container);

            // Listen for any changes
            selectEl.addEventListener('change', function() {
                updateDescription(selectEl, container);
            });
        });
    }

    // Initialise when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRegistryDescriptions);
    } else {
        initRegistryDescriptions();
    }

    // Re-initialise after htmx swaps
    document.addEventListener('htmx:afterSettle', function() {
        initRegistryDescriptions();
    });
})();
