from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('domains/', views.domain_list, name='domain_list'),
    path('domains/add/', views.add_domain, name='add_domain'),
    path('domains/<int:domain_id>/', views.domain_detail, name='domain_detail'),
    path('analyze/single-url/', views.analyze_single_url, name='analyze_single_url'),
    path('analyze/full-site/', views.analyze_full_site, name='analyze_full_site'),
    path('analyze/full-site/start/', views.start_full_site_analysis, name='start_full_site_analysis'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('results/site/<int:session_id>/', views.site_results, name='site_results'),
    path('results/url/<int:analysis_id>/', views.url_analysis_detail, name='url_analysis_detail'),
]
