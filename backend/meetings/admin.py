from django.contrib import admin
from .models import Meeting, TranscriptSegment, ChatMessage

admin.site.register(Meeting)
admin.site.register(TranscriptSegment)
admin.site.register(ChatMessage)