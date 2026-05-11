from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from NOPE.models import Article, Newsletter


class Command(BaseCommand):
    help = 'Set up user groups with appropriate permissions'

    def handle(self, *args, **options):
        # Get content types
        article_ct = ContentType.objects.get_for_model(Article)
        newsletter_ct = ContentType.objects.get_for_model(Newsletter)
        
        # Create or get groups
        reader_group, _ = Group.objects.get_or_create(name='Reader')
        editor_group, _ = Group.objects.get_or_create(name='Editor')
        journalist_group, _ = Group.objects.get_or_create(name='Journalist')
        
        # Clear existing permissions
        reader_group.permissions.clear()
        editor_group.permissions.clear()
        journalist_group.permissions.clear()
        
        # Reader permissions - view only
        reader_perms = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__startswith='view_'
        )
        reader_group.permissions.set(reader_perms)
        
        # Editor permissions - view, change, delete articles and newsletters
        editor_perms = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__in=[
                'view_article', 'change_article', 'delete_article', 'approve_article',
                'view_newsletter', 'change_newsletter', 'delete_newsletter'
            ]
        )
        editor_group.permissions.set(editor_perms)
        
        # Journalist permissions - create, view, change, delete their own content
        journalist_perms = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__in=[
                'add_article', 'view_article', 'change_article', 'delete_article',
                'add_newsletter', 'view_newsletter', 'change_newsletter', 'delete_newsletter'
            ]
        )
        journalist_group.permissions.set(journalist_perms)
        
        self.stdout.write(self.style.SUCCESS('Successfully configured user groups and permissions'))
        self.stdout.write(f'Reader: {reader_group.permissions.count()} permissions')
        self.stdout.write(f'Editor: {editor_group.permissions.count()} permissions')
        self.stdout.write(f'Journalist: {journalist_group.permissions.count()} permissions')
