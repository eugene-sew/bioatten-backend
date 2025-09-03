from rest_framework import serializers
from .models import FacialEnrollment, EnrollmentAttempt
from students.models import Student


class FacialEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for facial enrollment data."""
    
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    embedding_base64 = serializers.SerializerMethodField()
    
    class Meta:
        model = FacialEnrollment
        fields = [
            'id', 'student', 'student_name', 'student_id',
            'thumbnail', 'face_confidence', 'embedding_quality',
            'num_faces_detected', 'enrollment_date', 'last_updated',
            'is_active', 'embedding_base64'
        ]
        read_only_fields = [
            'id', 'enrollment_date', 'last_updated', 'embedding_base64'
        ]
    
    def get_embedding_base64(self, obj):
        """Return embedding as base64 string if requested."""
        request = self.context.get('request')
        if request and request.query_params.get('include_embedding', 'false').lower() == 'true':
            return obj.get_embedding_base64()
        return None


class EnrollmentAttemptSerializer(serializers.ModelSerializer):
    """Serializer for enrollment attempts."""
    
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    
    class Meta:
        model = EnrollmentAttempt
        fields = [
            'id', 'student', 'student_name', 'status',
            'frames_processed', 'faces_detected', 'error_message',
            'processing_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FacialEnrollmentCreateSerializer(serializers.Serializer):
    """Serializer for creating facial enrollment from video/images."""
    
    media = serializers.FileField(
        help_text="Video file or ZIP archive containing burst images"
    )
    
    def validate_media(self, value):
        """Validate the uploaded media file."""
        allowed_video_types = ['video/mp4', 'video/avi', 'video/mov', 'video/quicktime']
        allowed_image_archive_types = ['application/zip', 'application/x-zip-compressed']
        
        if value.content_type in allowed_video_types:
            # Validate video file size (max 50MB)
            if value.size > 50 * 1024 * 1024:
                raise serializers.ValidationError("Video file size cannot exceed 50MB")
        elif value.content_type in allowed_image_archive_types:
            # Validate archive file size (max 100MB)
            if value.size > 100 * 1024 * 1024:
                raise serializers.ValidationError("Archive file size cannot exceed 100MB")
        else:
            raise serializers.ValidationError(
                f"Unsupported file type: {value.content_type}. "
                "Please upload a video (MP4, AVI, MOV) or ZIP archive containing images."
            )
        
        return value


class EnrollmentResponseSerializer(serializers.Serializer):
    """Serializer for enrollment response."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    enrollment = FacialEnrollmentSerializer(required=False)
    quality_metrics = serializers.DictField(required=False)
    errors = serializers.ListField(child=serializers.CharField(), required=False)
