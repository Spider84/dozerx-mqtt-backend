// Custom JavaScript for Swagger UI - Collapse Schemas section by default
window.onload = function() {
    // Wait for Swagger UI to load completely
    setTimeout(function() {
        try {
            // Find the Schemas section
            const schemasSection = document.querySelector('div.opblock-section-section h4')?.parentElement.parentElement;
            
            if (schemasSection) {
                // Find the collapse/expand button
                const expandButton = schemasSection.querySelector('.opblock-summary-control');
                
                if (expandButton && expandButton.getAttribute('aria-expanded') === 'true') {
                    // Click to collapse if it's expanded
                    expandButton.click();
                    console.log('Schemas section collapsed by default');
                }
            }
        } catch (error) {
            console.log('Could not collapse Schemas section:', error);
        }
    }, 1000); // Wait 1 second for Swagger UI to fully load
};
