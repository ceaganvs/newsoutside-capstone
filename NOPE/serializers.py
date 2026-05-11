from rest_framework import serializers
from .models import Article, Newsletter, Publisher, CustomUser


class PublisherSerializer(serializers.ModelSerializer):
    """Serializer for Publisher model."""
    subscriber_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Publisher
        fields = ['id', 'name', 'description', 'website', 'created_at', 'subscriber_count']
        read_only_fields = ['created_at']
    
    def get_subscriber_count(self, obj):
        return obj.subscribers.count()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information for nested serialization."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'role']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class ArticleSerializer(serializers.ModelSerializer):
    """Serializer for Article model."""
    author_info = UserBasicSerializer(source='author', read_only=True)
    publisher_info = PublisherSerializer(source='publisher', read_only=True)
    approved_by_info = UserBasicSerializer(source='approved_by', read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'summary', 'content', 'tags',
            'author', 'author_info', 
            'publisher', 'publisher_info',
            'approved', 'approved_by', 'approved_by_info', 'approved_at',
            'is_public', 'view_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'approved_by', 'approved_at', 'created_at', 'updated_at', 'view_count']
    
    def validate(self, data):
        """Ensure journalists can only create articles for themselves."""
        request = self.context.get('request')
        if request and request.method == 'POST':
            if request.user.role == 'journalist':
                data['author'] = request.user
        return data


class NewsletterSerializer(serializers.ModelSerializer):
    """Serializer for Newsletter model."""
    author_info = UserBasicSerializer(source='author', read_only=True)
    articles = ArticleSerializer(many=True, read_only=True)
    article_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        queryset=Article.objects.all(),
        source='articles'
    )
    article_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Newsletter
        fields = [
            'id', 'title', 'description',
            'author', 'author_info',
            'articles', 'article_ids', 'article_count',
            'published', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'author']
    
    def get_article_count(self, obj):
        return obj.articles.count()
    
    def validate(self, data):
        """Ensure journalists/editors can only create newsletters for themselves."""
        request = self.context.get('request')
        if request and request.method == 'POST':
            if request.user.role in ['journalist', 'editor']:
                data['author'] = request.user
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for CustomUser model."""
    subscribed_publishers_info = PublisherSerializer(
        source='subscribed_publishers', 
        many=True, 
        read_only=True
    )
    subscribed_journalists_info = UserBasicSerializer(
        source='subscribed_journalists',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'bio', 'profile_picture',
            'publisher',
            'subscribed_publishers', 'subscribed_publishers_info',
            'subscribed_journalists', 'subscribed_journalists_info',
        ]
        read_only_fields = ['role']
        extra_kwargs = {
            'password': {'write_only': True}
        }
