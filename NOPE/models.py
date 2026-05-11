"""
NOPE models module.

Defines the database models for the News Outside Publishing Engine:
CustomUser, Publisher, Article, and Newsletter.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError
from django.utils import timezone


class Publisher(models.Model):
    """Represents a publishing organization with editors and journalists."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class CustomUser(AbstractUser):
    """Extended user model with role-based functionality."""
    
    ROLE_CHOICES = [
        ('reader', 'Reader'),
        ('editor', 'Editor'),
        ('journalist', 'Journalist'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='reader')
    
    # Reader-specific fields
    subscribed_publishers = models.ManyToManyField(
        Publisher,
        related_name='subscribers',
        blank=True
    )
    subscribed_journalists = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='readers_following',
        blank=True,
        limit_choices_to={'role': 'journalist'}
    )
    
    # Journalist/Editor association with publisher
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members'
    )
    
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # If user is journalist or editor, clear reader subscriptions
        if self.role in ['journalist', 'editor']:
            is_new = self.pk is None
            super().save(*args, **kwargs)
            if not is_new:
                self.subscribed_publishers.clear()
                self.subscribed_journalists.clear()
        else:
            super().save(*args, **kwargs)
        
        # Automatically assign to appropriate group
        self._assign_to_group()
    
    def _assign_to_group(self):
        """Assign user to correct group based on role."""
        # Remove from all role groups first
        self.groups.clear()
        
        group_name = self.role.capitalize()
        group, created = Group.objects.get_or_create(name=group_name)
        self.groups.add(group)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        ordering = ['username']


class Article(models.Model):
    """News article that can be created by journalists or publishers."""
    title = models.CharField(max_length=300)
    content = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='authored_articles',
        limit_choices_to={'role': 'journalist'}
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name='published_articles',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_articles',
        limit_choices_to={'role': 'editor'}
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Article metadata
    summary = models.TextField(blank=True, help_text="Brief summary of the article")
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    view_count = models.IntegerField(default=0)
    liked_by = models.ManyToManyField(CustomUser, related_name='liked_articles', blank=True)
    read_by = models.ManyToManyField(CustomUser, related_name='read_articles', blank=True)
    
    # Privacy settings
    is_public = models.BooleanField(
        default=True, 
        help_text="If True, article can be viewed by unauthenticated users. If False, requires login."
    )
    
    def clean(self):
        """Validate that article has either independent author or publisher."""
        super().clean()
        if not self.author and not self.publisher:
            raise ValidationError("Article must be associated with either a journalist or publisher.")
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('approve_article', 'Can approve articles'),
        ]


class Newsletter(models.Model):
    """Curated collection of articles created by journalists."""
    title = models.CharField(max_length=300)
    description = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='created_newsletters',
        limit_choices_to={'role__in': ['journalist', 'editor']}
    )
    articles = models.ManyToManyField(Article, related_name='newsletters', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
