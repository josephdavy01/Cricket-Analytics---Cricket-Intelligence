/**
 * IPL Cricket Analytics — Client-side interactivity
 */

document.addEventListener('DOMContentLoaded', () => {
    // Animate elements on page load
    initAnimations();

    // Mobile sidebar toggle
    initMobileSidebar();

    // Score bar animations
    initScoreBars();
});

function initAnimations() {
    const elements = document.querySelectorAll('.animate-in');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    elements.forEach(el => {
        el.style.animationPlayState = 'paused';
        observer.observe(el);
    });
}

function initMobileSidebar() {
    const toggle = document.querySelector('.mobile-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('show');
        });

        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.remove('open');
                overlay.classList.remove('show');
            });
        }
    }
}

function initScoreBars() {
    const bars = document.querySelectorAll('.score-bar-fill');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const width = entry.target.dataset.width || '0';
                entry.target.style.width = width + '%';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    bars.forEach(bar => {
        bar.style.width = '0%';
        observer.observe(bar);
    });
}

// Utility: format numbers with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
