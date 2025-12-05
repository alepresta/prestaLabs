/**
 * Presta Labs - Government Theme JavaScript
 * Funcionalidades interactivas para la plataforma gubernamental
 */

class GovernmentSidebar {
    constructor() {
        this.sidebar = document.getElementById('governmentSidebar');
        this.isOpen = false;
        this.init();
    }
    
    init() {
        // Cerrar sidebar al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (this.isOpen && !this.sidebar.contains(e.target) && !e.target.classList.contains('sidebar-toggle')) {
                this.close();
            }
        });
        
        // Cerrar con tecla Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }
    
    toggle() {
        this.isOpen ? this.close() : this.open();
    }
    
    open() {
        this.sidebar.classList.add('active');
        this.isOpen = true;
        document.body.style.overflow = 'hidden';
    }
    
    close() {
        this.sidebar.classList.remove('active');
        this.isOpen = false;
        document.body.style.overflow = '';
    }
}

class GovernmentModals {
    constructor() {
        this.init();
    }
    
    init() {
        // Configurar modal de análisis express
        this.setupQuickAnalysis();
    }
    
    setupQuickAnalysis() {
        const modal = document.getElementById('quickAnalysisModal');
        const form = document.getElementById('quickAnalysisForm');
        
        if (!modal || !form) return;
        
        const submitBtn = modal.querySelector('.btn-primary');
        submitBtn?.addEventListener('click', (e) => {
            e.preventDefault();
            this.handleQuickAnalysis();
        });
    }
    
    handleQuickAnalysis() {
        const urlInput = document.getElementById('quickUrl');
        const url = urlInput?.value;
        
        if (!url) {
            this.showAlert('Por favor ingresa una URL válida', 'warning');
            return;
        }
        
        // Redirigir a análisis de URL individual
        window.location.href = `/analysis/analyze/single-url/?url=${encodeURIComponent(url)}`;
    }
    
    showAlert(message, type = 'info') {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="fas fa-info-circle me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const container = document.querySelector('.main-content .container-fluid');
        if (container) {
            container.insertAdjacentHTML('afterbegin', alertHtml);
        }
    }
}

class GovernmentUtils {
    static formatScore(score) {
        if (score >= 90) return { class: 'success', label: 'Excelente' };
        if (score >= 80) return { class: 'info', label: 'Bueno' };
        if (score >= 70) return { class: 'warning', label: 'Regular' };
        if (score >= 60) return { class: 'orange', label: 'Deficiente' };
        return { class: 'danger', label: 'Malo' };
    }
    
    static animateNumber(element, finalNumber, duration = 2000) {
        const start = 0;
        const increment = finalNumber / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= finalNumber) {
                current = finalNumber;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 16);
    }
    
    static showToast(message, type = 'info') {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-info-circle me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Remover el elemento después de que se oculte
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Inicializar componentes cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar sidebar
    window.governmentSidebar = new GovernmentSidebar();
    
    // Inicializar modales
    window.governmentModals = new GovernmentModals();
    
    // Animar números en cards al cargar
    const numberElements = document.querySelectorAll('.card-number');
    numberElements.forEach(element => {
        const finalNumber = parseInt(element.textContent);
        if (!isNaN(finalNumber)) {
            element.textContent = '0';
            GovernmentUtils.animateNumber(element, finalNumber);
        }
    });
    
    // Mejorar tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Configurar popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    
    console.log('🏛️ Presta Labs - Sistema gubernamental inicializado correctamente');
});

// Funciones globales para compatibilidad
function toggleSidebar() {
    window.governmentSidebar?.toggle();
}

function showNotification(message, type = 'info') {
    GovernmentUtils.showToast(message, type);
}
