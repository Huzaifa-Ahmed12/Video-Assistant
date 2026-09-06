from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Meeting, ChatMessage
from .serializers import MeetingListSerializer, TranscriptSerializer, ChatMessageSerializer


@api_view(['GET', 'POST'])
def meeting_list_create(request):
    if request.method == 'GET':
        meetings = Meeting.objects.all().order_by('-created_at')
        return Response(MeetingListSerializer(meetings, many=True).data)

    if request.method == 'POST':
        title = request.data.get('title', '')
        url = request.data.get('url')
        file = request.FILES.get('file')
        language = request.data.get('language', 'auto')

        meeting = Meeting.objects.create(
            title=title,
            source_url=url,
            source_file=file,
            language=language,
            status='pending',
        )

        # TODO: trigger your transcription pipeline here (sync for now, Celery later)

        return Response(MeetingListSerializer(meeting).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE'])
def meeting_detail(request, pk):
    try:
        meeting = Meeting.objects.get(pk=pk)
    except Meeting.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        meeting.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(MeetingListSerializer(meeting).data)


@api_view(['GET'])
def get_transcript(request, pk):
    try:
        meeting = Meeting.objects.get(pk=pk)
    except Meeting.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response(TranscriptSerializer(meeting).data)


@api_view(['GET', 'POST'])
def chat(request, pk):
    try:
        meeting = Meeting.objects.get(pk=pk)
    except Meeting.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        messages = meeting.messages.all()
        return Response(ChatMessageSerializer(messages, many=True).data)

    if request.method == 'POST':
        user_text = request.data.get('message', '')
        ChatMessage.objects.create(meeting=meeting, role='user', content=user_text)

        # TODO: replace with real RAG pipeline call (pgvector retrieval + LLM)
        reply_text = "Backend pipeline not connected yet."

        reply = ChatMessage.objects.create(
            meeting=meeting, role='assistant', content=reply_text, sources=[]
        )
        return Response(ChatMessageSerializer(reply).data, status=status.HTTP_201_CREATED)
