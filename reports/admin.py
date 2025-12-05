from django.contrib import admin
from .models import Report, ReportSection

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'session', 'generated_by', 'generated_at')
    list_filter = ('report_type', 'generated_at')
    search_fields = ('title', 'session__domain__name')
    readonly_fields = ('generated_at',)

@admin.register(ReportSection)
class ReportSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'report', 'order')
    list_filter = ('report__report_type',)
    ordering = ['report', 'order']
