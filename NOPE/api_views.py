from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from .models import Article, Newsletter, Publisher, CustomUser
from .serializers import (
    ArticleSerializer, NewsletterSerializer, 
    PublisherSerializer, UserSerializer
)
from .permissions import (
    IsJournalistOrReadOnly, IsEditorOrJournalistOrReadOnly,
    IsEditorOnly, IsOwnerOrReadOnly
)


class ArticleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for articles.
    - GET /api/articles/ - List all approved public articles (or all approved if authenticated)
    - GET /api/articles/subscribed/ - Articles from subscribed publishers/journalists
    - GET /api/articles/<id>/ - Retrieve single article
    - POST /api/articles/ - Create article (journalists only)
    - PUT/PATCH /api/articles/<id>/ - Update article (editors/journalists)
    - DELETE /api/articles/<id>/ - Delete article (editors/journalists)
    """
    serializer_class = ArticleSerializer
    permission_classes = [IsEditorOrJournalistOrReadOnly]
    
    def get_queryset(self):
        """
        Unauthenticated: Only public, approved articles
        Readers: All approved articles (public + private)
        Journalists: Their own articles + all approved ones
        Editors: All articles
        """
        user = self.request.user
        
        # Unauthenticated users can only see public, approved articles
        if not user.is_authenticated:
            return Article.objects.filter(approved=True, is_public=True).select_related('author', 'publisher', 'approved_by')
        
        if user.role == 'editor':
            return Article.objects.all().select_related('author', 'publisher', 'approved_by')
        elif user.role == 'journalist':
            return Article.objects.filter(
                Q(approved=True) | Q(author=user)
            ).select_related('author', 'publisher', 'approved_by')
        else:  # reader
            return Article.objects.filter(approved=True).select_related('author', 'publisher')
    
    def perform_create(self, serializer):
        """Automatically set the author to current user for journalists."""
        serializer.save(author=self.request.user)
    
    @action(detail=False, methods=['get'])
    def subscribed(self, request):
        """
        Return articles from publishers/journalists that the reader is subscribed to.
        Only available for readers.
        """
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication required.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if request.user.role != 'reader':
            return Response(
                {'detail': 'This endpoint is only for readers.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get subscribed publishers and journalists
        subscribed_publishers = request.user.subscribed_publishers.all()
        subscribed_journalists = request.user.subscribed_journalists.all()
        
        # Filter approved articles from subscriptions
        articles = Article.objects.filter(
            approved=True
        ).filter(
            Q(publisher__in=subscribed_publishers) | Q(author__in=subscribed_journalists)
        ).select_related('author', 'publisher').distinct()
        
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEditorOnly])
    def approve(self, request, pk=None):
        """
        Approve an article (editors only).
        This triggers the signal that sends emails and posts to X.
        """
        article = self.get_object()
        
        if article.approved:
            return Response(
                {'detail': 'Article is already approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        article.approved = True
        article.approved_by = request.user
        article.approved_at = timezone.now()
        article.save()
        
        serializer = self.get_serializer(article)
        return Response({
            'detail': 'Article approved successfully. Subscribers have been notified.',
            'article': serializer.data
        })


class NewsletterViewSet(viewsets.ModelViewSet):
    """
    API endpoint for newsletters.
    Journalists and editors can create/edit newsletters.
    Readers can only view published newsletters.
    """
    serializer_class = NewsletterSerializer
    permission_classes = [IsAuthenticated, IsEditorOrJournalistOrReadOnly]
    
    def get_queryset(self):
        """
        Readers see only published newsletters.
        Journalists see their own + published.
        Editors see all.
        """
        user = self.request.user
        
        if user.role == 'editor':
            return Newsletter.objects.all().select_related('author').prefetch_related('articles')
        elif user.role == 'journalist':
            return Newsletter.objects.filter(
                Q(published=True) | Q(author=user)
            ).select_related('author').prefetch_related('articles')
        else:  # reader
            return Newsletter.objects.filter(published=True).select_related('author').prefetch_related('articles')
    
    def perform_create(self, serializer):
        """Automatically set the author to current user."""
        serializer.save(author=self.request.user)


class PublisherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for publishers (read-only).
    Lists all publishers and their details.
    """
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    permission_classes = [IsAuthenticated]


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for users (read-only).
    Users can view their own profile and other users' basic info.
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def subscribe_publisher(self, request, pk=None):
        """Subscribe to a publisher (readers only)."""
        if request.user.role != 'reader':
            return Response(
                {'detail': 'Only readers can subscribe to publishers.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            publisher = Publisher.objects.get(pk=request.data.get('publisher_id'))
            request.user.subscribed_publishers.add(publisher)
            return Response({'detail': f'Subscribed to {publisher.name}'})
        except Publisher.DoesNotExist:
            return Response(
                {'detail': 'Publisher not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def subscribe_journalist(self, request, pk=None):
        """Subscribe to a journalist (readers only)."""
        if request.user.role != 'reader':
            return Response(
                {'detail': 'Only readers can subscribe to journalists.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            journalist = CustomUser.objects.get(pk=request.data.get('journalist_id'), role='journalist')
            request.user.subscribed_journalists.add(journalist)
            return Response({'detail': f'Subscribed to {journalist.username}'})
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'Journalist not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
