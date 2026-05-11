from rest_framework import permissions


class IsJournalistOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only journalists to create articles.
    Everyone can read (if authenticated).
    """
    
    def has_permission(self, request, view):
        """Allow read access to all authenticated users; write access to journalists only."""
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.role == 'journalist'


class IsEditorOrJournalistOrReadOnly(permissions.BasePermission):
    """
    Editors and journalists can modify, everyone (including unauthenticated) can read.
    """
    
    def has_permission(self, request, view):
        """Allow unauthenticated read access; require editor or journalist role for writes."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.role in ['editor', 'journalist']

    def has_object_permission(self, request, view, obj):
        """Editors can modify any object; journalists can only modify their own."""
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.role == 'editor':
            return True

        if request.user.role == 'journalist':
            return obj.author == request.user

        return False


class IsEditorOnly(permissions.BasePermission):
    """
    Only editors can perform this action.
    """
    
    def has_permission(self, request, view):
        """Allow access only to authenticated users with the editor role."""
        return request.user and request.user.is_authenticated and request.user.role == 'editor'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit an object.
    """
    
    def has_object_permission(self, request, view, obj):
        """Allow read access to anyone; restrict writes to the object's author."""
        if request.method in permissions.SAFE_METHODS:
            return True

        return hasattr(obj, 'author') and obj.author == request.user
