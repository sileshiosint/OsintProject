// Social Media OSINT Tool - Client-side JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize tooltips and popovers
    initializeBootstrapComponents();
    
    // Initialize platform selection handlers
    initializePlatformHandlers();
    
    // Initialize search form handlers
    initializeSearchHandlers();
}

function initializeFormValidation() {
    // Add custom validation for search forms
    const forms = document.querySelectorAll('form[id$="Form"]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const queryInput = form.querySelector('input[name="query"]');
            const platformCheckboxes = form.querySelectorAll('input[name="platforms"]:checked');
            
            let isValid = true;
            
            // Validate query input
            if (!queryInput.value.trim()) {
                showFieldError(queryInput, 'Please enter a search term');
                isValid = false;
            } else {
                clearFieldError(queryInput);
            }
            
            // Validate platform selection
            if (platformCheckboxes.length === 0) {
                showPlatformError('Please select at least one platform');
                isValid = false;
            } else {
                clearPlatformError();
            }
            
            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();
            } else {
                // Show loading state
                showFormLoading(form);
            }
        });
    });
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    // Remove existing error message
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function showPlatformError(message) {
    const platformSection = document.querySelector('.form-check');
    if (platformSection) {
        const parentContainer = platformSection.closest('.mb-4');
        
        // Remove existing error
        const existingError = parentContainer.querySelector('.platform-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Add new error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'platform-error text-danger small mt-2';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>${message}`;
        parentContainer.appendChild(errorDiv);
    }
}

function clearPlatformError() {
    const errorDiv = document.querySelector('.platform-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function showFormLoading(form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Searching...';
    }
}

function initializeBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

function initializePlatformHandlers() {
    // Handle "Select All" functionality for platforms
    const platformContainers = document.querySelectorAll('.form-check input[type="checkbox"]');
    
    // Add select all/none buttons to platform sections
    const platformLabels = document.querySelectorAll('label.form-label');
    platformLabels.forEach(label => {
        if (label.textContent.includes('Select Platforms')) {
            const container = label.parentNode;
            if (container && !container.querySelector('.platform-controls')) {
                const controlsDiv = document.createElement('div');
                controlsDiv.className = 'platform-controls mb-2';
                controlsDiv.innerHTML = `
                    <button type="button" class="btn btn-sm btn-outline-secondary me-2" onclick="selectAllPlatforms(this)">
                        Select All
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="selectNonePlatforms(this)">
                        Select None
                    </button>
                `;
                container.insertBefore(controlsDiv, container.querySelector('.row'));
            }
        }
    });
}

function selectAllPlatforms(button) {
    const container = button.closest('.mb-4');
    const checkboxes = container.querySelectorAll('input[type="checkbox"][name="platforms"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
    clearPlatformError();
}

function selectNonePlatforms(button) {
    const container = button.closest('.mb-4');
    const checkboxes = container.querySelectorAll('input[type="checkbox"][name="platforms"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
}

function initializeSearchHandlers() {
    // Handle tab switching with query preservation
    const searchTabs = document.querySelectorAll('#searchTabs button[data-bs-toggle="tab"]');
    
    searchTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetPane = document.querySelector(event.target.getAttribute('data-bs-target'));
            const queryInput = targetPane.querySelector('input[name="query"]');
            
            // Focus on the query input when tab is shown
            if (queryInput) {
                setTimeout(() => queryInput.focus(), 100);
            }
        });
    });
    
    // Handle Enter key in search inputs
    const queryInputs = document.querySelectorAll('input[name="query"]');
    queryInputs.forEach(input => {
        input.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                const form = input.closest('form');
                if (form) {
                    // Trigger form validation before submit
                    const submitButton = form.querySelector('button[type="submit"]');
                    if (submitButton) {
                        submitButton.click();
                    }
                }
            }
        });
    });
}

// Utility functions for results page
function updateSearchProgress(message) {
    const statusMessage = document.getElementById('statusMessage');
    if (statusMessage) {
        statusMessage.innerHTML = `<small>${message}</small>`;
    }
}

function animateProgressBar() {
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = '0%';
        setTimeout(() => {
            progressBar.style.width = '100%';
            progressBar.style.transition = 'width 30s linear';
        }, 100);
    }
}

// Export functionality
function exportSearchResults(searchType, query, results) {
    const exportData = {
        searchType: searchType,
        query: query,
        timestamp: new Date().toISOString(),
        results: results,
        exportedBy: 'Social Media OSINT Tool'
    };
    
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `${searchType}_${query}_${new Date().getTime()}.json`;
    link.click();
    
    // Clean up
    URL.revokeObjectURL(link.href);
}

// Error handling utilities
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.querySelector('.container');
    if (!alertContainer) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
    
    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv && alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }
}

// Local storage utilities for caching recent searches
function saveRecentSearch(searchType, query, platforms) {
    const recentSearches = getRecentSearches();
    const newSearch = {
        searchType,
        query,
        platforms,
        timestamp: new Date().toISOString()
    };
    
    // Remove duplicates
    const filtered = recentSearches.filter(search => 
        !(search.searchType === searchType && search.query === query)
    );
    
    // Add new search at beginning
    filtered.unshift(newSearch);
    
    // Keep only last 10 searches
    const limited = filtered.slice(0, 10);
    
    localStorage.setItem('osint_recent_searches', JSON.stringify(limited));
}

function getRecentSearches() {
    try {
        const stored = localStorage.getItem('osint_recent_searches');
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.warn('Error loading recent searches:', error);
        return [];
    }
}

function clearRecentSearches() {
    localStorage.removeItem('osint_recent_searches');
    showAlert('Recent searches cleared', 'success');
}

// Platform availability checker
function checkPlatformAvailability() {
    // This could be extended to ping platforms and check if they're accessible
    // For now, it's a placeholder for future functionality
    const platforms = ['twitter', 'instagram', 'reddit'];
    const status = {};
    
    platforms.forEach(platform => {
        status[platform] = 'available'; // This would be dynamically checked
    });
    
    return status;
}

// Copy to clipboard utility
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showAlert('Copied to clipboard!', 'success', 2000);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            fallbackCopyTextToClipboard(text);
        });
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showAlert('Copied to clipboard!', 'success', 2000);
        } else {
            showAlert('Failed to copy to clipboard', 'warning', 3000);
        }
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        showAlert('Copy not supported', 'warning', 3000);
    }
    
    document.body.removeChild(textArea);
}

// Theme detection and handling
function detectPreferredTheme() {
    const stored = localStorage.getItem('osint_theme');
    if (stored) {
        return stored;
    }
    
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem('osint_theme', theme);
}

// Initialize theme on load
document.addEventListener('DOMContentLoaded', function() {
    const preferredTheme = detectPreferredTheme();
    setTheme(preferredTheme);
});

// Performance monitoring
function measurePageLoadTime() {
    window.addEventListener('load', function() {
        const loadTime = performance.now();
        console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
        
        // Send analytics if needed (placeholder)
        // analytics.track('page_load_time', loadTime);
    });
}

// Initialize performance monitoring
measurePageLoadTime();

// Service worker registration (for future offline functionality)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Service worker registration would go here
        // navigator.serviceWorker.register('/sw.js');
    });
}
