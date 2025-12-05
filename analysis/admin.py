from django.contrib import admin
from .models import Domain, CrawlingSession, URLAnalysis

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'created_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'created_by')
    search_fields = ('name', 'url')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CrawlingSession)
class CrawlingSessionAdmin(admin.ModelAdmin):
    list_display = ('domain', 'status', 'started_by', 'total_urls', 'processed_urls', 'started_at', 'completed_at')
    list_filter = ('status', 'started_at', 'domain')
    search_fields = ('domain__name', 'started_by__username')
    readonly_fields = ('started_at', 'completed_at')

@admin.register(URLAnalysis)
class URLAnalysisAdmin(admin.ModelAdmin):
    list_display = ('url', 'session', 'status_code', 'accessibility_score', 'accessibility_grade', 'analyzed_at')
    list_filter = ('status_code', 'analyzed_at', 'session__domain')
    search_fields = ('url', 'title')
    readonly_fields = ('analyzed_at',)
    
    def accessibility_grade(self, obj):
        return obj.accessibility_grade
    accessibility_grade.short_description = 'Grado'
