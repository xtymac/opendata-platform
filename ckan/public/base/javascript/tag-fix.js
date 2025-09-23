/**
 * CKAN Tag Input Fix
 * Fixes issues with tags disappearing when entered
 */
(function() {
    'use strict';

    console.log('[Tag Fix] Loading tag fix script...');

    // Wait for jQuery and page to be ready
    function initTagFix() {
        if (typeof jQuery === 'undefined' || typeof jQuery.fn.select2 === 'undefined') {
            console.warn('[Tag Fix] jQuery or Select2 not loaded yet, retrying...');
            setTimeout(initTagFix, 500);
            return;
        }

        console.log('[Tag Fix] Initializing tag fix...');

        // Fix for tag input fields
        function fixTagInput() {
            var tagInputs = jQuery('input[name="tag_string"], input[id="field-tags"], input[data-module="autocomplete"][data-module-tags=""]');

            tagInputs.each(function() {
                var $input = jQuery(this);

                // Skip if already initialized properly
                if ($input.data('tag-fix-applied')) {
                    return;
                }

                console.log('[Tag Fix] Fixing tag input:', $input.attr('name') || $input.attr('id'));

                // Store original value
                var originalValue = $input.val();

                // Remove any existing Select2 instance
                if ($input.data('select2')) {
                    $input.select2('destroy');
                }

                // Reinitialize with correct settings
                try {
                    $input.select2({
                        tags: true,
                        tokenSeparators: [','],
                        width: '100%',
                        placeholder: 'Enter tags...',
                        minimumInputLength: 0,
                        maximumInputLength: 100,
                        createTag: function(params) {
                            var term = jQuery.trim(params.term);
                            if (term === '') {
                                return null;
                            }
                            return {
                                id: term,
                                text: term,
                                newTag: true
                            };
                        },
                        insertTag: function(data, tag) {
                            // Insert at the end
                            data.push(tag);
                        }
                    });

                    // Restore original value if any
                    if (originalValue) {
                        var tags = originalValue.split(',').map(function(tag) {
                            return jQuery.trim(tag);
                        }).filter(function(tag) {
                            return tag.length > 0;
                        });

                        tags.forEach(function(tag) {
                            var option = new Option(tag, tag, true, true);
                            $input.append(option).trigger('change');
                        });
                    }

                    // Mark as fixed
                    $input.data('tag-fix-applied', true);

                    // Handle form submission to ensure tags are properly formatted
                    var $form = $input.closest('form');
                    if ($form.length && !$form.data('tag-fix-submit-handler')) {
                        $form.on('submit', function() {
                            var values = $input.val();
                            if (Array.isArray(values)) {
                                $input.val(values.join(','));
                            }
                        });
                        $form.data('tag-fix-submit-handler', true);
                    }

                    console.log('[Tag Fix] Successfully fixed tag input');

                } catch (e) {
                    console.error('[Tag Fix] Error fixing tag input:', e);
                }
            });
        }

        // Apply fix on page load
        jQuery(document).ready(function() {
            setTimeout(fixTagInput, 1000);
        });

        // Reapply fix when new content is loaded (AJAX)
        jQuery(document).on('DOMNodeInserted', function(e) {
            if (jQuery(e.target).find('input[name="tag_string"], input[id="field-tags"]').length > 0) {
                setTimeout(fixTagInput, 500);
            }
        });

        // Fix specifically for edit pages
        if (window.location.pathname.includes('/edit')) {
            console.log('[Tag Fix] Edit page detected, applying additional fixes...');
            setTimeout(function() {
                fixTagInput();
                // Try again in case of delayed initialization
                setTimeout(fixTagInput, 2000);
            }, 1500);
        }

        // Also listen for CKAN module events
        if (window.ckan && window.ckan.pubsub) {
            window.ckan.pubsub.subscribe('module.initialized', function() {
                setTimeout(fixTagInput, 500);
            });
        }

        console.log('[Tag Fix] Tag fix script loaded successfully');
    }

    // Start initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTagFix);
    } else {
        initTagFix();
    }
})();