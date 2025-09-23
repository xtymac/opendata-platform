/**
 * Enhanced Search functionality for Yamaguchi OpenData Platform
 * Provides universal search across datasets, organizations, and groups
 */
(function() {
    'use strict';

    console.log('[Yamaguchi Search] Loading enhanced search functionality...');

    function initYamaguchiSearch() {
        if (typeof jQuery === 'undefined') {
            console.warn('[Yamaguchi Search] jQuery not loaded yet, retrying...');
            setTimeout(initYamaguchiSearch, 500);
            return;
        }

        console.log('[Yamaguchi Search] Initializing enhanced search...');

        // Enhanced search form submission
        jQuery(document).on('submit', '.yamaguchi-search-form', function(e) {
            var searchTerm = jQuery('#yamaguchi-main-search').val().trim();

            if (!searchTerm) {
                e.preventDefault();
                jQuery('#yamaguchi-main-search').focus();
                return false;
            }

            // Add analytics tracking if available
            if (typeof gtag !== 'undefined') {
                gtag('event', 'search', {
                    'search_term': searchTerm,
                    'search_source': 'yamaguchi_hero'
                });
            }

            console.log('[Yamaguchi Search] Searching for:', searchTerm);
        });

        // Search input enhancements
        var searchInput = jQuery('#yamaguchi-main-search');

        // Add keyboard shortcuts
        searchInput.on('keydown', function(e) {
            // ESC to clear
            if (e.keyCode === 27) {
                jQuery(this).val('').focus();
            }
        });

        // Add search suggestions (basic implementation)
        searchInput.on('input', function() {
            var term = jQuery(this).val().trim();

            // Simple debounced search suggestions could be added here
            if (term.length >= 3) {
                // Future: implement autocomplete suggestions
                console.log('[Yamaguchi Search] Search term:', term);
            }
        });

        // Category tag analytics
        jQuery(document).on('click', '.yamaguchi-tag', function() {
            var category = jQuery(this).find('span').text();

            if (typeof gtag !== 'undefined') {
                gtag('event', 'category_click', {
                    'category_name': category,
                    'click_source': 'yamaguchi_hero'
                });
            }

            console.log('[Yamaguchi Search] Category clicked:', category);
        });

        // Search button hover effects
        jQuery('.yamaguchi-search-btn').on('mouseenter', function() {
            jQuery(this).addClass('pulse-animation');
        }).on('mouseleave', function() {
            jQuery(this).removeClass('pulse-animation');
        });

        console.log('[Yamaguchi Search] Enhanced search functionality loaded successfully');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initYamaguchiSearch);
    } else {
        initYamaguchiSearch();
    }

})();