"""Views for the News Outside application.

Handles web-facing pages for authentication, article management,
publisher administration, newsletter browsing, and reader subscriptions.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import models
from .models import Article, Newsletter, Publisher, CustomUser


def register(request):
    """Display and process the user registration form."""
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role', 'reader')

        if password != password2:
            messages.error(request, 'Passwords do not match.')
        elif CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        else:
            CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('user_login')

    return render(request, 'NOPE/register.html', {'title': 'Register'})


def user_login(request):
    """Display and process the login form."""
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next', 'landing')
            return redirect(next_url)

        messages.error(request, 'Invalid username or password.')

    return render(request, 'NOPE/login.html', {'title': 'Login'})


@login_required
def user_logout(request):
    """Log out the current user and redirect to the landing page."""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('landing')


def is_editor(user):
    """Return True if the user is authenticated and has the editor role."""
    return user.is_authenticated and user.role == 'editor'


def is_journalist(user):
    """Return True if the user is authenticated and has the journalist role."""
    return user.is_authenticated and user.role == 'journalist'


def is_editor_or_journalist(user):
    """Return True if the user is authenticated and has the editor or journalist role."""
    return user.is_authenticated and user.role in ['editor', 'journalist']


def landing(request):
    """Display the public landing page with the latest approved articles."""
    if request.user.is_authenticated:
        articles = Article.objects.filter(approved=True).select_related('author', 'publisher')
    else:
        articles = Article.objects.filter(approved=True, is_public=True).select_related('author', 'publisher')

    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'NOPE/landing.html', {'page_obj': page_obj, 'title': 'Latest News'})


@login_required
def home(request):
    """Redirect authenticated users to their dashboard."""
    return redirect('dashboard')


@login_required
def dashboard(request):
    """Display a role-specific dashboard for journalists, editors, and readers."""
    user = request.user

    if user.role == 'journalist':
        articles = Article.objects.filter(author=user).annotate(
            likes_count=models.Count('liked_by')
        ).order_by('-created_at')
        context = {
            'articles': articles,
            'title': 'My Dashboard',
            'total_articles': articles.count(),
            'approved_articles': articles.filter(approved=True).count(),
            'pending_articles': articles.filter(approved=False).count(),
            'total_views': sum(a.view_count for a in articles),
            'total_likes': sum(a.likes_count for a in articles),
        }
        return render(request, 'NOPE/dashboard_journalist.html', context)

    elif user.role == 'editor':
        reviewed = Article.objects.filter(approved_by=user).order_by('-approved_at')
        pending = Article.objects.filter(approved=False).order_by('-created_at')
        context = {
            'reviewed_articles': reviewed,
            'pending_articles': pending,
            'title': 'Editor Dashboard',
            'total_reviewed': reviewed.count(),
            'total_pending': pending.count(),
        }
        return render(request, 'NOPE/dashboard_editor.html', context)

    else:  # reader
        liked = user.liked_articles.filter(approved=True).order_by('-created_at')
        read = user.read_articles.filter(approved=True).order_by('-created_at')[:20]
        context = {
            'liked_articles': liked,
            'read_articles': read,
            'title': 'My Dashboard',
            'total_liked': liked.count(),
            'total_read': user.read_articles.count(),
        }
        return render(request, 'NOPE/dashboard_reader.html', context)


@login_required
@user_passes_test(is_editor)
def pending_articles(request):
    """List all unapproved articles awaiting editor review."""
    articles = Article.objects.filter(approved=False).select_related(
        'author', 'publisher'
    ).order_by('-created_at')

    paginator = Paginator(articles, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'NOPE/pending_articles.html', {
        'page_obj': page_obj,
        'title': 'Pending Articles for Review'
    })


@login_required
@user_passes_test(is_editor)
def approve_article(request, article_id):
    """Approve a pending article and notify subscribers."""
    article = get_object_or_404(Article, id=article_id)

    if request.method == 'POST':
        article.approved = True
        article.approved_by = request.user
        article.approved_at = timezone.now()
        article.save()

        messages.success(request, f'Article "{article.title}" approved. Subscribers have been notified.')
        return redirect('pending_articles')

    return render(request, 'NOPE/approve_article.html', {
        'article': article,
        'title': f'Approve: {article.title}'
    })


@login_required
@user_passes_test(is_editor)
def reject_article(request, article_id):
    """Delete a pending article that does not meet editorial standards."""
    article = get_object_or_404(Article, id=article_id)

    if request.method == 'POST':
        title = article.title
        article.delete()
        messages.warning(request, f'Article "{title}" has been rejected and removed.')
        return redirect('pending_articles')

    return render(request, 'NOPE/reject_article.html', {
        'article': article,
        'title': f'Reject: {article.title}'
    })


def article_detail(request, article_id):
    """Display a single article and record the view. Enforces public/private visibility rules."""
    if not request.user.is_authenticated:
        article = get_object_or_404(Article, id=article_id, approved=True, is_public=True)
    elif request.user.role == 'reader':
        article = get_object_or_404(Article, id=article_id, approved=True)
    else:
        article = get_object_or_404(Article, id=article_id)

    article.view_count += 1
    article.save(update_fields=['view_count'])

    if request.user.is_authenticated:
        article.read_by.add(request.user)

    return render(request, 'NOPE/article_detail.html', {
        'article': article,
        'title': article.title,
        'user_liked': article.liked_by.filter(id=request.user.id).exists() if request.user.is_authenticated else False
    })


@login_required
def like_article(request, article_id):
    """Toggle a like on an article for the current user."""
    article = get_object_or_404(Article, id=article_id)

    if article.liked_by.filter(id=request.user.id).exists():
        article.liked_by.remove(request.user)
        messages.success(request, 'Removed from your likes.')
    else:
        article.liked_by.add(request.user)
        messages.success(request, 'Added to your likes.')

    return redirect('article_detail', article_id=article_id)


@login_required
@user_passes_test(is_journalist)
def create_article(request):
    """Display the article creation form and handle submission."""
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        summary = request.POST.get('summary', '')
        tags = request.POST.get('tags', '')
        publisher_id = request.POST.get('publisher')
        is_public = request.POST.get('is_public') == 'on'

        publisher = None
        if publisher_id:
            publisher = get_object_or_404(Publisher, id=publisher_id)

        article = Article.objects.create(
            title=title,
            content=content,
            summary=summary,
            tags=tags,
            author=request.user,
            publisher=publisher,
            is_public=is_public,
            approved=False,
        )

        if publisher:
            messages.success(request, f'Article "{article.title}" submitted to {publisher.name} for editor review.')
        else:
            messages.success(request, f'Article "{article.title}" submitted for editor review.')

        return redirect('my_articles')

    publishers = Publisher.objects.all()
    return render(request, 'NOPE/create_article.html', {
        'publishers': publishers,
        'title': 'Write New Article'
    })


@login_required
@user_passes_test(is_journalist)
def my_articles(request):
    """List all articles written by the currently logged-in journalist."""
    articles = Article.objects.filter(author=request.user).order_by('-created_at')
    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'NOPE/my_articles.html', {'page_obj': page_obj, 'title': 'My Articles'})


@login_required
@user_passes_test(is_editor_or_journalist)
def create_newsletter(request):
    """Allow journalists and editors to create a new newsletter."""
    approved_articles = Article.objects.filter(approved=True).order_by('-created_at')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        article_ids = request.POST.getlist('articles')
        published = request.POST.get('published') == 'on'

        if not title:
            messages.error(request, 'Title is required.')
        else:
            newsletter = Newsletter.objects.create(
                title=title,
                description=description,
                author=request.user,
                published=published,
            )
            if article_ids:
                newsletter.articles.set(Article.objects.filter(id__in=article_ids))
            messages.success(request, f'Newsletter "{newsletter.title}" created successfully.')
            return redirect('newsletter_list')

    return render(request, 'NOPE/create_newsletter.html', {
        'approved_articles': approved_articles,
        'title': 'Create Newsletter',
    })


@login_required
@user_passes_test(is_editor_or_journalist)
def edit_article(request, article_id):
    """Allow editors to update any article, journalists to update their own."""
    article = get_object_or_404(Article, id=article_id)

    if request.user.role == 'journalist' and article.author != request.user:
        messages.error(request, 'You can only edit your own articles.')
        return redirect('article_detail', article_id=article.id)

    publishers = Publisher.objects.all()

    if request.method == 'POST':
        article.title = request.POST.get('title', article.title).strip()
        article.summary = request.POST.get('summary', article.summary).strip()
        article.content = request.POST.get('content', article.content).strip()
        article.tags = request.POST.get('tags', article.tags).strip()
        article.is_public = request.POST.get('is_public') == 'on'
        publisher_id = request.POST.get('publisher')
        article.publisher = get_object_or_404(Publisher, id=publisher_id) if publisher_id else None
        article.save()
        messages.success(request, f'Article "{article.title}" updated successfully.')
        return redirect('article_detail', article_id=article.id)

    return render(request, 'NOPE/edit_article.html', {
        'article': article,
        'publishers': publishers,
        'title': f'Edit: {article.title}',
    })


@login_required
@user_passes_test(is_editor_or_journalist)
def delete_article(request, article_id):
    """Allow editors to delete any article, journalists to delete their own."""
    article = get_object_or_404(Article, id=article_id)

    if request.user.role == 'journalist' and article.author != request.user:
        messages.error(request, 'You can only delete your own articles.')
        return redirect('article_detail', article_id=article.id)

    if request.method == 'POST':
        title = article.title
        article.delete()
        messages.success(request, f'Article "{title}" deleted successfully.')
        if request.user.role == 'journalist':
            return redirect('my_articles')
        return redirect('dashboard')

    return render(request, 'NOPE/delete_article.html', {
        'article': article,
        'title': f'Delete: {article.title}',
    })


@login_required
@user_passes_test(is_editor_or_journalist)
def edit_newsletter(request, newsletter_id):
    """Allow editors to update any newsletter, journalists to update their own."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    if request.user.role == 'journalist' and newsletter.author != request.user:
        messages.error(request, 'You can only edit your own newsletters.')
        return redirect('newsletter_detail', newsletter_id=newsletter.id)

    approved_articles = Article.objects.filter(approved=True).order_by('-created_at')
    selected_ids = set(newsletter.articles.values_list('id', flat=True))

    if request.method == 'POST':
        newsletter.title = request.POST.get('title', newsletter.title).strip()
        newsletter.description = request.POST.get('description', newsletter.description).strip()
        newsletter.published = request.POST.get('published') == 'on'
        article_ids = request.POST.getlist('articles')
        newsletter.save()
        newsletter.articles.set(Article.objects.filter(id__in=article_ids))
        messages.success(request, f'Newsletter "{newsletter.title}" updated successfully.')
        return redirect('newsletter_detail', newsletter_id=newsletter.id)

    return render(request, 'NOPE/edit_newsletter.html', {
        'newsletter': newsletter,
        'approved_articles': approved_articles,
        'selected_ids': selected_ids,
        'title': f'Edit: {newsletter.title}',
    })


@login_required
@user_passes_test(is_editor_or_journalist)
def delete_newsletter(request, newsletter_id):
    """Allow editors to delete any newsletter, journalists to delete their own."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    if request.user.role == 'journalist' and newsletter.author != request.user:
        messages.error(request, 'You can only delete your own newsletters.')
        return redirect('newsletter_detail', newsletter_id=newsletter.id)

    if request.method == 'POST':
        title = newsletter.title
        newsletter.delete()
        messages.success(request, f'Newsletter "{title}" deleted successfully.')
        return redirect('newsletter_list')

    return render(request, 'NOPE/delete_newsletter.html', {
        'newsletter': newsletter,
        'title': f'Delete: {newsletter.title}',
    })


@login_required
def newsletter_list(request):
    """Display a paginated list of all published newsletters."""
    newsletters = Newsletter.objects.filter(published=True).select_related('author').order_by('-created_at')
    paginator = Paginator(newsletters, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'NOPE/newsletter_list.html', {'page_obj': page_obj, 'title': 'Newsletters'})


@login_required
def newsletter_detail(request, newsletter_id):
    """Display a single newsletter. Readers can only access published newsletters."""
    if request.user.role == 'reader':
        newsletter = get_object_or_404(Newsletter, id=newsletter_id, published=True)
    else:
        newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    return render(request, 'NOPE/newsletter_detail.html', {
        'newsletter': newsletter,
        'title': newsletter.title
    })


def publisher_list(request):
    """Display all publishers and highlight those the current reader is subscribed to."""
    publishers = Publisher.objects.all().order_by('name')
    subscribed_publisher_ids = set()
    if request.user.is_authenticated and request.user.role == 'reader':
        subscribed_publisher_ids = set(request.user.subscribed_publishers.values_list('id', flat=True))
    return render(request, 'NOPE/publisher_list.html', {
        'publishers': publishers,
        'subscribed_publisher_ids': subscribed_publisher_ids,
        'title': 'Publishers'
    })


@login_required
@user_passes_test(is_editor)
def create_publisher(request):
    """Display the publisher creation form and handle submission (editors only)."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        website = request.POST.get('website', '').strip()

        if not name:
            messages.error(request, 'Publisher name is required.')
        elif Publisher.objects.filter(name=name).exists():
            messages.error(request, 'A publisher with that name already exists.')
        else:
            Publisher.objects.create(name=name, description=description, website=website)
            messages.success(request, f'Publisher "{name}" created successfully.')
            return redirect('publisher_list')

    return render(request, 'NOPE/create_publisher.html', {'title': 'Create Publisher'})


@login_required
def manage_subscriptions(request):
    """Allow readers to subscribe or unsubscribe from publishers and journalists."""
    if request.user.role != 'reader':
        messages.error(request, 'Only readers can manage subscriptions.')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        publisher_id = request.POST.get('publisher_id')
        journalist_id = request.POST.get('journalist_id')

        if action == 'toggle_publisher' and publisher_id:
            publisher = get_object_or_404(Publisher, id=publisher_id)
            if request.user.subscribed_publishers.filter(id=publisher_id).exists():
                request.user.subscribed_publishers.remove(publisher)
                messages.success(request, f'Unsubscribed from {publisher.name}.')
            else:
                request.user.subscribed_publishers.add(publisher)
                messages.success(request, f'Subscribed to {publisher.name}.')

        elif action == 'toggle_journalist' and journalist_id:
            journalist = get_object_or_404(CustomUser, id=journalist_id, role='journalist')
            if request.user.subscribed_journalists.filter(id=journalist_id).exists():
                request.user.subscribed_journalists.remove(journalist)
                messages.success(request, f'Unsubscribed from {journalist.username}.')
            else:
                request.user.subscribed_journalists.add(journalist)
                messages.success(request, f'Subscribed to {journalist.username}.')

        return redirect('manage_subscriptions')

    publishers = Publisher.objects.all().order_by('name')
    journalists = CustomUser.objects.filter(role='journalist').order_by('username')
    subscribed_publisher_ids = set(request.user.subscribed_publishers.values_list('id', flat=True))
    subscribed_journalist_ids = set(request.user.subscribed_journalists.values_list('id', flat=True))

    return render(request, 'NOPE/manage_subscriptions.html', {
        'publishers': publishers,
        'journalists': journalists,
        'subscribed_publisher_ids': subscribed_publisher_ids,
        'subscribed_journalist_ids': subscribed_journalist_ids,
        'title': 'Manage Subscriptions'
    })
