from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),

    # Core pages
    path('', views.landing, name='landing'),
    path('home/', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Articles
    path('articles/<int:article_id>/', views.article_detail, name='article_detail'),
    path('articles/<int:article_id>/like/', views.like_article, name='like_article'),
    path('articles/create/', views.create_article, name='create_article'),
    path('articles/my/', views.my_articles, name='my_articles'),

    # Editor workflow
    path('editor/pending/', views.pending_articles, name='pending_articles'),
    path('editor/approve/<int:article_id>/', views.approve_article, name='approve_article'),
    path('editor/reject/<int:article_id>/', views.reject_article, name='reject_article'),

    # Newsletters
    path('newsletters/', views.newsletter_list, name='newsletter_list'),
    path('newsletters/create/', views.create_newsletter, name='create_newsletter'),
    path('newsletters/<int:newsletter_id>/', views.newsletter_detail, name='newsletter_detail'),
    path('newsletters/<int:newsletter_id>/edit/', views.edit_newsletter, name='edit_newsletter'),
    path('newsletters/<int:newsletter_id>/delete/', views.delete_newsletter, name='delete_newsletter'),

    # Article editing and deleting
    path('articles/<int:article_id>/edit/', views.edit_article, name='edit_article'),
    path('articles/<int:article_id>/delete/', views.delete_article, name='delete_article'),

    # Publishers
    path('publishers/', views.publisher_list, name='publisher_list'),
    path('publishers/create/', views.create_publisher, name='create_publisher'),

    # Subscriptions
    path('subscriptions/', views.manage_subscriptions, name='manage_subscriptions'),
]
