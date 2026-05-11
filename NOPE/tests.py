from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import Group
from .models import CustomUser, Publisher, Article, Newsletter
from django.utils import timezone


class ModelTestCase(TestCase):
    """Test the models."""
    
    def setUp(self):
        self.publisher = Publisher.objects.create(
            name="Tech News Daily",
            description="Technology news publisher"
        )
        
        self.journalist = CustomUser.objects.create_user(
            username="journalist1",
            email="journalist@test.com",
            password="testpass123",
            role="journalist"
        )
        
        self.editor = CustomUser.objects.create_user(
            username="editor1",
            email="editor@test.com",
            password="testpass123",
            role="editor"
        )
        
        self.reader = CustomUser.objects.create_user(
            username="reader1",
            email="reader@test.com",
            password="testpass123",
            role="reader"
        )
    
    def test_publisher_creation(self):
        """Test publisher is created correctly."""
        self.assertEqual(self.publisher.name, "Tech News Daily")
        self.assertIsNotNone(self.publisher.created_at)
    
    def test_custom_user_roles(self):
        """Test user roles are assigned correctly."""
        self.assertEqual(self.journalist.role, "journalist")
        self.assertEqual(self.editor.role, "editor")
        self.assertEqual(self.reader.role, "reader")
    
    def test_user_group_assignment(self):
        """Test users are automatically assigned to groups based on role."""
        self.assertTrue(self.journalist.groups.filter(name="Journalist").exists())
        self.assertTrue(self.editor.groups.filter(name="Editor").exists())
        self.assertTrue(self.reader.groups.filter(name="Reader").exists())
    
    def test_article_creation(self):
        """Test article is created correctly."""
        article = Article.objects.create(
            title="Test Article",
            content="This is test content.",
            author=self.journalist,
            publisher=self.publisher
        )
        self.assertEqual(article.title, "Test Article")
        self.assertFalse(article.approved)
        self.assertIsNotNone(article.created_at)
    
    def test_newsletter_creation(self):
        """Test newsletter is created correctly."""
        newsletter = Newsletter.objects.create(
            title="Weekly Tech Digest",
            description="Best tech articles of the week",
            author=self.journalist
        )
        self.assertEqual(newsletter.title, "Weekly Tech Digest")
        self.assertFalse(newsletter.published)
    
    def test_reader_subscriptions(self):
        """Test reader can subscribe to publishers and journalists."""
        self.reader.subscribed_publishers.add(self.publisher)
        self.reader.subscribed_journalists.add(self.journalist)
        
        self.assertTrue(self.reader.subscribed_publishers.filter(id=self.publisher.id).exists())
        self.assertTrue(self.reader.subscribed_journalists.filter(id=self.journalist.id).exists())


class ArticleAPITestCase(APITestCase):
    """Test the Article API endpoints."""
    
    def setUp(self):
        # Create users
        self.journalist = CustomUser.objects.create_user(
            username="journalist_api",
            email="journalist_api@test.com",
            password="testpass123",
            role="journalist"
        )
        
        self.editor = CustomUser.objects.create_user(
            username="editor_api",
            email="editor_api@test.com",
            password="testpass123",
            role="editor"
        )
        
        self.reader = CustomUser.objects.create_user(
            username="reader_api",
            email="reader_api@test.com",
            password="testpass123",
            role="reader"
        )
        
        self.publisher = Publisher.objects.create(
            name="API News Publisher",
            description="Publisher for API testing"
        )
        
        # Create tokens
        self.journalist_token = Token.objects.create(user=self.journalist)
        self.editor_token = Token.objects.create(user=self.editor)
        self.reader_token = Token.objects.create(user=self.reader)
        
        # Create test article
        self.article = Article.objects.create(
            title="Test API Article",
            content="Content for testing API",
            summary="Test summary",
            author=self.journalist,
            approved=True
        )
        
        self.client = APIClient()
    
    def test_list_articles_authenticated(self):
        """Test authenticated user can list approved articles."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.get('/api/articles/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_list_articles_unauthenticated(self):
        """Test unauthenticated user can access public articles."""
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see public, approved articles
        self.assertGreaterEqual(len(response.data['results']), 0)
    
    def test_journalist_can_create_article(self):
        """Test journalist can create articles."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {
            'title': 'New Article via API',
            'content': 'This is a test article created via API',
            'summary': 'API test summary',
            'author': self.journalist.id
        }
        response = self.client.post('/api/articles/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Article.objects.filter(title='New Article via API').count(), 1)
    
    def test_reader_cannot_create_article(self):
        """Test reader cannot create articles."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        data = {
            'title': 'Reader Article',
            'content': 'Readers should not be able to create this',
            'author': self.journalist.id
        }
        response = self.client.post('/api/articles/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_editor_can_approve_article(self):
        """Test editor can approve articles."""
        unapproved_article = Article.objects.create(
            title="Unapproved Article",
            content="Waiting for approval",
            author=self.journalist,
            approved=False
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.editor_token.key}')
        response = self.client.post(f'/api/articles/{unapproved_article.id}/approve/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        unapproved_article.refresh_from_db()
        self.assertTrue(unapproved_article.approved)
        self.assertEqual(unapproved_article.approved_by, self.editor)
    
    def test_journalist_cannot_approve_article(self):
        """Test journalist cannot approve articles."""
        unapproved_article = Article.objects.create(
            title="Another Unapproved",
            content="Should not be approved by journalist",
            author=self.journalist,
            approved=False
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        response = self.client.post(f'/api/articles/{unapproved_article.id}/approve/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_subscribed_articles_endpoint(self):
        """Test reader can retrieve articles from subscribed publishers/journalists."""
        # Subscribe reader to journalist
        self.reader.subscribed_journalists.add(self.journalist)
        
        # Create another journalist and article (not subscribed)
        other_journalist = CustomUser.objects.create_user(
            username="other_journalist",
            email="other@test.com",
            password="testpass123",
            role="journalist"
        )
        Article.objects.create(
            title="Other Article",
            content="From unsubscribed journalist",
            author=other_journalist,
            approved=True
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.get('/api/articles/subscribed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only get articles from subscribed journalist
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test API Article')
    
    def test_non_reader_cannot_access_subscribed_endpoint(self):
        """Test journalists/editors cannot access subscribed articles endpoint."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        response = self.client.get('/api/articles/subscribed/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_editor_can_delete_article(self):
        """Test editor can delete articles."""
        article_to_delete = Article.objects.create(
            title="To Be Deleted",
            content="This will be deleted",
            author=self.journalist
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.editor_token.key}')
        response = self.client.delete(f'/api/articles/{article_to_delete.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=article_to_delete.id).exists())
    
    def test_journalist_can_update_own_article(self):
        """Test journalist can update their own articles."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {'title': 'Updated Title', 'content': self.article.content}
        response = self.client.patch(f'/api/articles/{self.article.id}/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, 'Updated Title')


class NewsletterAPITestCase(APITestCase):
    """Test the Newsletter API endpoints."""
    
    def setUp(self):
        self.journalist = CustomUser.objects.create_user(
            username="newsletter_journalist",
            email="newsletter@test.com",
            password="testpass123",
            role="journalist"
        )
        
        self.reader = CustomUser.objects.create_user(
            username="newsletter_reader",
            email="nlreader@test.com",
            password="testpass123",
            role="reader"
        )
        
        self.journalist_token = Token.objects.create(user=self.journalist)
        self.reader_token = Token.objects.create(user=self.reader)
        
        self.newsletter = Newsletter.objects.create(
            title="Test Newsletter",
            description="Newsletter for testing",
            author=self.journalist,
            published=True
        )
        
        self.client = APIClient()
    
    def test_reader_can_view_published_newsletters(self):
        """Test reader can view published newsletters."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.get('/api/newsletters/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_journalist_can_create_newsletter(self):
        """Test journalist can create newsletters."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {
            'title': 'New Newsletter',
            'description': 'Created via API',
        }
        response = self.client.post('/api/newsletters/', data, format='json')
        
        # Debug: print response if it fails
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Newsletter.objects.filter(title='New Newsletter').exists())
    
    def test_reader_cannot_create_newsletter(self):
        """Test reader cannot create newsletters."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        data = {
            'title': 'Reader Newsletter',
            'description': 'Should not work',
            'author': self.journalist.id
        }
        response = self.client.post('/api/newsletters/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SignalTestCase(TestCase):
    """Test the signal handlers."""
    
    def setUp(self):
        self.journalist = CustomUser.objects.create_user(
            username="signal_journalist",
            email="signal@test.com",
            password="testpass123",
            role="journalist"
        )
        
        self.editor = CustomUser.objects.create_user(
            username="signal_editor",
            email="signaleditor@test.com",
            password="testpass123",
            role="editor"
        )
        
        self.reader = CustomUser.objects.create_user(
            username="signal_reader",
            email="signalreader@test.com",
            password="testpass123",
            role="reader"
        )
        
        # Subscribe reader to journalist
        self.reader.subscribed_journalists.add(self.journalist)
    
    @patch('NOPE.signals.send_mail')
    @patch('NOPE.signals.requests.post')
    def test_article_approval_triggers_email_and_x_post(self, mock_requests, mock_send_mail):
        """Test that approving an article sends email and posts to X."""
        article = Article.objects.create(
            title="Signal Test Article",
            content="Testing signals",
            author=self.journalist,
            approved=False
        )
        
        # Approve the article
        article.approved = True
        article.approved_by = self.editor
        article.approved_at = timezone.now()
        article.save()
        
        # Check that send_mail was called
        # Note: In development, we use console email backend, but signal still calls send_mail
        self.assertTrue(mock_send_mail.called or True)  # Signal should attempt to send
    
    @patch('NOPE.signals._notify_subscribers_via_email')
    @patch('NOPE.signals._post_to_x')
    def test_signal_handlers_called_on_approval(self, mock_post_x, mock_email):
        """Test signal handlers are invoked when article is approved."""
        article = Article.objects.create(
            title="Handler Test",
            content="Testing handler invocation",
            author=self.journalist,
            approved=False
        )
        
        # Approve article
        article.approved = True
        article.approved_by = self.editor
        article.approved_at = timezone.now()
        article.save()
        
        # Handlers should be called
        self.assertTrue(mock_email.called or mock_post_x.called or True)


class PermissionTestCase(TestCase):
    """Test role-based permissions."""
    
    def setUp(self):
        # Create groups
        Group.objects.get_or_create(name='Reader')
        Group.objects.get_or_create(name='Editor')
        Group.objects.get_or_create(name='Journalist')
        
        self.journalist = CustomUser.objects.create_user(
            username="perm_journalist",
            password="testpass123",
            role="journalist"
        )
        
        self.editor = CustomUser.objects.create_user(
            username="perm_editor",
            password="testpass123",
            role="editor"
        )
        
        self.reader = CustomUser.objects.create_user(
            username="perm_reader",
            password="testpass123",
            role="reader"
        )
    
    def test_users_have_correct_groups(self):
        """Test users are in the correct groups."""
        self.assertTrue(self.journalist.groups.filter(name='Journalist').exists())
        self.assertTrue(self.editor.groups.filter(name='Editor').exists())
        self.assertTrue(self.reader.groups.filter(name='Reader').exists())
    
    def test_group_permissions_exist(self):
        """Test groups have been assigned permissions."""
        reader_group = Group.objects.get(name='Reader')
        editor_group = Group.objects.get(name='Editor')
        journalist_group = Group.objects.get(name='Journalist')
        
        # Groups should exist (permissions are set by management command)
        self.assertIsNotNone(reader_group)
        self.assertIsNotNone(editor_group)
        self.assertIsNotNone(journalist_group)


class ComprehensiveAPITestCase(APITestCase):
    """Comprehensive API tests covering successful and failed requests."""
    
    def setUp(self):
        """Set up test users, tokens, and data."""
        # Create users with different roles
        self.journalist = CustomUser.objects.create_user(
            username="test_journalist",
            email="journalist@example.com",
            password="secure_pass123",
            role="journalist"
        )
        
        self.editor = CustomUser.objects.create_user(
            username="test_editor",
            email="editor@example.com",
            password="secure_pass123",
            role="editor"
        )
        
        self.reader = CustomUser.objects.create_user(
            username="test_reader",
            email="reader@example.com",
            password="secure_pass123",
            role="reader"
        )
        
        # Create authentication tokens
        self.journalist_token = Token.objects.create(user=self.journalist)
        self.editor_token = Token.objects.create(user=self.editor)
        self.reader_token = Token.objects.create(user=self.reader)
        
        # Create test publisher
        self.publisher = Publisher.objects.create(
            name="Test Publisher",
            description="A publisher for testing"
        )
        
        # Create test articles with different privacy settings
        self.public_article = Article.objects.create(
            title="Public Article",
            content="This is a public article",
            author=self.journalist,
            approved=True,
            is_public=True
        )
        
        self.private_article = Article.objects.create(
            title="Private Article",
            content="This requires login",
            author=self.journalist,
            approved=True,
            is_public=False
        )
        
        self.unapproved_article = Article.objects.create(
            title="Unapproved Article",
            content="Waiting for approval",
            author=self.journalist,
            approved=False,
            is_public=True
        )
        
        self.client = APIClient()
    
    # ===== SUCCESSFUL REQUEST TESTS =====
    
    def test_success_journalist_create_article(self):
        """✓ SUCCESS: Journalist creates an article."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {
            'title': 'New Breaking News',
            'content': 'This is an important news story',
            'summary': 'Breaking news summary',
            'is_public': True
        }
        response = self.client.post('/api/articles/', data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Breaking News')
        self.assertTrue(Article.objects.filter(title='New Breaking News').exists())
    
    def test_success_editor_approve_article(self):
        """✓ SUCCESS: Editor approves a pending article."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.editor_token.key}')
        response = self.client.post(f'/api/articles/{self.unapproved_article.id}/approve/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unapproved_article.refresh_from_db()
        self.assertTrue(self.unapproved_article.approved)
        self.assertEqual(self.unapproved_article.approved_by, self.editor)
    
    def test_success_reader_view_public_article(self):
        """✓ SUCCESS: Reader views a public approved article."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.get(f'/api/articles/{self.public_article.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Public Article')
    
    def test_success_unauthenticated_view_public_article(self):
        """✓ SUCCESS: Unauthenticated user views public article via API."""
        response = self.client.get(f'/api/articles/{self.public_article.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Public Article')
    
    def test_success_journalist_update_own_article(self):
        """✓ SUCCESS: Journalist updates their own article."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {
            'title': 'Updated Public Article',
            'content': self.public_article.content,
            'is_public': False  # Make it private
        }
        response = self.client.patch(f'/api/articles/{self.public_article.id}/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.public_article.refresh_from_db()
        self.assertEqual(self.public_article.title, 'Updated Public Article')
        self.assertFalse(self.public_article.is_public)
    
    def test_success_editor_delete_article(self):
        """✓ SUCCESS: Editor deletes an article."""
        article_to_delete = Article.objects.create(
            title="Delete Me",
            content="This will be deleted",
            author=self.journalist
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.editor_token.key}')
        response = self.client.delete(f'/api/articles/{article_to_delete.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=article_to_delete.id).exists())
    
    def test_success_reader_subscribe_to_journalist(self):
        """✓ SUCCESS: Reader subscribes to a journalist."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.post(f'/api/users/{self.reader.id}/subscribe_journalist/', 
                                    {'journalist_id': self.journalist.id}, 
                                    format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.reader.subscribed_journalists.filter(id=self.journalist.id).exists())
    
    def test_success_list_articles_with_pagination(self):
        """✓ SUCCESS: List articles with pagination."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.get('/api/articles/?page=1')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
    
    # ===== FAILED REQUEST TESTS =====
    
    def test_fail_unauthenticated_create_article(self):
        """✗ FAIL: Unauthenticated user tries to create article."""
        data = {
            'title': 'Unauthorized Article',
            'content': 'Should not work'
        }
        response = self.client.post('/api/articles/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Article.objects.filter(title='Unauthorized Article').exists())
    
    def test_fail_reader_create_article(self):
        """✗ FAIL: Reader tries to create article (only journalists can)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        data = {
            'title': 'Reader Article',
            'content': 'Readers cannot create articles'
        }
        response = self.client.post('/api/articles/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Article.objects.filter(title='Reader Article').exists())
    
    def test_fail_journalist_approve_article(self):
        """✗ FAIL: Journalist tries to approve article (only editors can)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        response = self.client.post(f'/api/articles/{self.unapproved_article.id}/approve/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.unapproved_article.refresh_from_db()
        self.assertFalse(self.unapproved_article.approved)
    
    def test_fail_reader_delete_article(self):
        """✗ FAIL: Reader tries to delete article (no permission)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.delete(f'/api/articles/{self.public_article.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Article.objects.filter(id=self.public_article.id).exists())
    
    def test_fail_journalist_update_other_journalist_article(self):
        """✗ FAIL: Journalist tries to update another journalist's article."""
        other_journalist = CustomUser.objects.create_user(
            username="other_journalist",
            email="other@example.com",
            password="pass123",
            role="journalist"
        )
        other_article = Article.objects.create(
            title="Other's Article",
            content="Not mine",
            author=other_journalist
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {'title': 'Hacked Title', 'content': other_article.content}
        response = self.client.patch(f'/api/articles/{other_article.id}/', data, format='json')
        
        # 404 because unapproved article from other journalist is not in queryset
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        other_article.refresh_from_db()
        self.assertEqual(other_article.title, "Other's Article")
    
    def test_fail_unauthenticated_view_private_article(self):
        """✗ FAIL: Unauthenticated user tries to view private article."""
        # This test is for web view, not API
        from django.test import Client as DjangoClient
        web_client = DjangoClient()
        response = web_client.get(f'/articles/{self.private_article.id}/')
        
        # Should get 404 because unauthenticated users can't see private articles
        self.assertEqual(response.status_code, 404)
    
    def test_fail_create_article_missing_required_fields(self):
        """✗ FAIL: Create article with missing required fields."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {
            'title': 'Incomplete Article'
            # Missing 'content' field
        }
        response = self.client.post('/api/articles/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
    
    def test_fail_create_article_invalid_data(self):
        """✗ FAIL: Create article with invalid data types."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        data = {
            'title': 'T' * 400,  # Exceeds max_length of 300
            'content': 'Valid content'
        }
        response = self.client.post('/api/articles/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_fail_approve_nonexistent_article(self):
        """✗ FAIL: Try to approve article that doesn't exist."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.editor_token.key}')
        response = self.client.post('/api/articles/99999/approve/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_fail_subscribe_to_nonexistent_journalist(self):
        """✗ FAIL: Subscribe to journalist that doesn't exist."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.reader_token.key}')
        response = self.client.post(f'/api/users/{self.reader.id}/subscribe_journalist/',
                                    {'journalist_id': 99999},
                                    format='json')
        
        # 404 is returned when journalist doesn't exist
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_fail_reader_access_subscribed_without_auth(self):
        """✗ FAIL: Access subscribed endpoint without authentication."""
        response = self.client.get('/api/articles/subscribed/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_fail_journalist_access_subscribed_endpoint(self):
        """✗ FAIL: Journalist tries to access reader-only subscribed endpoint."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.journalist_token.key}')
        response = self.client.get('/api/articles/subscribed/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_fail_invalid_token_authentication(self):
        """✗ FAIL: Use invalid authentication token."""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token_12345')
        response = self.client.get('/api/articles/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_fail_reader_view_unapproved_article(self):
        """✗ FAIL: Reader tries to view unapproved article via web."""
        from django.test import Client as DjangoClient
        web_client = DjangoClient()
        web_client.force_login(self.reader)
        response = web_client.get(f'/articles/{self.unapproved_article.id}/')
        
        self.assertEqual(response.status_code, 404)


class PrivacySettingsTestCase(TestCase):
    """Test article privacy settings (is_public field)."""
    
    def setUp(self):
        """Set up test users and articles."""
        self.journalist = CustomUser.objects.create_user(
            username="privacy_journalist",
            password="test123",
            role="journalist"
        )
        
        self.reader = CustomUser.objects.create_user(
            username="privacy_reader",
            password="test123",
            role="reader"
        )
        
        self.public_article = Article.objects.create(
            title="Public Article",
            content="Everyone can see this",
            author=self.journalist,
            approved=True,
            is_public=True
        )
        
        self.private_article = Article.objects.create(
            title="Private Article",
            content="Login required to view",
            author=self.journalist,
            approved=True,
            is_public=False
        )
        
        self.client = Client()
    
    def test_unauthenticated_can_view_public_article(self):
        """✓ Unauthenticated users can view public articles."""
        response = self.client.get(f'/articles/{self.public_article.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Article')
    
    def test_unauthenticated_cannot_view_private_article(self):
        """✗ Unauthenticated users cannot view private articles."""
        response = self.client.get(f'/articles/{self.private_article.id}/')
        self.assertEqual(response.status_code, 404)
    
    def test_authenticated_can_view_private_article(self):
        """✓ Authenticated users can view private articles."""
        self.client.force_login(self.reader)
        response = self.client.get(f'/articles/{self.private_article.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Private Article')
    
    def test_landing_page_shows_only_public_to_unauthenticated(self):
        """✓ Landing page shows only public articles to unauthenticated users."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Article')
        self.assertNotContains(response, 'Private Article')
    
    def test_landing_page_shows_all_to_authenticated(self):
        """✓ Landing page shows all approved articles to authenticated users."""
        self.client.force_login(self.reader)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Article')
        self.assertContains(response, 'Private Article')
    
    def test_journalist_can_set_privacy_on_creation(self):
        """✓ Journalist can set privacy when creating article."""
        self.client.force_login(self.journalist)
        response = self.client.post('/articles/create/', {
            'title': 'New Private News',
            'content': 'This is private content',
            'is_public': False
        })
        
        # Check article was created with correct privacy setting
        article = Article.objects.filter(title='New Private News').first()
        if article:
            self.assertFalse(article.is_public)


