import os
import io
import json
import uuid
import zipfile
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404, HttpResponseBadRequest
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from django.db.models import Q, Sum

from django.contrib import messages
from drive.models import DriveItem
from drive.forms import UserRegisterForm, UserLoginForm, ForgotPasswordForm
from drive.utils import (
    format_bytes,
    detect_mime_type,
    get_file_category,
    get_user_storage_usage,
    get_admin_contact_email,
    clear_admin_email_cache,
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)


# ==============================================================================
# Authentication Views
# ==============================================================================

def register_view(request):
    if request.user.is_authenticated:
        return redirect('drive_root')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('drive_root')
    else:
        form = UserRegisterForm()
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('drive_root')
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get('next') or 'drive_root'
            return redirect(next_url)
    else:
        form = UserLoginForm()
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('drive_root')

    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            user = form.user
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            messages.success(request, f'Password for account "{user.username}" reset successfully! Please sign in with your new password.')
            return redirect('login')
    else:
        form = ForgotPasswordForm()

    return render(request, 'auth/forgot_password.html', {'form': form})


# ==============================================================================
# Browsing Views (My Drive, Nested Folders, Starred, Trash, Share)
# ==============================================================================

VALID_CATEGORIES = {
    'all', 'documents', 'doc', 'docs',
    'images', 'photos', 'photos_images', 'photos & images', 'photo',
    'pdf', 'pdfs',
    'videos', 'video',
    'audio',
    'folders', 'folder'
}

def clean_category(category):
    cat = (category or '').lower().strip()
    if cat not in VALID_CATEGORIES:
        return 'all'
    if cat in ['photos', 'photos_images', 'photos & images', 'photo']:
        return 'images'
    if cat in ['doc', 'docs']:
        return 'documents'
    if cat in ['video']:
        return 'videos'
    if cat in ['pdfs']:
        return 'pdf'
    if cat in ['folder']:
        return 'folders'
    return cat

def filter_items_by_category(queryset, category):
    cat = clean_category(category)
    if not cat or cat == 'all':
        return queryset

    if cat in ['pdf', 'pdfs']:
        return queryset.filter(is_folder=False).filter(
            Q(file_extension__iexact='pdf') |
            Q(mime_type='application/pdf') |
            Q(name__iendswith='.pdf')
        )
    elif cat in ['documents', 'doc', 'docs']:
        return queryset.filter(is_folder=False).filter(
            Q(file_extension__in=DOCUMENT_EXTENSIONS) |
            Q(mime_type__in=[
                'application/pdf', 'application/msword', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain', 'text/markdown', 'text/csv'
            ])
        )
    elif cat in ['images', 'photos', 'photos_images', 'photos & images', 'photo']:
        return queryset.filter(is_folder=False).filter(
            Q(file_extension__in=IMAGE_EXTENSIONS) |
            Q(mime_type__startswith='image/')
        )
    elif cat in ['videos', 'video']:
        return queryset.filter(is_folder=False).filter(
            Q(file_extension__in=VIDEO_EXTENSIONS) |
            Q(mime_type__startswith='video/')
        )
    elif cat in ['audio']:
        return queryset.filter(is_folder=False).filter(
            Q(file_extension__in=AUDIO_EXTENSIONS) |
            Q(mime_type__startswith='audio/')
        )
    elif cat in ['folders', 'folder']:
        return queryset.filter(is_folder=True)

    return queryset


def get_drive_view_context(request, items, page_title, active_tab, current_folder=None, breadcrumbs=None, search_everywhere=False, files_order='-created_at'):
    search_query = request.GET.get('q', '').strip()
    if search_query:
        if search_everywhere:
            items = DriveItem.objects.filter(owner=request.user, is_trashed=False, name__icontains=search_query)
        else:
            items = items.filter(name__icontains=search_query)

    category = clean_category(request.GET.get('category', 'all'))
    if category != 'all':
        items = filter_items_by_category(items, category)

    return {
        'current_folder': current_folder,
        'breadcrumbs': breadcrumbs if breadcrumbs is not None else ([] if not current_folder else current_folder.get_breadcrumbs()),
        'folders': items.filter(is_folder=True).order_by('name'),
        'files': items.filter(is_folder=False).order_by(files_order),
        'view_mode': request.GET.get('view', 'grid'),
        'search_query': search_query,
        'active_category': category,
        'page_title': page_title,
        'active_tab': active_tab,
    }


@login_required
def drive_root(request):
    items = DriveItem.objects.filter(owner=request.user, parent=None, is_trashed=False)
    context = get_drive_view_context(request, items, 'My Drive', 'my_drive', search_everywhere=True)
    return render(request, 'drive/index.html', context)


@login_required
def folder_view(request, folder_id):
    current_folder = get_object_or_404(DriveItem, id=folder_id, owner=request.user, is_folder=True, is_trashed=False)
    items = DriveItem.objects.filter(owner=request.user, parent=current_folder, is_trashed=False)
    context = get_drive_view_context(request, items, current_folder.name, 'my_drive', current_folder=current_folder)
    return render(request, 'drive/index.html', context)


@login_required
def starred_view(request):
    items = DriveItem.objects.filter(owner=request.user, is_starred=True, is_trashed=False)
    context = get_drive_view_context(request, items, 'Starred', 'starred', breadcrumbs=[{'id': '', 'name': 'Starred'}])
    return render(request, 'drive/starred.html', context)


@login_required
def trash_view(request):
    items = DriveItem.objects.filter(owner=request.user, is_trashed=True)
    context = get_drive_view_context(request, items, 'Trash', 'trash', breadcrumbs=[{'id': '', 'name': 'Trash'}], files_order='-trashed_at')
    return render(request, 'drive/trash.html', context)


def is_item_publicly_accessible(item):
    """
    Check if an item is publicly accessible because it is shared,
    or because any of its parent folders are shared.
    """
    if not item or item.is_trashed:
        return False
    if item.is_shared:
        return True
    current = item.parent
    while current:
        if current.is_trashed:
            return False
        if current.is_shared:
            return True
        current = current.parent
    return False


def share_view(request, share_token):
    """
    Public preview and download for shared files and folders.
    Supports full subfolder hierarchy navigation and interactive file previews.
    Accessible without login, or with any logged-in user.
    """
    item = get_object_or_404(DriveItem.objects.select_related('owner', 'parent'), share_token=share_token, is_shared=True, is_trashed=False)

    is_owner = request.user.is_authenticated and item.owner == request.user
    can_save_to_drive = request.user.is_authenticated and not is_owner

    context = {
        'item': item,
        'page_title': f"{item.name} - Shared Google Drive",
        'is_owner': is_owner,
        'can_save_to_drive': can_save_to_drive,
        'share_url': request.build_absolute_uri(f"/share/{item.share_token}/"),
    }

    if item.is_folder:
        current_folder = item
        breadcrumbs = [{'id': '', 'name': item.name}]

        subfolder_param = request.GET.get('subfolder', '').strip()
        if subfolder_param:
            try:
                sub_uuid = uuid.UUID(subfolder_param)
                candidate = DriveItem.objects.filter(id=sub_uuid, is_folder=True, is_trashed=False).first()
                if candidate:
                    # Verify candidate is a descendant of item
                    chain = []
                    curr = candidate
                    is_descendant = False
                    while curr:
                        if curr.id == item.id:
                            is_descendant = True
                            break
                        chain.insert(0, {'id': str(curr.id), 'name': curr.name})
                        curr = curr.parent
                    
                    if is_descendant:
                        current_folder = candidate
                        breadcrumbs.extend(chain)
            except (ValueError, TypeError):
                pass

        children_folders = current_folder.children.filter(is_folder=True, is_trashed=False).order_by('name')
        children_files = current_folder.children.filter(is_folder=False, is_trashed=False).order_by('name')

        context.update({
            'is_folder': True,
            'current_folder': current_folder,
            'breadcrumbs': breadcrumbs,
            'children_folders': children_folders,
            'children_files': children_files,
            'total_items_count': children_folders.count() + children_files.count(),
        })
    else:
        text_content = ''
        if item.preview_type == 'text' and item.file and os.path.exists(item.file.path):
            try:
                with open(item.file.path, 'r', encoding='utf-8', errors='replace') as f:
                    text_content = f.read(300000)
            except Exception:
                text_content = ''

        context.update({
            'is_folder': False,
            'text_content': text_content,
        })

    return render(request, 'drive/share.html', context)


def share_folder_download_zip(request, share_token):
    """
    Download a shared folder and all its contents as a ZIP archive.
    """
    item = get_object_or_404(DriveItem, share_token=share_token, is_shared=True, is_trashed=False, is_folder=True)

    target_folder = item
    subfolder_param = request.GET.get('subfolder', '').strip()
    if subfolder_param:
        try:
            sub_uuid = uuid.UUID(subfolder_param)
            candidate = DriveItem.objects.filter(id=sub_uuid, is_folder=True, is_trashed=False).first()
            if candidate:
                curr = candidate
                while curr:
                    if curr.id == item.id:
                        target_folder = candidate
                        break
                    curr = curr.parent
        except (ValueError, TypeError):
            pass

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        def add_folder_to_zip(folder, base_path=""):
            for f in folder.children.filter(is_folder=False, is_trashed=False):
                if f.file and os.path.exists(f.file.path):
                    arcname = os.path.join(base_path, f.name)
                    zip_file.write(f.file.path, arcname)
            for sub in folder.children.filter(is_folder=True, is_trashed=False):
                sub_path = os.path.join(base_path, sub.name)
                add_folder_to_zip(sub, sub_path)

        add_folder_to_zip(target_folder, "")

    buffer.seek(0)
    zip_name = f"{target_folder.name}.zip"
    return FileResponse(buffer, as_attachment=True, filename=zip_name, content_type='application/zip')


# ==============================================================================
# File Download View
# ==============================================================================

def download_file(request, file_id):
    """
    Download a file. Accessible by owner or if shared publicly directly/via parent folder.
    """
    item = get_object_or_404(DriveItem, id=file_id, is_folder=False)

    is_owner = request.user.is_authenticated and item.owner == request.user
    is_public = is_item_publicly_accessible(item)

    if not is_owner and not is_public:
        raise Http404("File not found or permission denied.")

    if not item.file or not os.path.exists(item.file.path):
        raise Http404("Physical file missing on server.")

    response = FileResponse(open(item.file.path, 'rb'), as_attachment=True, filename=item.name)
    return response


# ==============================================================================
# Helper Serialization
# ==============================================================================

def serialize_item(item):
    return {
        'id': str(item.id),
        'name': item.name,
        'is_folder': item.is_folder,
        'parent_id': str(item.parent_id) if item.parent_id else None,
        'file_size': item.file_size,
        'formatted_size': item.formatted_size,
        'mime_type': item.mime_type,
        'file_extension': item.file_extension,
        'is_starred': item.is_starred,
        'is_trashed': item.is_trashed,
        'is_shared': item.is_shared,
        'share_token': item.share_token or '',
        'file_url': item.file_url,
        'download_url': f"/drive/download/{item.id}/" if not item.is_folder else '',
        'preview_type': item.preview_type,
        'created_at': item.created_at.strftime('%b %d, %Y'),
        'updated_at': item.updated_at.strftime('%b %d, %Y'),
    }


# ==============================================================================
# JSON API Endpoints
# ==============================================================================

@login_required
@require_POST
def api_create_folder(request):
    name = request.POST.get('name', '').strip()
    parent_id = request.POST.get('parent_id', '').strip()

    if not name:
        return JsonResponse({'error': 'Folder name cannot be empty.'}, status=400)

    parent = None
    if parent_id:
        parent = get_object_or_404(DriveItem, id=parent_id, owner=request.user, is_folder=True, is_trashed=False)

    # Check for duplicate folder name in same directory
    if DriveItem.objects.filter(owner=request.user, parent=parent, is_folder=True, name=name, is_trashed=False).exists():
        return JsonResponse({'error': f'A folder named "{name}" already exists here.'}, status=409)

    folder = DriveItem.objects.create(
        owner=request.user,
        name=name,
        is_folder=True,
        parent=parent,
    )

    return JsonResponse({
        'success': True,
        'message': f'Folder "{name}" created.',
        'item': serialize_item(folder),
    })


@login_required
@require_POST
def api_upload_file(request):
    parent_id = request.POST.get('parent_id', '').strip()
    replace_existing = request.POST.get('replace', 'false').lower() == 'true'

    parent = None
    if parent_id:
        parent = get_object_or_404(DriveItem, id=parent_id, owner=request.user, is_folder=True, is_trashed=False)

    uploaded_files = request.FILES.getlist('files')
    if not uploaded_files and 'file' in request.FILES:
        uploaded_files = [request.FILES['file']]

    if not uploaded_files:
        return JsonResponse({'error': 'No files were uploaded.'}, status=400)

    # Check storage quota
    incoming_total_size = sum(f.size for f in uploaded_files)
    usage = get_user_storage_usage(request.user)
    if usage['used_bytes'] + incoming_total_size > usage['limit_bytes']:
        return JsonResponse({
            'error': f"Storage limit ({usage['formatted_limit']}) exceeded. Cannot upload files."
        }, status=413)

    existing_names = set(DriveItem.objects.filter(
        owner=request.user,
        parent=parent,
        is_folder=False,
        is_trashed=False
    ).values_list('name', flat=True))

    created_items = []
    for uploaded_file in uploaded_files:
        orig_name = uploaded_file.name
        ext = orig_name.split('.')[-1].lower() if '.' in orig_name else ''
        mime = detect_mime_type(orig_name)

        final_name = orig_name
        if final_name in existing_names:
            if replace_existing:
                DriveItem.objects.filter(
                    owner=request.user,
                    parent=parent,
                    is_folder=False,
                    name=final_name,
                    is_trashed=False
                ).delete()
            else:
                base, dot_ext = os.path.splitext(orig_name)
                counter = 1
                while final_name in existing_names:
                    final_name = f"{base} ({counter}){dot_ext}"
                    counter += 1
        existing_names.add(final_name)

        item = DriveItem.objects.create(
            owner=request.user,
            name=final_name,
            is_folder=False,
            parent=parent,
            file=uploaded_file,
            file_size=uploaded_file.size,
            mime_type=mime,
            file_extension=ext,
        )
        created_items.append(serialize_item(item))

    updated_storage = get_user_storage_usage(request.user)

    return JsonResponse({
        'success': True,
        'message': f"Uploaded {len(created_items)} file(s).",
        'items': created_items,
        'storage': updated_storage,
    })


@login_required
@require_POST
def api_rename_item(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)
    new_name = request.POST.get('name', '').strip()

    if not new_name:
        return JsonResponse({'error': 'Name cannot be empty.'}, status=400)

    # Check duplicate in same parent folder
    conflict = DriveItem.objects.filter(
        owner=request.user,
        parent=item.parent,
        is_folder=item.is_folder,
        name=new_name,
        is_trashed=False
    ).exclude(id=item.id).exists()

    if conflict:
        return JsonResponse({'error': f'An item named "{new_name}" already exists here.'}, status=409)

    item.name = new_name
    if not item.is_folder and '.' in new_name:
        item.file_extension = new_name.split('.')[-1].lower()
        item.mime_type = detect_mime_type(new_name)
    item.save()

    return JsonResponse({
        'success': True,
        'message': 'Renamed successfully.',
        'item': serialize_item(item),
    })


@login_required
@require_POST
def api_move_item(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)
    dest_id = request.POST.get('destination_id', '').strip()

    dest_folder = None
    if dest_id:
        dest_folder = get_object_or_404(DriveItem, id=dest_id, owner=request.user, is_folder=True, is_trashed=False)

    # Prevent moving item into its current folder
    if dest_folder == item.parent:
        return JsonResponse({'error': 'Item is already in this folder.'}, status=400)

    # Prevent folder from moving into itself or its descendants
    if item.is_folder:
        if dest_folder and (dest_folder.id == item.id or dest_folder in item.get_all_descendants()):
            return JsonResponse({'error': 'A folder cannot be moved into itself or its subfolders.'}, status=400)

    # Check for name conflicts in destination
    conflict = DriveItem.objects.filter(
        owner=request.user,
        parent=dest_folder,
        is_folder=item.is_folder,
        name=item.name,
        is_trashed=False
    ).exclude(id=item.id).first()

    if conflict:
        return JsonResponse({
            'error': f'An item named "{item.name}" already exists in the destination folder.'
        }, status=409)

    item.parent = dest_folder
    item.is_trashed = False
    item.trashed_at = None
    item.save()

    return JsonResponse({
        'success': True,
        'message': f'Moved "{item.name}" successfully.',
        'item': serialize_item(item),
    })


@login_required
@require_POST
def api_copy_item(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)
    dest_id = request.POST.get('destination_id', '').strip()

    dest_folder = None
    if dest_id:
        dest_folder = get_object_or_404(DriveItem, id=dest_id, owner=request.user, is_folder=True, is_trashed=False)

    # Calculate total size to copy
    all_to_copy = [item] + (item.get_all_descendants() if item.is_folder else [])
    copy_bytes = sum(entry.file_size for entry in all_to_copy if not entry.is_folder)

    usage = get_user_storage_usage(request.user)
    if usage['used_bytes'] + copy_bytes > usage['limit_bytes']:
        return JsonResponse({
            'error': f"This copy requires {format_bytes(copy_bytes)}, which exceeds your {usage['formatted_limit']} storage limit."
        }, status=413)

    # Recursive copy helper
    def deep_copy_item(source_item, target_parent):
        # Determine name to avoid collisions
        base_name = source_item.name
        if target_parent == source_item.parent:
            if source_item.is_folder:
                copy_name = f"{base_name} (Copy)"
            else:
                base, ext = os.path.splitext(base_name)
                copy_name = f"{base} (Copy){ext}"
        else:
            copy_name = base_name

        # Ensure unique name in target parent
        existing_names = set(DriveItem.objects.filter(owner=request.user, parent=target_parent, is_folder=source_item.is_folder, is_trashed=False).values_list('name', flat=True))
        counter = 1
        test_name = copy_name
        while test_name in existing_names:
            if source_item.is_folder:
                test_name = f"{copy_name} ({counter})"
            else:
                base, ext = os.path.splitext(copy_name)
                test_name = f"{base} ({counter}){ext}"
            counter += 1
        copy_name = test_name

        if source_item.is_folder:
            new_folder = DriveItem.objects.create(
                owner=request.user,
                name=copy_name,
                is_folder=True,
                parent=target_parent,
                is_starred=source_item.is_starred,
            )
            for child in source_item.children.filter(is_trashed=False):
                deep_copy_item(child, new_folder)
            return new_folder
        else:
            new_file_entry = DriveItem(
                owner=request.user,
                name=copy_name,
                is_folder=False,
                parent=target_parent,
                file_size=source_item.file_size,
                mime_type=source_item.mime_type,
                file_extension=source_item.file_extension,
                is_starred=source_item.is_starred,
            )
            if source_item.file and os.path.exists(source_item.file.path):
                with open(source_item.file.path, 'rb') as f:
                    new_file_entry.file.save(copy_name, ContentFile(f.read()), save=False)
            new_file_entry.save()
            return new_file_entry

    copied_root = deep_copy_item(item, dest_folder)
    updated_storage = get_user_storage_usage(request.user)

    return JsonResponse({
        'success': True,
        'message': f'Created copy of "{item.name}".',
        'item': serialize_item(copied_root),
        'storage': updated_storage,
    })


@login_required
@require_POST
def api_toggle_star(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)
    item.is_starred = not item.is_starred
    item.save(update_fields=['is_starred', 'updated_at'])

    return JsonResponse({
        'success': True,
        'is_starred': item.is_starred,
        'message': f'{"Added to" if item.is_starred else "Removed from"} Starred.',
    })


@login_required
@require_POST
def api_trash_item(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)
    now = timezone.now()

    # Move item to trash
    item.is_trashed = True
    item.is_starred = False
    item.trashed_at = now
    item.save(update_fields=['is_trashed', 'is_starred', 'trashed_at', 'updated_at'])

    # If it's a folder, trash all descendants in a single bulk update
    if item.is_folder:
        descendants = item.get_all_descendants()
        if descendants:
            desc_ids = [d.id for d in descendants]
            DriveItem.objects.filter(id__in=desc_ids).update(
                is_trashed=True,
                is_starred=False,
                trashed_at=now,
                updated_at=now
            )

    return JsonResponse({
        'success': True,
        'message': f'Moved "{item.name}" to Trash.',
    })


@login_required
@require_POST
def api_restore_item(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)
    now = timezone.now()

    # Check if parent is also trashed; if so, reparent to root
    if item.parent and item.parent.is_trashed:
        item.parent = None

    item.is_trashed = False
    item.trashed_at = None
    item.save(update_fields=['parent', 'is_trashed', 'trashed_at', 'updated_at'])

    if item.is_folder:
        descendants = item.get_all_descendants()
        if descendants:
            desc_ids = [d.id for d in descendants]
            DriveItem.objects.filter(id__in=desc_ids).update(
                is_trashed=False,
                trashed_at=None,
                updated_at=now
            )

    return JsonResponse({
        'success': True,
        'message': f'Restored "{item.name}".',
    })


@login_required
@require_POST
def api_delete_permanent(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)
    name = item.name
    item.delete()  # Physical file purged from disk via model delete & post_delete signal

    updated_storage = get_user_storage_usage(request.user)

    return JsonResponse({
        'success': True,
        'message': f'Permanently deleted "{name}".',
        'storage': updated_storage,
    })


@login_required
@require_POST
def api_empty_trash(request):
    trashed_items = list(DriveItem.objects.filter(owner=request.user, is_trashed=True))
    count = len(trashed_items)

    for item in trashed_items:
        item.delete()

    updated_storage = get_user_storage_usage(request.user)

    return JsonResponse({
        'success': True,
        'message': f'Emptied trash ({count} items deleted).',
        'storage': updated_storage,
    })


@login_required
@require_POST
def api_share_settings(request, item_id):
    item = get_object_or_404(DriveItem, id=item_id, owner=request.user)

    is_shared = request.POST.get('is_shared', 'false').lower() == 'true'

    if is_shared:
        if not item.share_token:
            item.share_token = uuid.uuid4().hex
        item.is_shared = True
    else:
        item.is_shared = False
        item.share_token = None

    item.save()

    share_url = request.build_absolute_uri(f"/share/{item.share_token}/") if item.is_shared else ""

    return JsonResponse({
        'success': True,
        'item_id': str(item.id),
        'name': item.name,
        'is_folder': item.is_folder,
        'is_shared': item.is_shared,
        'share_token': item.share_token or '',
        'share_url': share_url,
        'message': f'General access updated to {"Anyone with the link" if item.is_shared else "Restricted"}.',
    })


@login_required
@require_GET
def api_storage_stats(request):
    usage = get_user_storage_usage(request.user)
    usage['admin_email'] = get_admin_contact_email()
    return JsonResponse(usage)


@login_required
@require_GET
def api_available_folders(request, item_id=None):
    """
    Return all folders available for move or copy destinations.
    Excludes self and descendants if item_id is provided.
    Optimized to execute in a single SQL query with in-memory hierarchy traversal.
    """
    folders = list(DriveItem.objects.filter(owner=request.user, is_folder=True, is_trashed=False))
    folders_by_id = {str(f.id): f for f in folders}

    # Children mapping for in-memory descendant traversal
    children_map = {}
    for f in folders:
        pid = str(f.parent_id) if f.parent_id else None
        children_map.setdefault(pid, []).append(str(f.id))

    excluded_ids = set()
    if item_id and str(item_id) in folders_by_id:
        stack = [str(item_id)]
        while stack:
            curr_id = stack.pop()
            excluded_ids.add(curr_id)
            stack.extend(children_map.get(curr_id, []))

    def build_path(folder_id):
        path = []
        curr_id = folder_id
        while curr_id and curr_id in folders_by_id:
            folder = folders_by_id[curr_id]
            path.insert(0, folder.name)
            curr_id = str(folder.parent_id) if folder.parent_id else None
        return " > ".join(path)

    folder_list = [{'id': '', 'name': 'My Drive (Root)', 'path': 'My Drive'}]
    for f in folders:
        fid_str = str(f.id)
        if fid_str not in excluded_ids:
            path_str = build_path(fid_str)
            folder_list.append({
                'id': fid_str,
                'name': f.name,
                'path': f"My Drive > {path_str}" if path_str else f"My Drive > {f.name}"
            })

    return JsonResponse({'folders': folder_list})


@login_required
@require_GET
def api_instant_search(request):
    """
    Real-time autocomplete & instant search results as the user writes in the search bar.
    """
    query = request.GET.get('q', '').strip()
    category = clean_category(request.GET.get('category', ''))

    items = DriveItem.objects.select_related('parent').filter(owner=request.user, is_trashed=False)

    if query:
        clean_ext = query.lstrip('.')
        items = items.filter(
            Q(name__icontains=query) |
            Q(file_extension__iexact=clean_ext)
        )

    if category and category != 'all':
        items = filter_items_by_category(items, category)

    # Return up to 8 items, folders first, then recent items
    items = items.order_by('-is_folder', '-updated_at')[:8]

    serialized = []
    for item in items:
        serialized.append({
            'id': str(item.id),
            'name': item.name,
            'is_folder': item.is_folder,
            'category': item.category,
            'preview_type': item.preview_type,
            'formatted_size': item.formatted_size,
            'file_url': item.file_url if not item.is_folder else '',
            'folder_url': f"/drive/folder/{item.id}/" if item.is_folder else '',
            'updated_at': item.updated_at.strftime('%Y/%m/%d'),
            'parent_name': item.parent.name if item.parent else 'My Drive',
            'owner_name': 'You',
            'extension': (item.file_extension or '').lower().lstrip('.') or ('folder' if item.is_folder else 'file'),
        })

    return JsonResponse({
        'query': query,
        'results': serialized,
        'count': len(serialized),
    })


@login_required
@require_POST
def api_save_shared_copy(request, item_id):
    """
    Save a copy of a shared file or folder to the authenticated user's My Drive.
    """
    item = get_object_or_404(DriveItem, id=item_id, is_trashed=False)

    if not is_item_publicly_accessible(item) and item.owner != request.user:
        return JsonResponse({'error': 'Item is not shared or accessible.'}, status=403)

    if item.is_folder:
        new_folder = DriveItem.objects.create(
            owner=request.user,
            name=f"{item.name} (Shared Copy)",
            is_folder=True,
            parent=None
        )
        copied_count = 0
        for child in item.children.filter(is_folder=False, is_trashed=False):
            if child.file and os.path.exists(child.file.path):
                with open(child.file.path, 'rb') as f:
                    content = ContentFile(f.read())
                    new_file = DriveItem(
                        owner=request.user,
                        parent=new_folder,
                        name=child.name,
                        is_folder=False,
                        file_size=child.file_size,
                        mime_type=child.mime_type,
                        file_extension=child.file_extension
                    )
                    new_file.file.save(child.name, content, save=True)
                    copied_count += 1
        return JsonResponse({
            'success': True,
            'message': f'Folder "{item.name}" copied to your My Drive with {copied_count} files.',
            'redirect_url': f"/drive/folder/{new_folder.id}/",
        })
    else:
        if not item.file or not os.path.exists(item.file.path):
            return JsonResponse({'error': 'Physical file missing on server.'}, status=404)

        with open(item.file.path, 'rb') as f:
            content = ContentFile(f.read())
            new_file = DriveItem(
                owner=request.user,
                name=f"Copy of {item.name}" if item.owner == request.user else item.name,
                is_folder=False,
                file_size=item.file_size,
                mime_type=item.mime_type,
                file_extension=item.file_extension,
                parent=None
            )
            new_file.file.save(item.name, content, save=True)

        return JsonResponse({
            'success': True,
            'message': f'"{item.name}" saved to your My Drive!',
            'redirect_url': '/drive/',
        })


# ==============================================================================
# Batch Operations API Endpoints
# ==============================================================================

def _extract_item_ids(request):
    """
    Extract list of item ID strings from JSON payload, POST form data, or GET query params.
    """
    if request.content_type == 'application/json':
        try:
            raw = json.loads(request.body).get('item_ids', [])
            if isinstance(raw, list):
                return [str(x).strip() for x in raw if str(x).strip()]
        except Exception:
            pass

    for src in (request.POST, request.GET):
        items = src.getlist('item_ids') or src.getlist('item_ids[]')
        if not items:
            raw_str = src.get('item_ids', '')
            items = [x.strip() for x in raw_str.split(',') if x.strip()] if raw_str else []
        if items:
            return [str(x).strip() for x in items if str(x).strip()]

    return []


@login_required
@require_POST
def api_batch_trash(request):
    """
    Move multiple items to trash in a single batch operation.
    """
    item_ids = _extract_item_ids(request)
    if not item_ids:
        return JsonResponse({'error': 'No items selected.'}, status=400)

    now = timezone.now()
    items = list(DriveItem.objects.filter(id__in=item_ids, owner=request.user, is_trashed=False))
    if not items:
        return JsonResponse({'success': True, 'count': 0, 'message': 'No items moved to Trash.'})

    all_ids_to_trash = set()
    for item in items:
        all_ids_to_trash.add(item.id)
        if item.is_folder:
            for desc in item.get_all_descendants():
                all_ids_to_trash.add(desc.id)

    DriveItem.objects.filter(id__in=all_ids_to_trash).update(
        is_trashed=True,
        is_starred=False,
        trashed_at=now,
        updated_at=now
    )
    count = len(items)

    return JsonResponse({
        'success': True,
        'count': count,
        'message': f'Moved {count} item(s) to Trash.',
    })


@login_required
@require_POST
def api_batch_restore(request):
    """
    Restore multiple trashed items at once.
    """
    item_ids = _extract_item_ids(request)
    if not item_ids:
        return JsonResponse({'error': 'No items selected.'}, status=400)

    items = list(DriveItem.objects.filter(id__in=item_ids, owner=request.user, is_trashed=True))
    if not items:
        return JsonResponse({'success': True, 'count': 0, 'message': 'No items restored.'})

    now = timezone.now()
    all_ids_to_restore = set()
    for item in items:
        if item.parent and item.parent.is_trashed:
            item.parent = None
            item.save(update_fields=['parent'])
        all_ids_to_restore.add(item.id)
        if item.is_folder:
            for desc in item.get_all_descendants():
                all_ids_to_restore.add(desc.id)

    DriveItem.objects.filter(id__in=all_ids_to_restore).update(
        is_trashed=False,
        trashed_at=None,
        updated_at=now
    )
    count = len(items)

    return JsonResponse({
        'success': True,
        'count': count,
        'message': f'Restored {count} item(s).',
    })


@login_required
@require_POST
def api_batch_delete(request):
    """
    Permanently delete multiple items at once (from trash or drive).
    """
    item_ids = _extract_item_ids(request)
    if not item_ids:
        return JsonResponse({'error': 'No items selected.'}, status=400)

    items = list(DriveItem.objects.filter(id__in=item_ids, owner=request.user))
    count = 0
    for item in items:
        item.delete()
        count += 1

    updated_storage = get_user_storage_usage(request.user)
    return JsonResponse({
        'success': True,
        'count': count,
        'message': f'Permanently deleted {count} item(s).',
        'storage': updated_storage,
    })


@login_required
@require_POST
def api_batch_star(request):
    """
    Batch star or unstar items. Accepts action: 'star', 'unstar', or 'toggle'.
    """
    item_ids = _extract_item_ids(request)
    if not item_ids:
        return JsonResponse({'error': 'No items selected.'}, status=400)

    action = request.POST.get('action')
    if not action and request.content_type == 'application/json':
        try:
            action = json.loads(request.body).get('action')
        except Exception:
            pass
    if not action:
        action = 'toggle'

    now = timezone.now()
    qs = DriveItem.objects.filter(id__in=item_ids, owner=request.user, is_trashed=False)
    if action == 'star':
        count = qs.update(is_starred=True, updated_at=now)
    elif action == 'unstar':
        count = qs.update(is_starred=False, updated_at=now)
    else:
        count = 0
        for item in qs:
            item.is_starred = not item.is_starred
            item.save(update_fields=['is_starred', 'updated_at'])
            count += 1

    return JsonResponse({
        'success': True,
        'count': count,
        'message': f'Updated star for {count} item(s).',
    })


@login_required
@require_POST
def api_batch_move(request):
    """
    Batch move items into a target destination folder (or root).
    """
    item_ids = _extract_item_ids(request)
    if not item_ids:
        return JsonResponse({'error': 'No items selected.'}, status=400)

    dest_id = request.POST.get('destination_id', '').strip()
    if not dest_id and request.content_type == 'application/json':
        try:
            dest_id = str(json.loads(request.body).get('destination_id', '')).strip()
        except Exception:
            pass

    dest_folder = None
    if dest_id:
        dest_folder = get_object_or_404(DriveItem, id=dest_id, owner=request.user, is_folder=True, is_trashed=False)

    items = DriveItem.objects.filter(id__in=item_ids, owner=request.user, is_trashed=False)
    moved_count = 0
    errors = []

    existing_names = set(DriveItem.objects.filter(
        owner=request.user,
        parent=dest_folder,
        is_trashed=False
    ).values_list('name', flat=True))

    for item in items:
        if dest_folder == item.parent:
            continue
        if item.is_folder:
            if dest_folder and (dest_folder.id == item.id or dest_folder in item.get_all_descendants()):
                errors.append(f'Cannot move folder "{item.name}" into itself or its subfolder.')
                continue

        final_name = item.name
        if final_name in existing_names and final_name != item.name:
            base, ext = os.path.splitext(item.name) if not item.is_folder else (item.name, "")
            counter = 1
            while final_name in existing_names:
                final_name = f"{base} ({counter}){ext}"
                counter += 1

        existing_names.add(final_name)
        item.name = final_name
        item.parent = dest_folder
        item.save(update_fields=['name', 'parent', 'updated_at'])
        moved_count += 1

    return JsonResponse({
        'success': True,
        'count': moved_count,
        'message': f'Moved {moved_count} item(s).' + (f" ({len(errors)} skipped)" if errors else ""),
        'errors': errors,
    })


@login_required
def api_batch_download_zip(request):
    """
    Download multiple selected items as a single organized ZIP archive.
    """
    item_ids = _extract_item_ids(request)
    if not item_ids:
        return JsonResponse({'error': 'No items selected.'}, status=400)

    items = DriveItem.objects.filter(id__in=item_ids, owner=request.user, is_trashed=False)
    if not items.exists():
        return JsonResponse({'error': 'No valid items found.'}, status=404)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        def add_item_to_zip(item, base_path=""):
            if item.is_folder:
                folder_path = os.path.join(base_path, item.name)
                # Create directory entry in zip
                zip_file.writestr(f"{folder_path}/", "")
                for child in item.children.filter(is_trashed=False):
                    add_item_to_zip(child, folder_path)
            else:
                if item.file and os.path.exists(item.file.path):
                    arcname = os.path.join(base_path, item.name) if base_path else item.name
                    zip_file.write(item.file.path, arcname)

        for it in items:
            add_item_to_zip(it, "")

    buffer.seek(0)
    zip_name = "drive_items.zip" if items.count() > 1 else f"{items.first().name}.zip"
    return FileResponse(buffer, as_attachment=True, filename=zip_name, content_type='application/zip')


# ==============================================================================
# User Account, Profile & Password Management
# ==============================================================================

@login_required
@require_POST
def api_update_profile(request):
    """
    Update the authenticated user's username, first name, last name, and email.
    Synchronizes directly with Django's native User model so changes are
    immediately reflected across the user website and Django Admin Console.
    """
    user = request.user
    username = request.POST.get('username', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()

    # Validate and update username
    if username and username != user.username:
        if len(username) < 3:
            return JsonResponse({'error': 'Username must be at least 3 characters.'}, status=400)
        if User.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
            return JsonResponse({'error': f'Username "{username}" is already taken.'}, status=400)
        user.username = username

    # Validate and update email
    if email and email != user.email:
        if '@' not in email or '.' not in email.split('@')[-1]:
            return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            return JsonResponse({'error': f'Email "{email}" is already registered to another account.'}, status=400)
        user.email = email

    user.first_name = first_name
    user.last_name = last_name
    user.save()
    clear_admin_email_cache()

    full_name = user.get_full_name() or user.username
    initial = (user.first_name or user.username)[0].upper() if (user.first_name or user.username) else 'U'

    return JsonResponse({
        'success': True,
        'message': 'Profile updated successfully!',
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': full_name,
        'email': user.email,
        'initial': initial,
        'admin_email': get_admin_contact_email(),
    })


@login_required
@require_POST
def api_change_password(request):
    """
    Securely change the authenticated user's password.
    Preserves session auth hash so the user remains logged in.
    """
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    old_password = request.POST.get('old_password', '')
    new_password1 = request.POST.get('new_password1', '')
    new_password2 = request.POST.get('new_password2', '')

    if not old_password:
        return JsonResponse({'error': 'Please provide your current password.'}, status=400)

    if not request.user.check_password(old_password):
        return JsonResponse({'error': 'Current password is incorrect.'}, status=400)

    if not new_password1 or not new_password2:
        return JsonResponse({'error': 'Please provide and confirm your new password.'}, status=400)

    if new_password1 != new_password2:
        return JsonResponse({'error': 'New passwords do not match.'}, status=400)

    if old_password == new_password1:
        return JsonResponse({'error': 'Your new password cannot be the same as your old password.'}, status=400)

    # Validate new password with Django's configured password validators
    try:
        validate_password(new_password1, user=request.user)
    except ValidationError as err:
        return JsonResponse({'error': ' '.join(err.messages)}, status=400)

    request.user.set_password(new_password1)
    request.user.save()
    update_session_auth_hash(request, request.user)

    return JsonResponse({
        'success': True,
        'message': 'Password changed successfully! Your account is now secured with your new password.',
    })

