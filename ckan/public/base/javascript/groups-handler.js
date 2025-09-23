/**
 * Simple Groups Handler for CKAN Dataset Form
 * Processes groups input field on form submission
 */
(function() {
    'use strict';

    console.log('[Groups Handler] Loading simple groups handler...');

    function initGroupsHandler() {
        if (typeof jQuery === 'undefined') {
            console.warn('[Groups Handler] jQuery not loaded yet, retrying...');
            setTimeout(initGroupsHandler, 500);
            return;
        }

        console.log('[Groups Handler] Initializing groups handler...');

        // Handle form submission
        jQuery(document).on('submit', '#dataset-edit', function(e) {
            console.log('[Groups Handler] Form submitted, processing groups...');

            var groupsInput = jQuery('#field-groups').val();
            console.log('[Groups Handler] Groups input value:', groupsInput);

            if (!groupsInput || groupsInput.trim() === '') {
                console.log('[Groups Handler] No groups input found');
                return;
            }

            // Split groups by comma and clean up
            var groupNames = groupsInput.split(',').map(function(name) {
                return name.trim();
            }).filter(function(name) {
                return name.length > 0;
            });

            console.log('[Groups Handler] Parsed group names:', groupNames);

            // Remove existing group fields
            jQuery('input[name^="groups__"]').remove();
            console.log('[Groups Handler] Removed existing group fields');

            // Add proper group fields for each group
            groupNames.forEach(function(groupName, index) {
                var hiddenField = jQuery('<input>')
                    .attr('type', 'hidden')
                    .attr('name', 'groups__' + index + '__name')
                    .val(groupName);

                jQuery('#dataset-edit').append(hiddenField);
                console.log('[Groups Handler] Added group field:', groupName, 'with name:', 'groups__' + index + '__name');
            });

            console.log('[Groups Handler] Groups processing completed');
        });

        console.log('[Groups Handler] Groups handler initialized successfully');
    }

    // Start initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGroupsHandler);
    } else {
        initGroupsHandler();
    }
})();