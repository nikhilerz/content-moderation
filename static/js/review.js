/**
 * Review page JavaScript functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Set up action buttons
    setupActionButtons();
    
    // Highlight flagged terms in the content
    highlightFlaggedTerms();
    
    // Set up explanation accordions
    setupExplanationAccordions();
});

/**
 * Set up event listeners for approve/reject buttons
 */
function setupActionButtons() {
    // Approve button
    const approveBtn = document.getElementById('approveBtn');
    if (approveBtn) {
        approveBtn.addEventListener('click', function() {
            document.getElementById('statusField').value = 'approved';
            if (confirmAction('approve')) {
                document.getElementById('updateForm').submit();
            }
        });
    }
    
    // Reject button
    const rejectBtn = document.getElementById('rejectBtn');
    if (rejectBtn) {
        rejectBtn.addEventListener('click', function() {
            document.getElementById('statusField').value = 'rejected';
            if (confirmAction('reject')) {
                document.getElementById('updateForm').submit();
            }
        });
    }
    
    // Back button (no confirmation needed)
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', function() {
            window.history.back();
        });
    }
}

/**
 * Confirm moderation action before submitting
 */
function confirmAction(actionText) {
    const notes = document.getElementById('notesField').value.trim();
    let message = `Are you sure you want to ${actionText} this content?`;
    
    if (!notes) {
        const addNotes = confirm(`You haven't added any notes. Would you like to add notes before ${actionText}ing?`);
        if (addNotes) {
            document.getElementById('notesField').focus();
            return false;
        }
    }
    
    return confirm(message);
}

/**
 * Highlight flagged terms in the content
 */
function highlightFlaggedTerms() {
    // Get the content element
    const contentElement = document.getElementById('contentText');
    if (!contentElement) return;
    
    // Get flag explanations data
    const flagExplanationsElement = document.getElementById('flagExplanations');
    if (!flagExplanationsElement) return;
    
    const flagExplanations = JSON.parse(flagExplanationsElement.textContent || '{}');
    
    // Get the content text
    let contentText = contentElement.textContent;
    
    // Create a map to store all terms and their categories
    const termMap = {};
    
    // Process each flag category
    Object.keys(flagExplanations).forEach(category => {
        const explanation = flagExplanations[category];
        
        // Process each term in the explanation
        explanation.forEach(item => {
            const term = item.term;
            const coefficient = item.coefficient;
            
            // Only highlight terms with positive coefficients
            if (coefficient > 0) {
                termMap[term] = category;
            }
        });
    });
    
    // Sort terms by length (longest first) to handle overlapping terms
    const sortedTerms = Object.keys(termMap).sort((a, b) => b.length - a.length);
    
    // Replace terms with highlighted versions
    sortedTerms.forEach(term => {
        const category = termMap[term];
        const highlightClass = `highlight-${category.replace('_', '-')}`;
        
        // Use regular expression to match whole words only
        const regex = new RegExp(`\\b${escapeRegex(term)}\\b`, 'gi');
        contentText = contentText.replace(regex, `<span class="${highlightClass}" title="${category}">$&</span>`);
    });
    
    // Update the content element
    contentElement.innerHTML = contentText;
}

/**
 * Set up explanation accordions for each flag type
 */
function setupExplanationAccordions() {
    // Get all accordion buttons
    const accordionBtns = document.querySelectorAll('.explanation-toggle');
    
    // Add click event listeners
    accordionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Get the target content
            const targetId = this.getAttribute('data-bs-target');
            const targetContent = document.querySelector(targetId);
            
            // Toggle the expanded state
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            this.setAttribute('aria-expanded', !isExpanded);
            
            // Toggle the collapse class
            if (isExpanded) {
                targetContent.classList.remove('show');
            } else {
                targetContent.classList.add('show');
            }
            
            // Toggle the icon
            const icon = this.querySelector('i');
            if (icon) {
                if (isExpanded) {
                    icon.classList.remove('fa-chevron-up');
                    icon.classList.add('fa-chevron-down');
                } else {
                    icon.classList.remove('fa-chevron-down');
                    icon.classList.add('fa-chevron-up');
                }
            }
        });
    });
}

/**
 * Get CSS class for highlighting based on flag category
 */
function getCategoryColorClass(category) {
    const colorMap = {
        'profanity': 'danger',
        'hate_speech': 'warning',
        'violence': 'orange',
        'sexual_content': 'primary',
        'harassment': 'purple'
    };
    
    return colorMap[category] || 'secondary';
}

/**
 * Escape special characters for regex
 */
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}