from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class CrawlingSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'En progreso'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='sessions')
    started_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_urls = models.IntegerField(default=0)
    processed_urls = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.domain.name} - {self.get_status_display()}"
    
    @property
    def duration(self):
        if self.completed_at:
            return self.completed_at - self.started_at
        return timezone.now() - self.started_at

class URLAnalysis(models.Model):
    session = models.ForeignKey(CrawlingSession, on_delete=models.CASCADE, related_name='url_analyses')
    url = models.URLField()
    title = models.CharField(max_length=500, blank=True)
    status_code = models.IntegerField()
    response_time = models.FloatField(help_text="Response time in seconds")
    content_size = models.IntegerField(help_text="Content size in bytes")
    
    # Accessibility metrics
    accessibility_score = models.FloatField(null=True, blank=True)
    wcag_violations = models.JSONField(default=dict)
    color_contrast_issues = models.IntegerField(default=0)
    alt_text_missing = models.IntegerField(default=0)
    heading_structure_issues = models.IntegerField(default=0)
    
    # Technical metrics
    load_time = models.FloatField(null=True, blank=True)
    page_size = models.IntegerField(null=True, blank=True)
    
    # SEO metrics
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-analyzed_at']
        unique_together = ['session', 'url']
    
    def __str__(self):
        return f"{self.url} - {self.status_code}"
    
    @property
    def is_accessible(self):
        return self.accessibility_score and self.accessibility_score >= 80
    
    @property
    def accessibility_grade(self):
        if not self.accessibility_score:
            return 'N/A'
        if self.accessibility_score >= 90:
            return 'A'
        elif self.accessibility_score >= 80:
            return 'B'
        elif self.accessibility_score >= 70:
            return 'C'
        elif self.accessibility_score >= 60:
            return 'D'
        else:
            return 'F'
