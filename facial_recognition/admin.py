from django.contrib import admin
from django.utils.html import format_html
from .models import FacialEnrollment, EnrollmentAttempt


@admin.register(FacialEnrollment)
class FacialEnrollmentAdmin(admin.ModelAdmin):
    """Admin interface for Facial Enrollment."""
    
    list_display = [
        'student_display', 'student_id_display', 'enrollment_date',
        'quality_badge', 'faces_detected', 'is_active', 'thumbnail_preview'
    ]
    list_filter = ['is_active', 'enrollment_date', 'embedding_quality']
    search_fields = [
        'student__user__first_name', 'student__user__last_name',
        'student__student_id', 'student__user__email'
    ]
    readonly_fields = [
        'enrollment_date', 'last_updated', 'embedding_display',
        'thumbnail_preview_large'
    ]
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Enrollment Data', {
            'fields': (
                'thumbnail', 'thumbnail_preview_large',
                'embedding_display', 'is_active'
            )
        }),
        ('Quality Metrics', {
            'fields': (
                'face_confidence', 'embedding_quality',
                'num_faces_detected'
            )
        }),
        ('Timestamps', {
            'fields': ('enrollment_date', 'last_updated'),
            'classes': ('collapse',)
        })
    )
    
    def student_display(self, obj):
        return obj.student.user.full_name
    student_display.short_description = 'Student Name'
    student_display.admin_order_field = 'student__user__last_name'
    
    def student_id_display(self, obj):
        return obj.student.student_id
    student_id_display.short_description = 'Student ID'
    student_id_display.admin_order_field = 'student__student_id'
    
    def quality_badge(self, obj):
        quality = obj.embedding_quality
        if quality >= 0.8:
            color = 'green'
            label = 'Excellent'
        elif quality >= 0.6:
            color = 'orange'
            label = 'Good'
        else:
            color = 'red'
            label = 'Poor'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1%} ({})</span>',
            color, quality, label
        )
    quality_badge.short_description = 'Quality'
    quality_badge.admin_order_field = 'embedding_quality'
    
    def faces_detected(self, obj):
        return obj.num_faces_detected
    faces_detected.short_description = 'Faces'
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />',
                obj.thumbnail.url
            )
        return '-'
    thumbnail_preview.short_description = 'Thumbnail'
    
    def thumbnail_preview_large(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="200" height="200" style="object-fit: cover; border-radius: 10px;" />',
                obj.thumbnail.url
            )
        return '-'
    thumbnail_preview_large.short_description = 'Thumbnail Preview'
    
    def embedding_display(self, obj):
        return format_html(
            '<code style="font-size: 11px;">128-D embedding stored (Binary field)</code>'
        )
    embedding_display.short_description = 'Embedding Data'


@admin.register(EnrollmentAttempt)
class EnrollmentAttemptAdmin(admin.ModelAdmin):
    """Admin interface for Enrollment Attempts."""
    
    list_display = [
        'student_display', 'created_at', 'status_badge',
        'frames_processed', 'faces_detected', 'processing_time_display'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'student__user__first_name', 'student__user__last_name',
        'student__student_id'
    ]
    readonly_fields = ['created_at', 'processing_time']
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Attempt Details', {
            'fields': (
                'status', 'frames_processed', 'faces_detected',
                'processing_time', 'error_message'
            )
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def student_display(self, obj):
        return obj.student.user.full_name
    student_display.short_description = 'Student'
    student_display.admin_order_field = 'student__user__last_name'
    
    def status_badge(self, obj):
        colors = {
            'SUCCESS': 'green',
            'FAILED': 'red',
            'PROCESSING': 'orange'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def processing_time_display(self, obj):
        if obj.processing_time:
            return f"{obj.processing_time:.2f}s"
        return '-'
    processing_time_display.short_description = 'Processing Time'
    processing_time_display.admin_order_field = 'processing_time'
