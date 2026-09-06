from django.db import models

class Meeting(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]
    title = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True, null=True)
    source_file = models.FileField(upload_to='uploads/', blank=True, null=True)
    language = models.CharField(max_length=10, default='auto')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Meeting {self.id}"


class TranscriptSegment(models.Model):
    meeting = models.ForeignKey(Meeting, related_name='segments', on_delete=models.CASCADE)
    speaker = models.CharField(max_length=50, blank=True, null=True)
    start = models.FloatField(blank=True, null=True)
    end = models.FloatField(blank=True, null=True)
    text = models.TextField()

    class Meta:
        ordering = ['start']


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    meeting = models.ForeignKey(Meeting, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']