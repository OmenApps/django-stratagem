(function() {
    'use strict';

    /**
     * Hierarchical Registry Field Handler
     *
     * Cascades parent field selections to filter child field dropdowns
     * using the RegistryChoicesAPIView endpoint.
     */

    function getChoicesUrl() {
        // Try to find the URL from a data attribute on body or a meta tag
        var el = document.querySelector('[data-registry-choices-url]');
        if (el) {
            return el.getAttribute('data-registry-choices-url');
        }
        // Fallback to a conventional URL
        return '/api/registry/choices/';
    }

    function updateChildField(childSelect, registryName, parentValue) {
        if (!parentValue) {
            // Clear child options and add empty option
            childSelect.innerHTML = '';
            var emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '---------';
            childSelect.appendChild(emptyOption);
            childSelect.dispatchEvent(new Event('change'));
            return;
        }

        var url = getChoicesUrl();
        var params = new URLSearchParams({
            registry: registryName,
            parent: parentValue
        });

        fetch(url + '?' + params.toString(), {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(function(data) {
            var currentValue = childSelect.value;
            childSelect.innerHTML = '';

            // Add empty option
            var emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '---------';
            childSelect.appendChild(emptyOption);

            // Add choices from response
            var choices = data.choices || [];
            for (var i = 0; i < choices.length; i++) {
                var option = document.createElement('option');
                option.value = choices[i][0];
                option.textContent = choices[i][1];
                if (choices[i][0] === currentValue) {
                    option.selected = true;
                }
                childSelect.appendChild(option);
            }

            childSelect.dispatchEvent(new Event('change'));
        })
        .catch(function(error) {
            console.error('Error fetching hierarchical choices:', error);
        });
    }

    function initHierarchicalFields() {
        var hierarchicalFields = document.querySelectorAll('[data-hierarchical="true"]');

        hierarchicalFields.forEach(function(childSelect) {
            var parentFieldName = childSelect.getAttribute('data-parent-field');
            var registryName = childSelect.getAttribute('data-registry');

            if (!parentFieldName || !registryName) {
                return;
            }

            // Find the parent select element
            var parentSelect = document.getElementById('id_' + parentFieldName);
            if (!parentSelect) {
                return;
            }

            // Listen for parent changes
            parentSelect.addEventListener('change', function() {
                updateChildField(childSelect, registryName, parentSelect.value);
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHierarchicalFields);
    } else {
        initHierarchicalFields();
    }
})();
