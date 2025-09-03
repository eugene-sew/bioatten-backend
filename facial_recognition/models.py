from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from students.models import Student
from common.models import BaseModel
import pickle
import base64


class FacialEnrollment(BaseModel):
    """Model to store facial embeddings for enrolled students."""
    
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='facial_enrollment'
    )
    
    # Store the 128-D embedding as a binary field
    embedding = models.BinaryField(help_text="128-D facial embedding")
    
    # Store the thumbnail image
    thumbnail = models.ImageField(
        upload_to='facial_thumbnails/',
        help_text="Thumbnail of the enrolled face"
    )
    
    # Quality metrics
    face_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Confidence score of face detection"
    )
    
    embedding_quality = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Quality score of the facial embedding"
    )
    
    num_faces_detected = models.IntegerField(
        default=1,
        help_text="Number of faces detected in the enrollment process"
    )
    
    # Metadata
    enrollment_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'facial_enrollments'
        verbose_name = 'Facial Enrollment'
        verbose_name_plural = 'Facial Enrollments'
        ordering = ['-enrollment_date']
    
    def __str__(self):
        return f"Facial Enrollment for {self.student.user.full_name}"
    
    def set_embedding(self, embedding_array):
        """Serialize and store the numpy array embedding."""
        self.embedding = pickle.dumps(embedding_array)
    
    def get_embedding(self):
        """Deserialize and return the numpy array embedding."""
        return pickle.loads(self.embedding)
    
    def get_embedding_base64(self):
        """Return the embedding as a base64 encoded string."""
        return base64.b64encode(self.embedding).decode('utf-8')


class EnrollmentAttempt(BaseModel):
    """Model to track enrollment attempts and their results."""
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollment_attempts'
    )
    
    # Status of the attempt
    STATUS_CHOICES = [
        ('SUCCESS', 'Successful'),
        ('FAILED', 'Failed'),
        ('PROCESSING', 'Processing'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Details about the attempt
    frames_processed = models.IntegerField(default=0)
    faces_detected = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    # Processing metadata
    processing_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Time taken to process in seconds"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'enrollment_attempts'
        verbose_name = 'Enrollment Attempt'
        verbose_name_plural = 'Enrollment Attempts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Enrollment attempt for {self.student.user.full_name} - {self.status}"
