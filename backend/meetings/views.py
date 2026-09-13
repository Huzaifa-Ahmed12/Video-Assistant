import traceback
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Meeting, TranscriptSegment, ChatMessage, Chunk
from .serializers import MeetingListSerializer, TranscriptSerializer, ChatMessageSerializer
from utils.main import run_pipeline
from core.rag_engine import build_rag_chain, load_rag_chain, get_question
from core.vector_store import get_embeddings


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
            status='processing',
        )

        try:
            # Determine source input
            if meeting.source_file:
                source_input = meeting.source_file.path
            elif meeting.source_url:
                source_input = meeting.source_url
            else:
                meeting.status = 'failed'
                meeting.save()
                return Response({'error': 'No audio file or URL provided'}, status=status.HTTP_400_BAD_REQUEST)

            # Run full AI pipeline (transcription, translation, diarization)
            pipeline_result = run_pipeline(source_input)

            # Update meeting title if auto-generated
            if not meeting.title and pipeline_result.get('title'):
                meeting.title = pipeline_result['title']

            # Extract segments
            translated_blocks = pipeline_result.get('translated_blocks') or []
            diarized_blocks = pipeline_result.get('diarized_blocks') or []
            english_transcript = pipeline_result.get('english_transcript') or ""

            segments_to_create = []
            if translated_blocks:
                for idx, block in enumerate(translated_blocks):
                    speaker = block.get('speaker', 'Speaker')
                    text = block.get('english_text') or block.get('text', '')
                    if text.strip():
                        segments_to_create.append(
                            TranscriptSegment(
                                meeting=meeting,
                                speaker=speaker,
                                start=float(idx * 5),
                                end=float((idx + 1) * 5),
                                text=text.strip()
                            )
                        )
            elif diarized_blocks:
                for idx, block in enumerate(diarized_blocks):
                    speaker = block.get('speaker', 'Speaker')
                    text = block.get('text', '')
                    if text.strip():
                        segments_to_create.append(
                            TranscriptSegment(
                                meeting=meeting,
                                speaker=speaker,
                                start=float(idx * 5),
                                end=float((idx + 1) * 5),
                                text=text.strip()
                            )
                        )
            elif english_transcript.strip():
                paragraphs = [p.strip() for p in english_transcript.split('\n\n') if p.strip()]
                for idx, p in enumerate(paragraphs):
                    segments_to_create.append(
                        TranscriptSegment(
                            meeting=meeting,
                            speaker='Speaker',
                            start=float(idx * 5),
                            end=float((idx + 1) * 5),
                            text=p
                        )
                    )

            if segments_to_create:
                TranscriptSegment.objects.bulk_create(segments_to_create)

                # Populate Chunk records in PostgreSQL with pgvector embeddings
                try:
                    embeddings_model = get_embeddings()
                    chunks_to_create = []
                    for seg in segments_to_create:
                        vector = embeddings_model.embed_query(seg.text)
                        chunks_to_create.append(
                            Chunk(
                                meeting=meeting,
                                text=seg.text,
                                speaker=seg.speaker,
                                start_time=seg.start,
                                end_time=seg.end,
                                embedding=vector
                            )
                        )
                    if chunks_to_create:
                        Chunk.objects.bulk_create(chunks_to_create)
                except Exception as chunk_err:
                    print(f"[!] Warning: Could not create PostgreSQL pgvector chunks: {chunk_err}")

            # Build Chroma Vector DB collection for this specific meeting
            collection_name = f"meeting_{meeting.id}"
            insight_text = "\n\n".join(seg.text for seg in segments_to_create) if segments_to_create else english_transcript
            if insight_text.strip():
                build_rag_chain(insight_text, collection_name=collection_name)

            meeting.status = 'done'
            meeting.save()

        except Exception as e:
            print(f"[!] Error processing meeting {meeting.id}: {e}")
            traceback.print_exc()
            meeting.status = 'failed'
            meeting.save()

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
        if not user_text:
            return Response({'error': 'Message text is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Save user message
        ChatMessage.objects.create(meeting=meeting, role='user', content=user_text)

        collection_name = f"meeting_{meeting.id}"
        reply_text = ""

        try:
            # Query the RAG chain for this specific meeting
            rag_chain = load_rag_chain(collection_name=collection_name)
            reply_text = get_question(rag_chain, user_text)
        except Exception as e:
            print(f"[!] Error using load_rag_chain for meeting {meeting.id}: {e}")
            # Fallback: build vector store dynamically if segments exist
            segments = meeting.segments.all()
            if segments.exists():
                full_text = "\n\n".join(f"{s.speaker or 'Speaker'}: {s.text}" for s in segments)
                rag_chain = build_rag_chain(full_text, collection_name=collection_name)
                reply_text = get_question(rag_chain, user_text)
            else:
                reply_text = "I could not find any transcript content available for this meeting."

        reply = ChatMessage.objects.create(
            meeting=meeting, role='assistant', content=reply_text, sources=[]
        )
        return Response(ChatMessageSerializer(reply).data, status=status.HTTP_201_CREATED)

