from django.shortcuts import render
from django.http import HttpResponse


def test_session_recovery(request):
    """Vista de prueba para la recuperación de sesión"""

    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prueba de Recuperación de Sesión - PrestaLabs</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
</head>
<body>
    <div class="container py-4">
        <h2 class="mb-4">🧪 Prueba de Recuperación de Sesión</h2>
        
        <div class="alert alert-info">
            <h5><i class="bi bi-info-circle"></i> ¿Qué hace esta prueba?</h5>
            <p class="mb-2">Esta página simula exactamente lo que pediste: 
                <strong>"me gustaría seguir viendo el div progreso-crawling"</strong> 
                después de cerrar y reabrir el navegador.</p>
            <ul class="mb-0">
                <li>✅ Recupera automáticamente el último crawling completado</li>
                <li>✅ Muestra la barra de progreso al 100%</li>
                <li>✅ Mantiene visible toda la información: URLs, tiempos, conteo</li>
                <li>✅ Persiste el estado entre sesiones del navegador</li>
            </ul>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>🔧 Panel de Control</h5>
                    </div>
                    <div class="card-body">
                        <button id="btnSimular" class="btn btn-primary mb-3">
                            <i class="bi bi-arrow-clockwise"></i> Simular Recuperación Manual
                        </button>
                        <div id="log" class="mt-3" style="font-family: monospace; font-size: 0.9rem; background: #f8f9fa; padding: 10px; border-radius: 5px; height: 200px; overflow-y: auto;"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <!-- Este es el div que permanece visible tras la recuperación de sesión -->
                <div id="progreso-crawling" class="mb-4" style="display: none;">
                    <div class="card border-success">
                        <div class="card-header bg-success text-white">
                            <h5 class="mb-0">
                                <i class="bi bi-check-circle"></i> Crawling Completado - Sesión Recuperada
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-3">
                                <span class="me-2" style="font-size:1.5em;color:#198754;">
                                    <i class="bi bi-globe"></i>
                                </span>
                                <h6 class="mb-0">Dominio: <span id="dominio-actual"></span></h6>
                            </div>
                            
                            <!-- Barra de Progreso al 100% -->
                            <div class="mb-3">
                                <label class="form-label">Progreso del análisis:</label>
                                <div class="progress" style="height: 1.5rem;">
                                    <div id="barra-progreso" class="progress-bar bg-success fw-bold" role="progressbar" style="width: 0%">0%</div>
                                </div>
                            </div>
                            
                            <!-- Información de URLs -->
                            <div class="row mb-3">
                                <div class="col-auto">
                                    <span id="count-urls" class="badge bg-success fs-6">URLs encontradas: 0</span>
                                </div>
                                <div class="col-auto">
                                    <span class="badge bg-info">Completado</span>
                                </div>
                            </div>
                            
                            <!-- Información de Tiempo -->
                            <div class="mb-3">
                                <small class="text-muted">
                                    <i class="bi bi-clock"></i> 
                                    <strong>Inicio:</strong> <span id="hora-inicio">--</span> | 
                                    <strong>Fin:</strong> <span id="hora-fin">--</span> | 
                                    <strong>Duración:</strong> <span id="duracion">--</span>
                                </small>
                            </div>
                            
                            <!-- Lista Completa de URLs -->
                            <div id="urls-container">
                                <h6><i class="bi bi-list-ul"></i> URLs Encontradas:</h6>
                                <div class="list-group" id="lista-urls" style="max-height: 300px; overflow-y: auto;">
                                    <!-- URLs se cargarán dinámicamente -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function log(mensaje, tipo = 'info') {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const colorClass = {
                'info': 'text-primary',
                'success': 'text-success', 
                'error': 'text-danger',
                'warning': 'text-warning'
            }[tipo] || 'text-dark';
            
            logDiv.innerHTML += `<div class="${colorClass}">[${time}] ${mensaje}</div>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        async function cargarUltimoProgreso() {
            try {
                log('🔍 Consultando endpoint /analisis/estado/...', 'info');
                
                const response = await fetch('/analisis/estado/', {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                log('📊 Respuesta del servidor recibida correctamente', 'success');
                
                if (data.progreso && data.progreso.urls && data.progreso.urls.length > 0) {
                    log(`✨ ¡ÉXITO! Crawling encontrado con ${data.progreso.count} URLs`, 'success');
                    
                    // ⭐ MOSTRAR EL DIV PROGRESO-CRAWLING (esto es lo que pediste!)
                    const progresoDiv = document.getElementById('progreso-crawling');
                    progresoDiv.style.display = 'block';
                    log('👁️ div#progreso-crawling ahora VISIBLE', 'success');
                    
                    // Actualizar dominio
                    document.getElementById('dominio-actual').textContent = data.progreso.dominio || 'No especificado';
                    
                    // ⭐ BARRA DE PROGRESO AL 100% (mantener visible como solicitado)
                    const porcentaje = data.progreso.porcentaje || 100;
                    const barraProgreso = document.getElementById('barra-progreso');
                    barraProgreso.style.width = porcentaje + '%';
                    barraProgreso.textContent = porcentaje + '%';
                    log(`📊 Barra de progreso: ${porcentaje}%`, 'success');
                    
                    // ⭐ CONTEO DE URLs (mantener visible como solicitado)
                    const countUrls = data.progreso.count || data.progreso.urls.length;
                    document.getElementById('count-urls').textContent = `URLs encontradas: ${countUrls}`;
                    log(`🔢 URLs contabilizadas: ${countUrls}`, 'success');
                    
                    // ⭐ INFORMACIÓN DE TIEMPO (mantener visible como solicitado)
                    document.getElementById('hora-inicio').textContent = data.progreso.hora_inicio || '--';
                    document.getElementById('hora-fin').textContent = data.progreso.hora_fin || '--';
                    document.getElementById('duracion').textContent = data.progreso.duracion || '--';
                    log('⏱️ Información de tiempo actualizada', 'success');
                    
                    // ⭐ LISTA COMPLETA DE URLs (mantener visible como solicitado)
                    const listaUrls = document.getElementById('lista-urls');
                    listaUrls.innerHTML = '';
                    
                    data.progreso.urls.forEach((url, index) => {
                        const urlItem = document.createElement('div');
                        urlItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                        urlItem.innerHTML = `
                            <small><code>${url}</code></small>
                            <span class="badge bg-success">${index + 1}</span>
                        `;
                        listaUrls.appendChild(urlItem);
                    });
                    
                    log(`🎯 OBJETIVO CUMPLIDO: div#progreso-crawling visible con TODA la info`, 'success');
                    log(`📝 Incluye: barra al ${porcentaje}%, ${countUrls} URLs, tiempos, lista completa`, 'success');
                    
                } else {
                    log('⚠️ No hay crawling completado disponible para mostrar', 'warning');
                    log('💡 Ejecuta un análisis de dominio primero', 'info');
                }
                
            } catch (error) {
                log(`❌ Error: ${error.message}`, 'error');
            }
        }
        
        // Botón manual
        document.getElementById('btnSimular').addEventListener('click', function() {
            document.getElementById('log').innerHTML = '';
            log('🔄 Recuperación manual iniciada...', 'info');
            cargarUltimoProgreso();
        });
        
        // ⭐ RECUPERACIÓN AUTOMÁTICA (simula reabrir el navegador)
        document.addEventListener('DOMContentLoaded', function() {
            log('🌐 Página cargada - Simulando sesión recuperada automáticamente', 'info');
            log('🎯 Objetivo: Mantener visible div#progreso-crawling con toda la info', 'info');
            setTimeout(cargarUltimoProgreso, 1000);
        });
    </script>
</body>
</html>"""

    return HttpResponse(html_content)
