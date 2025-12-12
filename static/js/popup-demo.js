/**
 * Demostraciones del Sistema de Popups PrestaLabs
 * Ejecuta en la consola del navegador para probar todas las funcionalidades
 */

// Función para probar todos los tipos de popup
function probarTodosLosPopups() {
    console.log('🚀 Iniciando demostración del Sistema de Popups PrestaLabs');
    
    // 1. Alerta simple
    setTimeout(() => {
        PrestaLabs.Popup.alerta('Este es un mensaje informativo simple');
    }, 500);
    
    // 2. Alerta con callback
    setTimeout(() => {
        PrestaLabs.Popup.alerta('Mensaje con callback personalizado', function() {
            console.log('✅ Callback de alerta ejecutado');
        }, {
            titulo: 'Alerta Personalizada',
            textoBoton: 'Entendido'
        });
    }, 3000);
    
    // 3. Confirmación simple
    setTimeout(() => {
        PrestaLabs.Popup.confirmar(
            '¿Deseas continuar con la demostración?',
            function() {
                console.log('✅ Usuario confirmó');
                PrestaLabs.Popup.exito('¡Perfecto! Continuamos...');
            },
            function() {
                console.log('❌ Usuario canceló');
                PrestaLabs.Popup.alerta('Demostración pausada');
            }
        );
    }, 6000);
    
    // 4. Confirmación peligrosa
    setTimeout(() => {
        PrestaLabs.Popup.confirmar(
            'Esta es una acción IRREVERSIBLE. ¿Estás completamente seguro?',
            function() {
                PrestaLabs.Popup.error('¡Acción peligrosa ejecutada!');
            },
            function() {
                PrestaLabs.Popup.exito('Buena decisión. Acción cancelada.');
            },
            {
                titulo: '⚠️ Acción Peligrosa',
                textoConfirmar: 'Sí, ejecutar',
                textoCancelar: 'No, cancelar',
                tipoBoton: 'danger'
            }
        );
    }, 10000);
    
    // 5. Mensaje de éxito
    setTimeout(() => {
        PrestaLabs.Popup.exito('¡Operación completada exitosamente!', function() {
            console.log('✅ Usuario cerró mensaje de éxito');
        });
    }, 14000);
    
    // 6. Mensaje de error
    setTimeout(() => {
        PrestaLabs.Popup.error('Error simulado para demostración', function() {
            console.log('🔥 Usuario cerró mensaje de error');
        });
    }, 16000);
    
    console.log('📋 Demostración programada. Los popups aparecerán cada 2-3 segundos...');
}

// Función para probar interceptación (opcional)
function activarInterceptacion() {
    console.log('🔄 Activando interceptación de alert() y confirm()...');
    
    // Activar interceptación
    PrestaLabs.Popup.interceptar.alert(true);
    PrestaLabs.Popup.interceptar.confirm(true);
    
    // Probar alert interceptado
    setTimeout(() => {
        alert('Este alert() ha sido interceptado y convertido en modal');
    }, 1000);
    
    // Probar confirm interceptado
    setTimeout(() => {
        if (confirm('Este confirm() también ha sido interceptado')) {
            alert('Usuario confirmó');
        } else {
            alert('Usuario canceló');
        }
    }, 3000);
}

// Función para desactivar interceptación
function desactivarInterceptacion() {
    console.log('🔙 Desactivando interceptación...');
    PrestaLabs.Popup.interceptar.alert(false);
    PrestaLabs.Popup.interceptar.confirm(false);
    
    // Probar que vuelve al comportamiento original
    setTimeout(() => {
        alert('Este es el alert() original del navegador');
    }, 1000);
}

// Función para probar estados de error
function probarManejoCrawling() {
    console.log('🕷️ Probando integración con sistema de crawling...');
    
    // Simular detener crawling
    PrestaLabs.Popup.confirmar(
        '¿Estás seguro de que quieres detener el crawling de ejemplo.com?',
        function() {
            // Simular proceso
            console.log('Deteniendo crawling...');
            
            // Simular éxito
            setTimeout(() => {
                PrestaLabs.Popup.exito('Crawling detenido exitosamente', function() {
                    console.log('Usuario puede recargar página ahora');
                });
            }, 1500);
        },
        function() {
            console.log('Cancelado por usuario');
        },
        {
            titulo: 'Detener Crawling',
            textoConfirmar: 'Sí, detener',
            textoCancelar: 'Cancelar',
            tipoBoton: 'warning'
        }
    );
}

// Exportar funciones para uso en consola
window.DemoPopups = {
    probarTodos: probarTodosLosPopups,
    activarInterceptacion: activarInterceptacion,
    desactivarInterceptacion: desactivarInterceptacion,
    probarCrawling: probarManejoCrawling
};

console.log(`
🎯 Sistema de Popups PrestaLabs cargado!

Para probar las funcionalidades, ejecuta en consola:

• DemoPopups.probarTodos()          - Prueba todos los tipos de popup
• DemoPopups.activarInterceptacion() - Intercepta alert() y confirm() nativos  
• DemoPopups.desactivarInterceptacion() - Restaura comportamiento original
• DemoPopups.probarCrawling()       - Prueba integración con crawling

También puedes usar directamente:
• PrestaLabs.Popup.alerta("mensaje")
• PrestaLabs.Popup.confirmar("mensaje", onConfirm, onCancel)
• PrestaLabs.Popup.exito("mensaje") 
• PrestaLabs.Popup.error("mensaje")
`);