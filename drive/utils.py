import os
import uuid
import mimetypes
from django.conf import settings
from django.utils.text import get_valid_filename

DOCUMENT_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'tsv', 'md', 'markdown',
    'json', 'xml', 'yaml', 'yml', 'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'htm', 'css', 'scss', 'sql', 'sh',
    'bash', 'log', 'env', 'ini', 'toml', 'conf', 'cfg', 'c', 'cpp', 'java', 'kt', 'rs', 'go', 'php', 'rb', 'r'
}
IMAGE_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico', 'tiff', 'jfif'
}
VIDEO_EXTENSIONS = {
    'mp4', 'webm', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'm4v'
}
AUDIO_EXTENSIONS = {
    'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'
}

def user_directory_path(instance, filename):
    """
    Generate clean, isolated user file paths.
    Format: uploads/user_<owner_id>/<unique_uuid>_<cleaned_filename>
    """
    clean_name = get_valid_filename(os.path.basename(filename)) or "file"
    unique_prefix = uuid.uuid4().hex[:10]
    return f"uploads/user_{instance.owner.id}/{unique_prefix}_{clean_name}"

def format_bytes(size_in_bytes):
    """
    Format bytes to human-readable format like 15 KB, 2.4 MB, 1.2 GB.
    """
    if size_in_bytes is None or size_in_bytes <= 0:
        return "0 B"
    size = float(size_in_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            if unit == 'B':
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

def get_file_category(extension, mime_type=""):
    ext = (extension or "").lower().lstrip('.')
    mime = (mime_type or "").lower()
    if ext == 'pdf' or 'pdf' in mime:
        return 'pdf'
    if ext in DOCUMENT_EXTENSIONS or ('document' in mime or 'text' in mime):
        return 'documents'
    if ext in IMAGE_EXTENSIONS or mime.startswith('image/'):
        return 'images'
    if ext in VIDEO_EXTENSIONS or mime.startswith('video/'):
        return 'videos'
    if ext in AUDIO_EXTENSIONS or mime.startswith('audio/'):
        return 'audio'
    return 'others'

def detect_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def get_user_storage_usage(user):
    from drive.models import DriveItem, UserProfile, STORAGE_PLAN_15GB
    from django.db.models import Sum

    total = 0
    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        total = DriveItem.objects.filter(owner=user, is_folder=False).aggregate(total=Sum('file_size'))['total'] or 0
        profile, _ = UserProfile.objects.get_or_create(user=user)
        limit = profile.storage_limit_bytes
        plan_id = profile.storage_plan
        plan_name = profile.formatted_plan_name
    else:
        limit = getattr(settings, 'USER_STORAGE_LIMIT_BYTES', STORAGE_PLAN_15GB)
        plan_id = '15GB'
        plan_name = '15 GB (Free / Basic)'

    percent = min(100.0, round((total / limit) * 100, 1)) if limit > 0 else 0.0
    return {
        'used_bytes': total,
        'limit_bytes': limit,
        'formatted_used': format_bytes(total),
        'formatted_limit': format_bytes(limit),
        'percent': percent,
        'plan_id': plan_id,
        'plan_name': plan_name,
    }


_ADMIN_EMAIL_CACHE = None

def clear_admin_email_cache():
    global _ADMIN_EMAIL_CACHE
    _ADMIN_EMAIL_CACHE = None

def get_admin_contact_email():
    """
    Retrieve the active administrator's contact email.
    Uses process-level caching to avoid repeated database lookups on every request.
    """
    global _ADMIN_EMAIL_CACHE
    if _ADMIN_EMAIL_CACHE is not None:
        return _ADMIN_EMAIL_CACHE

    from django.contrib.auth.models import User
    from django.db.models import Q

    admin = User.objects.filter(
        Q(is_superuser=True) | Q(is_staff=True) | Q(username__iexact='admin'),
        is_active=True,
        email__isnull=False
    ).exclude(email='').order_by('-is_superuser', '-is_staff', 'id').first()

    if admin and admin.email:
        _ADMIN_EMAIL_CACHE = admin.email.strip()
    else:
        _ADMIN_EMAIL_CACHE = getattr(settings, 'ADMIN_CONTACT_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@gmail.com'))

    return _ADMIN_EMAIL_CACHE


def cleanup_orphaned_media_files():
    """
    Scan media/uploads directory and delete any physical files that are no longer
    referenced by any DriveItem in the database, reclaiming lost storage and disk space.
    Returns dict with count of deleted files, reclaimed bytes, and human-readable string.
    """
    from drive.models import DriveItem
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    if not os.path.exists(upload_dir):
        return {'deleted_files': 0, 'reclaimed_bytes': 0, 'formatted_reclaimed': '0 B'}

    # Collect all active file paths from database (normalized with forward slashes)
    active_files = set(
        f.replace('\\', '/')
        for f in DriveItem.objects.exclude(file='').exclude(file__isnull=True).values_list('file', flat=True)
        if f
    )

    deleted_count = 0
    reclaimed_bytes = 0

    for root, dirs, files in os.walk(upload_dir, topdown=False):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, settings.MEDIA_ROOT).replace('\\', '/')
            if rel_path not in active_files:
                try:
                    file_size = os.path.getsize(full_path)
                    os.remove(full_path)
                    deleted_count += 1
                    reclaimed_bytes += file_size
                except Exception:
                    pass

        # Remove empty directories if any (skip root uploads folder)
        if root != upload_dir:
            try:
                if not os.listdir(root):
                    os.rmdir(root)
            except Exception:
                pass

    return {
        'deleted_files': deleted_count,
        'reclaimed_bytes': reclaimed_bytes,
        'formatted_reclaimed': format_bytes(reclaimed_bytes),
    }


