from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Publisher, Article, Newsletter


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin interface for CustomUser model."""
    list_display = ['username', 'email', 'role', 'publisher', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Publisher Info', {
            'fields': ('role', 'publisher', 'bio', 'profile_picture')
        }),
        ('Subscriptions (Reader only)', {
            'fields': ('subscribed_publishers', 'subscribed_journalists'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['subscribed_publishers', 'subscribed_journalists', 'groups', 'user_permissions']


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    """Admin interface for Publisher model."""
    list_display = ['name', 'website', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Admin interface for Article model."""
    list_display = ['title', 'author', 'publisher', 'approved', 'created_at']
    list_filter = ['approved', 'created_at', 'publisher']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'summary', 'content', 'tags')
        }),
        ('Author & Publisher', {
            'fields': ('author', 'publisher')
        }),
        ('Approval Status', {
            'fields': ('approved', 'approved_by', 'approved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """Admin interface for Newsletter model."""
    list_display = ['title', 'author', 'published', 'created_at']
    list_filter = ['published', 'created_at']
    search_fields = ['title', 'description', 'author__username']
    filter_horizontal = ['articles']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

