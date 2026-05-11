"""
NOPE signals module.

Handles post-save signals for the Article model: notifies subscribers by email
and posts to X (Twitter) when an article is approved and published.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Article, CustomUser
from datetime import datetime


@receiver(post_save, sender=Article)
def handle_article_approval(sender, instance, created, **kwargs):
    """Fire email and X notifications when an article is freshly approved."""
    if not created and instance.approved and instance.approved_at:
        time_since_approval = (datetime.now(instance.approved_at.tzinfo) - instance.approved_at).total_seconds()
        if time_since_approval > 5:
            return
        _notify_subscribers_via_email(instance)
        _post_to_x(instance)


def _notify_subscribers_via_email(article):
    """Send a notification email to all readers subscribed to the article's author or publisher."""
    subscribers = set()

    if article.author:
        subscribers.update(article.author.readers_following.filter(role='reader'))

    if article.publisher:
        subscribers.update(article.publisher.subscribers.filter(role='reader'))

    subject = f"New Article Published: {article.title}"
    message = (
        f"Hello!\n\n"
        f"A new article has been published:\n\n"
        f"Title: {article.title}\n"
        f"Author: {article.author.get_full_name() or article.author.username}\n"
    )
    if article.publisher:
        message += f"Publisher: {article.publisher.name}\n"
    message += f"\nSummary: {article.summary or 'No summary available.'}\n\n"
    message += "---\nNews Outside - Keeping you informed"

    recipient_emails = [user.email for user in subscribers if user.email]

    if recipient_emails:
        try:
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@newsoutside.com'),
                recipient_emails,
                fail_silently=False,
            )
            print(f"Email sent to {len(recipient_emails)} subscribers for: {article.title}")
        except Exception as exc:
            print(f"Error sending subscriber emails: {exc}")


def _post_to_x(article):
    """Post a summary of the approved article to X if API credentials are configured."""
    tweet_text = f"New article: {article.title}"
    if article.summary:
        summary = article.summary[:200]
        if len(article.summary) > 200:
            summary += "..."
        tweet_text += f"\n{summary}"

    key = getattr(settings, 'X_API_CONSUMER_KEY', '')
    secret = getattr(settings, 'X_API_CONSUMER_SECRET', '')
    token = getattr(settings, 'X_API_ACCESS_TOKEN', '')
    token_secret = getattr(settings, 'X_API_ACCESS_TOKEN_SECRET', '')

    if not all([key, secret, token, token_secret]):
        print(f"X API not configured — would post: {tweet_text[:80]}")
        return

    try:
        from requests_oauthlib import OAuth1Session
        oauth = OAuth1Session(
            key,
            client_secret=secret,
            resource_owner_key=token,
            resource_owner_secret=token_secret,
        )
        response = oauth.post(
            "https://api.twitter.com/2/tweets",
            json={"text": tweet_text},
        )
        if response.status_code == 201:
            print(f"Posted to X: {article.title}")
        else:
            print(f"X post failed ({response.status_code}): {response.text}")
    except Exception as exc:
        print(f"X post error: {exc}")
