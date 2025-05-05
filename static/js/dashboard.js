/**
 * Dashboard JavaScript functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize interactive elements
    initializeInteractiveElements();
    
    // Load charts if the elements exist
    if (document.getElementById('dailyProcessedChart')) {
        loadDailyProcessedChart();
    }
    
    if (document.getElementById('flagDistributionChart')) {
        loadFlagDistributionChart();
    }
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refreshStats');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            refreshStats();
        });
    }
});

/**
 * Initialize interactive elements on the dashboard
 */
function initializeInteractiveElements() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Load the daily processed content chart
 */
function loadDailyProcessedChart() {
    // Get metrics data from the page
    const metricsData = JSON.parse(document.getElementById('metricsData').textContent);
    const dailyProcessed = metricsData.daily_processed || [];
    
    // Prepare data for the chart
    const dates = dailyProcessed.map(item => formatDate(item.date));
    const counts = dailyProcessed.map(item => item.value.count);
    
    // Create the chart
    const ctx = document.getElementById('dailyProcessedChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Daily Processed Content',
                data: counts,
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderColor: 'rgba(13, 110, 253, 0.8)',
                borderWidth: 2,
                tension: 0.3,
                pointBackgroundColor: 'rgba(13, 110, 253, 1)',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        drawBorder: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * Load the flag distribution pie chart
 */
function loadFlagDistributionChart() {
    // Get metrics data from the page
    const metricsData = JSON.parse(document.getElementById('metricsData').textContent);
    const flagDistribution = metricsData.flag_distribution || [];
    
    // Aggregate flag types across all days
    const aggregatedFlags = {};
    flagDistribution.forEach(item => {
        const flags = item.value;
        Object.keys(flags).forEach(flagType => {
            if (aggregatedFlags[flagType]) {
                aggregatedFlags[flagType] += flags[flagType];
            } else {
                aggregatedFlags[flagType] = flags[flagType];
            }
        });
    });
    
    // Prepare data for the chart
    const flagTypes = Object.keys(aggregatedFlags).map(type => formatFlagType(type));
    const flagCounts = Object.values(aggregatedFlags);
    
    // Colors for different flag types
    const flagColors = {
        'profanity': 'rgba(220, 53, 69, 0.8)',
        'hate_speech': 'rgba(255, 193, 7, 0.8)',
        'violence': 'rgba(253, 126, 20, 0.8)',
        'sexual_content': 'rgba(13, 110, 253, 0.8)',
        'harassment': 'rgba(111, 66, 193, 0.8)'
    };
    
    // Get colors for each flag type
    const colors = Object.keys(aggregatedFlags).map(type => {
        return flagColors[type] || 'rgba(108, 117, 125, 0.8)';
    });
    
    // Create the chart
    const ctx = document.getElementById('flagDistributionChart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: flagTypes,
            datasets: [{
                data: flagCounts,
                backgroundColor: colors,
                borderColor: 'rgba(255, 255, 255, 0.5)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Format date string from ISO to readable format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Format flag type to be more readable
 */
function formatFlagType(type) {
    // Replace underscores with spaces and capitalize each word
    return type.split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Refresh statistics by calling the API
 */
function refreshStats() {
    // Show loading state
    const refreshBtn = document.getElementById('refreshStats');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing...';
    }
    
    // Call the API to generate metrics
    fetch('/api/generate_metrics', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload the page to show updated metrics
            window.location.reload();
        } else {
            // Show error message
            alert('Error refreshing metrics: ' + (data.error || 'Unknown error'));
            
            // Reset button state
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Statistics';
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error refreshing metrics. Please try again.');
        
        // Reset button state
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Statistics';
        }
    });
}