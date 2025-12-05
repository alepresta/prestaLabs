from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.utils import timezone
from .models import Domain, CrawlingSession, URLAnalysis
from .services import AccessibilityAnalyzer, WebCrawler
import json
from django.views.decorators.csrf import csrf_exempt

@login_required
def dashboard(request):
    """Vista principal del dashboard."""
    # Estadísticas generales
    stats = {
        'total_domains': Domain.objects.filter(created_by=request.user).count(),
        'total_sessions': CrawlingSession.objects.filter(started_by=request.user).count(),
        'total_urls_analyzed': URLAnalysis.objects.filter(session__started_by=request.user).count(),
        'avg_accessibility_score': URLAnalysis.objects.filter(
            session__started_by=request.user,
            accessibility_score__isnull=False
        ).aggregate(avg_score=Avg('accessibility_score'))['avg_score'] or 0
    }
    
    # Sesiones recientes
    recent_sessions = CrawlingSession.objects.filter(
        started_by=request.user
    ).order_by('-started_at')[:5]
    
    # Dominios del usuario
    user_domains = Domain.objects.filter(created_by=request.user, is_active=True)[:5]
    
    # URLs con mejores scores
    top_urls = URLAnalysis.objects.filter(
        session__started_by=request.user,
        accessibility_score__isnull=False
    ).order_by('-accessibility_score')[:5]
    
    context = {
        'stats': stats,
        'recent_sessions': recent_sessions,
        'user_domains': user_domains,
        'top_urls': top_urls,
    }
    
    return render(request, 'analysis/dashboard.html', context)

@login_required
def domain_list(request):
    """Lista de dominios del usuario."""
    domains = Domain.objects.filter(created_by=request.user)
    return render(request, 'analysis/domain_list.html', {'domains': domains})

@login_required
def add_domain(request):
    """Agregar nuevo dominio."""
    if request.method == 'POST':
        name = request.POST.get('name')
        url = request.POST.get('url')
        
        if name and url:
            try:
                domain = Domain.objects.create(
                    name=name,
                    url=url,
                    created_by=request.user
                )
                messages.success(request, f'Dominio "{name}" agregado exitosamente.')
                return redirect('analysis:domain_detail', domain_id=domain.id)
            except Exception as e:
                messages.error(request, f'Error al agregar dominio: {str(e)}')
        else:
            messages.error(request, 'Nombre y URL son requeridos.')
    
    return render(request, 'analysis/add_domain.html')

@login_required
def domain_detail(request, domain_id):
    """Detalle de un dominio específico."""
    domain = get_object_or_404(Domain, id=domain_id, created_by=request.user)
    sessions = CrawlingSession.objects.filter(domain=domain).order_by('-started_at')
    
    # Estadísticas del dominio
    stats = {
        'total_sessions': sessions.count(),
        'completed_sessions': sessions.filter(status='completed').count(),
        'total_urls': URLAnalysis.objects.filter(session__domain=domain).count(),
        'avg_score': URLAnalysis.objects.filter(
            session__domain=domain,
            accessibility_score__isnull=False
        ).aggregate(avg=Avg('accessibility_score'))['avg'] or 0
    }
    
    context = {
        'domain': domain,
        'sessions': sessions,
        'stats': stats,
    }
    
    return render(request, 'analysis/domain_detail.html', context)

@login_required
def analyze_single_url(request):
    """Analizar una URL individual."""
    if request.method == 'POST':
        url = request.POST.get('url')
        if url:
            analyzer = AccessibilityAnalyzer()
            analysis = analyzer.analyze_url(url)
            
            # Crear sesión temporal para mostrar resultados
            domain, created = Domain.objects.get_or_create(
                url=url,
                defaults={'name': f'Análisis temporal - {url}', 'created_by': request.user}
            )
            
            session = CrawlingSession.objects.create(
                domain=domain,
                started_by=request.user,
                status='completed',
                total_urls=1,
                processed_urls=1,
                completed_at=timezone.now()
            )
            
            if 'error' not in analysis:
                URLAnalysis.objects.create(
                    session=session,
                    **analysis
                )
                return redirect('analysis:site_results', session_id=session.id)
            else:
                messages.error(request, f'Error analizando URL: {analysis["error"]}')
    
    return render(request, 'analysis/analyze_single_url.html')

@login_required
def analyze_full_site(request):
    """Vista para analizar sitio completo."""
    domains = Domain.objects.filter(created_by=request.user, is_active=True)
    return render(request, 'analysis/analyze_full_site.html', {'domains': domains})

@csrf_exempt
@login_required
def start_full_site_analysis(request):
    """Iniciar análisis completo de sitio."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            domain_id = data.get('domain_id')
            max_pages = int(data.get('max_pages', 50))
            
            domain = get_object_or_404(Domain, id=domain_id, created_by=request.user)
            
            # Crear sesión de crawling
            session = CrawlingSession.objects.create(
                domain=domain,
                started_by=request.user,
                status='running'
            )
            
            # Iniciar crawling
            crawler = WebCrawler()
            results = crawler.crawl_site(domain.url, max_pages)
            
            # Guardar resultados
            for result in results:
                if 'error' not in result:
                    URLAnalysis.objects.create(
                        session=session,
                        **result
                    )
            
            # Actualizar sesión
            session.status = 'completed'
            session.total_urls = len(results)
            session.processed_urls = len([r for r in results if 'error' not in r])
            session.completed_at = timezone.now()
            session.save()
            
            print(f"✅ Crawling completado para {domain.url}")
            
            return JsonResponse({'success': True, 'session_id': session.id})
            
        except Exception as e:
            print(f"❌ Error en crawling: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def session_detail(request, session_id):
    """Detalle de una sesión de crawling."""
    session = get_object_or_404(CrawlingSession, id=session_id, started_by=request.user)
    url_analyses = URLAnalysis.objects.filter(session=session).order_by('-accessibility_score')
    
    # Estadísticas de la sesión
    stats = {
        'total_urls': url_analyses.count(),
        'successful_urls': url_analyses.filter(status_code=200).count(),
        'failed_urls': url_analyses.exclude(status_code=200).count(),
        'avg_score': url_analyses.filter(accessibility_score__isnull=False).aggregate(
            avg=Avg('accessibility_score'))['avg'] or 0,
        'avg_response_time': url_analyses.aggregate(avg=Avg('response_time'))['avg'] or 0,
    }
    
    context = {
        'session': session,
        'url_analyses': url_analyses,
        'stats': stats,
    }
    
    return render(request, 'analysis/session_detail.html', context)

@login_required
def site_results(request, session_id):
    """Resultados del análisis de sitio."""
    session = get_object_or_404(CrawlingSession, id=session_id, started_by=request.user)
    url_analyses = URLAnalysis.objects.filter(session=session)
    
    # Estadísticas detalladas
    total_analyses = url_analyses.count()
    successful_analyses = url_analyses.filter(status_code=200)
    
    stats = {
        'total_urls': total_analyses,
        'successful_urls': successful_analyses.count(),
        'failed_urls': total_analyses - successful_analyses.count(),
        'avg_accessibility_score': successful_analyses.aggregate(
            avg=Avg('accessibility_score'))['avg'] or 0,
        'high_score_urls': successful_analyses.filter(accessibility_score__gte=80).count(),
        'medium_score_urls': successful_analyses.filter(
            accessibility_score__gte=60, accessibility_score__lt=80).count(),
        'low_score_urls': successful_analyses.filter(accessibility_score__lt=60).count(),
        'avg_response_time': successful_analyses.aggregate(avg=Avg('response_time'))['avg'] or 0,
    }
    
    # URLs ordenadas por score
    top_urls = successful_analyses.filter(
        accessibility_score__isnull=False
    ).order_by('-accessibility_score')[:10]
    
    worst_urls = successful_analyses.filter(
        accessibility_score__isnull=False
    ).order_by('accessibility_score')[:10]
    
    context = {
        'session': session,
        'stats': stats,
        'top_urls': top_urls,
        'worst_urls': worst_urls,
        'all_analyses': url_analyses.order_by('-accessibility_score'),
    }
    
    return render(request, 'analysis/site_results.html', context)

@login_required
def url_analysis_detail(request, analysis_id):
    """Detalle del análisis de una URL específica."""
    analysis = get_object_or_404(URLAnalysis, id=analysis_id, session__started_by=request.user)
    
    context = {
        'analysis': analysis,
    }
    
    return render(request, 'analysis/url_analysis_detail.html', context)
