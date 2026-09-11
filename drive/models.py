import os
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from drive.utils import (
    user_directory_path,
    format_bytes,
    get_file_category,
    detect_mime_type,
)
from drive.crypto import encrypted_storage


class DriveItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='drive_items'
    )
    name = models.CharField(max_length=255)
    is_folder = models.BooleanField(default=False)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children'
    )
    file = models.FileField(storage=encrypted_storage, upload_to=user_directory_path, null=True, blank=True)
    file_size = models.BigIntegerField(default=0)  # In bytes
    mime_type = models.CharField(max_length=120, default='application/octet-stream')
    file_extension = models.CharField(max_length=30, blank=True)
    is_starred = models.BooleanField(default=False)
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    is_shared = models.BooleanField(default=False)
    share_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_folder', 'name']
        indexes = [
            models.Index(fields=['owner', 'parent', 'is_trashed']),
            models.Index(fields=['owner', 'is_starred', 'is_trashed']),
            models.Index(fields=['owner', 'is_trashed']),
            models.Index(fields=['owner', 'is_folder']),
            models.Index(fields=['share_token']),
        ]

    def __str__(self):
        return f"{'[Folder] ' if self.is_folder else '[File] '}{self.name}"

    @property
    def file_url(self):
        if self.is_folder or not self.file:
            return ''
        return f"/drive/view/{self.id}/"

    def read_bytes(self):
        """Return decrypted raw file bytes."""
        from drive.crypto import read_decrypted_bytes
        return read_decrypted_bytes(self)

    def open_decrypted(self):
        """Return a seekable BytesIO stream containing decrypted file bytes."""
        from drive.crypto import get_decrypted_file_stream
        return get_decrypted_file_stream(self)

    def read_text(self, max_chars=300000):
        """Return decrypted file content as UTF-8 string."""
        from drive.crypto import read_decrypted_text
        return read_decrypted_text(self, max_chars=max_chars)


    @property
    def formatted_size(self):

        if self.is_folder:
            return "--"
        return format_bytes(self.file_size)

    @property
    def category(self):
        if self.is_folder:
            return 'folder'
        return get_file_category(self.file_extension, self.mime_type)

    @property
    def preview_type(self):
        if self.is_folder:
            return 'none'
        ext = (self.file_extension or '').lower().lstrip('.')
        mime = self.mime_type or ''
        if ext in {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico', 'jfif', 'tif', 'tiff', 'avif'} or mime.startswith('image/'):
            return 'image'
        if ext == 'pdf' or 'pdf' in mime:
            return 'pdf'
        if ext in {'mp4', 'webm', 'ogg', 'mov', 'm4v', 'mkv', 'avi', 'wmv', 'flv'} or mime.startswith('video/'):
            return 'video'
        if ext in {'mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac', 'wma', 'opus', 'm4b'} or mime.startswith('audio/'):
            return 'audio'
        if ext in {
            'txt', 'md', 'markdown', 'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'htm', 'css', 'scss', 'sass', 'less',
            'json', 'xml', 'csv', 'tsv', 'log', 'sh', 'bash', 'zsh', 'sql', 'yaml', 'yml', 'env', 'ini', 'toml',
            'conf', 'cfg', 'c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'java', 'kt', 'rs', 'go', 'php', 'rb', 'r',
            'bat', 'cmd', 'ps1', 'dockerfile', 'gitignore', 'lock', 'rst', 'tex'
        } or mime.startswith('text/') or mime in {
            'application/json', 'application/xml', 'application/javascript', 'application/x-sh',
            'application/x-yaml', 'application/x-python-code'
        }:
            return 'text'
        return 'none'

    @property
    def is_code_file(self):
        ext = (self.file_extension or '').lower().lstrip('.')
        return ext in {
            'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'htm', 'css', 'scss', 'sass', 'json', 'xml', 'sql',
            'sh', 'bash', 'yaml', 'yml', 'c', 'cpp', 'cc', 'h', 'hpp', 'java', 'kt', 'rs', 'go', 'php', 'rb'
        }

    @property
    def is_tabular_file(self):
        ext = (self.file_extension or '').lower().lstrip('.')
        return ext in {'csv', 'tsv'}

    @property
    def text_preview_snippet(self):
        """
        Return the first few lines of text content for preview rendering in grid cards.
        """
        if hasattr(self, '_cached_text_preview_snippet'):
            return self._cached_text_preview_snippet

        if self.is_folder or not self.file:
            self._cached_text_preview_snippet = ''
            return ''
        if self.preview_type != 'text':
            self._cached_text_preview_snippet = ''
            return ''
        try:
            self._cached_text_preview_snippet = self.read_text(max_chars=1200)
        except Exception:
            self._cached_text_preview_snippet = ''
        return self._cached_text_preview_snippet

    def get_breadcrumbs(self):
        """
        Return ordered list of ancestor folders from root to this item.
        """
        crumbs = []
        curr = self if self.is_folder else self.parent
        while curr is not None:
            crumbs.insert(0, {
                'id': str(curr.id),
                'name': curr.name,
            })
            curr = curr.parent
        return crumbs

    def get_all_descendants(self):
        """
        Return a flat list of all descendants (files & subfolders) recursively.
        Optimized to execute in a single database query with in-memory hierarchy traversal.
        """
        if not self.is_folder:
            return []
        all_items = list(DriveItem.objects.filter(owner_id=self.owner_id)) if self.owner_id else list(DriveItem.objects.all())
        children_map = {}
        for item in all_items:
            children_map.setdefault(item.parent_id, []).append(item)

        descendants = []
        stack = list(children_map.get(self.id, []))
        while stack:
            child = stack.pop()
            descendants.append(child)
            if child.is_folder:
                stack.extend(children_map.get(child.id, []))
        return descendants

    def clean_physical_file(self):
        """
        Physically delete the file from the filesystem and storage backend
        to free up disk storage space and memory.
        """
        if not self.file or not bool(self.file.name):
            return

        # 1. Close any open file descriptors so Windows file locks are released
        try:
            if hasattr(self.file, 'close'):
                self.file.close()
        except Exception:
            pass

        # 2. Check and remove via local filesystem path if available
        try:
            file_path = self.file.path if hasattr(self.file, 'path') else None
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        except Exception:
            pass

        # 3. Also delete through Django's storage backend (handles storage abstraction)
        try:
            if self.file.storage and self.file.storage.exists(self.file.name):
                self.file.storage.delete(self.file.name)
        except Exception:
            pass

    def delete(self, *args, **kwargs):
        """
        Ensure physical files are purged when DriveItem or folder tree is permanently deleted.
        """
        if self.is_folder:
            for descendant in self.get_all_descendants():
                if not descendant.is_folder:
                    descendant.clean_physical_file()
        else:
            self.clean_physical_file()
        super().delete(*args, **kwargs)


# ==============================================================================
# User Profile & Storage Plans (15 GB, 100 GB, 500 GB)
# ==============================================================================

STORAGE_PLAN_15GB = 15 * 1024 * 1024 * 1024
STORAGE_PLAN_100GB = 100 * 1024 * 1024 * 1024
STORAGE_PLAN_500GB = 500 * 1024 * 1024 * 1024

STORAGE_PLANS = [
    ('15GB', '15 GB (Free / Basic)'),
    ('100GB', '100 GB (Standard)'),
    ('500GB', '500 GB (Premium Pro)'),
]

PLAN_LIMITS = {
    '15GB': STORAGE_PLAN_15GB,
    '100GB': STORAGE_PLAN_100GB,
    '500GB': STORAGE_PLAN_500GB,
}


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    storage_plan = models.CharField(
        max_length=20,
        choices=STORAGE_PLANS,
        default='15GB',
        help_text="Storage tier allocated to this user."
    )
    custom_storage_limit_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Optional custom storage limit in bytes. Overrides plan tier if set."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile & Storage Plan'
        verbose_name_plural = 'User Profiles & Storage Plans'

    @property
    def storage_limit_bytes(self):
        if self.custom_storage_limit_bytes is not None and self.custom_storage_limit_bytes > 0:
            return self.custom_storage_limit_bytes
        return PLAN_LIMITS.get(self.storage_plan, STORAGE_PLAN_15GB)

    @property
    def formatted_plan_name(self):
        return dict(STORAGE_PLANS).get(self.storage_plan, '15 GB (Free / Basic)')

    def __str__(self):
        return f"{self.user.username} ({self.formatted_plan_name})"


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_delete, sender=DriveItem)
def auto_delete_file_on_driveitem_delete(sender, instance, **kwargs):
    """
    Guarantees physical file cleanup on the filesystem whenever a DriveItem
    record is deleted (from trash, batch delete, cascade delete, or admin delete).
    """
    if not instance.is_folder:
        instance.clean_physical_file()


@receiver(post_delete, sender=settings.AUTH_USER_MODEL)
def auto_cleanup_user_media_folder(sender, instance, **kwargs):
    """
    When a user is deleted, remove their upload directory if empty or purged.
    """
    import shutil
    user_folder = os.path.join(settings.MEDIA_ROOT, 'uploads', f"user_{instance.id}")
    if os.path.exists(user_folder):
        try:
            shutil.rmtree(user_folder, ignore_errors=True)
        except Exception:
            pass


