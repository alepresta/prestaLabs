from django.db import models
from django.contrib.auth import get_user_model
from analysis.models import CrawlingSession

User = get_user_model()

class Report(models.Model):
    REPORT_TYPES = [
        ('accessibility', 'Reporte de Accesibilidad'),
        ('technical', 'Reporte Técnico'),
        ('seo', 'Reporte SEO'),
        ('complete', 'Reporte Completo'),
    ]
    
    session = models.ForeignKey(CrawlingSession, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    file_path = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_report_type_display()}"

class ReportSection(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.report.title} - {self.title}"
