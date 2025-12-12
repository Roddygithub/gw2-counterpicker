/**
 * GW2 CounterPicker - Frontend JavaScript
 * Enhanced interactions and visualizations
 */

// HTMX event handlers
document.addEventListener('htmx:afterRequest', function(event) {
    // Scroll to results after successful request
    if (event.detail.successful) {
        const target = event.detail.target;
        if (target) {
            setTimeout(() => {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }
});

document.addEventListener('htmx:beforeRequest', function(event) {
    // Add loading state
    const indicator = event.detail.elt.querySelector('.htmx-indicator');
    if (indicator) {
        indicator.classList.add('animate-spin');
    }
});

// Copy to clipboard helper
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Lien copié !', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Erreur lors de la copie', 'error');
    });
}

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-xl font-medium text-white z-50 animate-slide-up ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        'bg-gw2-purple'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Composition chart rendering
function renderCompositionChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    const colors = [
        '#8B5CF6', '#EC4899', '#22D3EE', '#10B981', '#F59E0B',
        '#EF4444', '#6366F1', '#14B8A6', '#F97316', '#8B5CF6'
    ];
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: colors.slice(0, Object.keys(data).length),
                borderColor: '#0F0A1F',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#9CA3AF',
                        font: {
                            family: 'Inter'
                        }
                    }
                }
            }
        }
    });
}

// Hourly evolution chart
function renderEvolutionChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    const specs = [...new Set(data.flatMap(h => Object.keys(h.spec_counts)))].slice(0, 5);
    const colors = ['#8B5CF6', '#EC4899', '#22D3EE', '#10B981', '#F59E0B'];
    
    const datasets = specs.map((spec, i) => ({
        label: spec,
        data: data.map(h => h.spec_counts[spec] || 0),
        borderColor: colors[i],
        backgroundColor: colors[i] + '20',
        fill: true,
        tension: 0.4
    }));
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(h => h.hour),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#1F2937'
                    },
                    ticks: {
                        color: '#9CA3AF'
                    }
                },
                x: {
                    grid: {
                        color: '#1F2937'
                    },
                    ticks: {
                        color: '#9CA3AF'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#9CA3AF'
                    }
                }
            }
        }
    });
}

// Parallax effect for background
document.addEventListener('mousemove', function(e) {
    const nebula = document.querySelector('.nebula-bg::before');
    if (nebula) {
        const x = e.clientX / window.innerWidth;
        const y = e.clientY / window.innerHeight;
        nebula.style.transform = `translate(${x * 20}px, ${y * 20}px)`;
    }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔮 GW2 CounterPicker initialized');
    console.log('Made with rage, love and 15 years of WvW pain.');
});
