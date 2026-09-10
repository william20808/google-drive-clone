"""
Comprehensive Functional & Feature Validation Suite
Consolidates all feature-level verifications from scratch/ into a single, high-efficiency test suite:
1. Account profile updates, uniqueness constraints, format validations & password lifecycle.
2. Account & Django Admin bidirectional sync and admin user creation edge cases (nameless users).
3. Storage plan tiers, usage calculations, UI quota modals & admin console access.
4. Folder tree hierarchies, public share link navigation, dedicated reading modes & full batch operations suite.
"""

import os
import sys
import io
import json
import zipfile

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gdrive_project.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.files.uploadedfile import SimpleUploadedFile
from drive.models import DriveItem, UserProfile
from drive.utils import get_user_storage_usage


def test_account_lifecycle_and_validation():
    print("\n--- [Section 1] Testing Account Profile, Password Lifecycle & Validation ---")
    client = Client()
    test_username = "validation_user"
    test_email = "validation_init@example.com"
    initial_pass = "InitialSecurePass123!"

    # Clean up prior test users
    User.objects.filter(username__in=[test_username, "validation_user_renamed", "collision_test_user"]).delete()

    user = User.objects.create_user(
        username=test_username,
        email=test_email,
        password=initial_pass,
        first_name="InitialFirst",
        last_name="InitialLast"
    )
    collision_user = User.objects.create_user(
        username="collision_test_user",
        email="collision_test@example.com",
        password=initial_pass
    )

    logged_in = client.login(username=test_username, password=initial_pass)
    assert logged_in, "Client login failed"

    # 1. Username Collision Rejection
    res = client.post('/api/account/profile/', {
        'username': 'collision_test_user',
        'first_name': 'First',
        'last_name': 'Last',
        'email': test_email
    })
    assert res.status_code == 400 and 'already taken' in res.json().get('error', '').lower()

    # 2. Username Length Validation (< 3 chars)
    res = client.post('/api/account/profile/', {
        'username': 'xy',
        'first_name': 'First',
        'last_name': 'Last',
        'email': test_email
    })
    assert res.status_code == 400 and 'at least 3 characters' in res.json().get('error', '').lower()

    # 3. Valid Username & Name Update
    new_username = "validation_user_renamed"
    res = client.post('/api/account/profile/', {
        'username': new_username,
        'first_name': 'UpdatedFirst',
        'last_name': 'UpdatedLast',
        'email': test_email
    })
    assert res.status_code == 200
    assert res.json()['username'] == new_username
    user.refresh_from_db()
    assert user.username == new_username and user.first_name == 'UpdatedFirst'

    # 4. Email Format Rejection
    res = client.post('/api/account/profile/', {
        'username': new_username,
        'first_name': 'UpdatedFirst',
        'last_name': 'UpdatedLast',
        'email': 'not-a-valid-email'
    })
    assert res.status_code == 400 and 'valid email' in res.json().get('error', '').lower()

    # 5. Email Collision Rejection
    res = client.post('/api/account/profile/', {
        'username': new_username,
        'first_name': 'UpdatedFirst',
        'last_name': 'UpdatedLast',
        'email': 'collision_test@example.com'
    })
    assert res.status_code == 400 and 'already registered' in res.json().get('error', '').lower()

    # 6. Valid Email Update
    new_email = "validation_updated@example.com"
    res = client.post('/api/account/profile/', {
        'username': new_username,
        'first_name': 'UpdatedFirst',
        'last_name': 'UpdatedLast',
        'email': new_email
    })
    assert res.status_code == 200
    user.refresh_from_db()
    assert user.email == new_email

    # 7. Password Validations: Wrong Old Pass, Mismatch, Same Pass, Short Pass
    new_pass = "BrandNewValidPass2026!#"
    # Wrong old pass
    res = client.post('/api/account/change-password/', {
        'old_password': 'WrongPass123!',
        'new_password1': new_pass,
        'new_password2': new_pass
    })
    assert res.status_code == 400 and 'incorrect' in res.json().get('error', '').lower()

    # Mismatch
    res = client.post('/api/account/change-password/', {
        'old_password': initial_pass,
        'new_password1': new_pass,
        'new_password2': 'MismatchPass!'
    })
    assert res.status_code == 400 and 'match' in res.json().get('error', '').lower()

    # Same password
    res = client.post('/api/account/change-password/', {
        'old_password': initial_pass,
        'new_password1': initial_pass,
        'new_password2': initial_pass
    })
    assert res.status_code == 400 and 'same' in res.json().get('error', '').lower()

    # Short password
    res = client.post('/api/account/change-password/', {
        'old_password': initial_pass,
        'new_password1': 'short',
        'new_password2': 'short'
    })
    assert res.status_code == 400 and ('short' in res.json().get('error', '').lower() or 'at least 8' in res.json().get('error', '').lower())

    # Valid password change
    res = client.post('/api/account/change-password/', {
        'old_password': initial_pass,
        'new_password1': new_pass,
        'new_password2': new_pass
    })
    assert res.status_code == 200 and res.json()['success'] is True

    # DB & Re-authentication check
    user.refresh_from_db()
    assert not user.check_password(initial_pass)
    assert user.check_password(new_pass)
    auth_user = authenticate(username=new_username, password=new_pass)
    assert auth_user is not None and auth_user.pk == user.pk

    # Cleanup
    user.delete()
    collision_user.delete()
    print("  -> Section 1 PASSED: All account lifecycle, validations & auth confirmed.")


def test_account_admin_sync_and_management():
    print("\n--- [Section 2] Testing Bidirectional Name Sync & Admin User Management ---")
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin_sync_test', 'admin_sync@example.com', 'AdminPass123!')
    
    sync_user, _ = User.objects.get_or_create(username='sync_test_user')
    sync_user.first_name = 'SyncFirst'
    sync_user.last_name = 'SyncLast'
    sync_user.set_password('SyncPass123!')
    sync_user.save()

    # Nameless user edge case test
    nameless_user, _ = User.objects.get_or_create(username='sync_nameless_user')
    nameless_user.first_name = ''
    nameless_user.last_name = ''
    nameless_user.save()

    admin_client = Client()
    admin_client.force_login(admin_user)

    # 1. Admin changelist loads without error and displays '(No name set)'
    res_list = admin_client.get('/admin/auth/user/')
    assert res_list.status_code == 200
    html = res_list.content.decode('utf-8')
    assert 'sync_nameless_user' in html
    assert '(No name set)' in html

    # 2. Admin adds user via /admin/auth/user/add/
    User.objects.filter(username='admin_created_user').delete()
    res_add = admin_client.post('/admin/auth/user/add/', {
        'username': 'admin_created_user',
        'password1': 'AdminCreatedPass123!',
        'password2': 'AdminCreatedPass123!',
    })
    assert res_add.status_code == 302
    created = User.objects.filter(username='admin_created_user').first()
    assert created is not None

    # Verify user change page loads inline UserProfile cleanly
    res_change = admin_client.get(f'/admin/auth/user/{created.id}/change/')
    assert res_change.status_code == 200
    assert 'storage_plan' in res_change.content.decode('utf-8') or 'Storage Profile' in res_change.content.decode('utf-8')

    # 3. Bidirectional Sync: Admin updates user name -> reflected on user views
    sync_user.first_name = 'AdminEditedFirst'
    sync_user.last_name = 'AdminEditedLast'
    sync_user.save()

    user_client = Client()
    user_client.force_login(sync_user)
    res_drive = user_client.get('/drive/')
    assert res_drive.status_code == 200
    assert 'AdminEditedFirst AdminEditedLast' in res_drive.content.decode('utf-8')

    # User updates name via API -> reflected in Admin Console
    res_api = user_client.post('/api/account/profile/', {
        'first_name': 'UserSelfFirst',
        'last_name': 'UserSelfLast',
        'email': 'userself@example.com'
    })
    assert res_api.status_code == 200
    res_admin_check = admin_client.get('/admin/auth/user/')
    assert 'UserSelfFirst UserSelfLast' in res_admin_check.content.decode('utf-8')

    # Cleanup
    created.delete()
    nameless_user.delete()
    sync_user.delete()
    print("  -> Section 2 PASSED: Bidirectional name sync and admin user handling confirmed.")


def test_storage_plans_and_admin_system():
    print("\n--- [Section 3] Testing Storage Plan Tiers, Quota & Admin Console ---")
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin_storage_test', 'admin_storage@example.com', 'AdminPass123!')

    storage_user, _ = User.objects.get_or_create(username='storage_tier_user')
    profile, _ = UserProfile.objects.get_or_create(user=storage_user)

    # 1. Check 15GB, 100GB, 500GB plans
    for plan, expected_limit_str in [('15GB', '15.0 GB'), ('100GB', '100.0 GB'), ('500GB', '500.0 GB')]:
        profile.storage_plan = plan
        profile.custom_storage_limit_bytes = None
        profile.save()
        usage = get_user_storage_usage(storage_user)
        assert usage['plan_id'] == plan
        assert expected_limit_str in usage['formatted_limit']

    # Reset to 15GB
    profile.storage_plan = '15GB'
    profile.save()

    # 2. Check UI elements for storage modal and admin email
    client = Client()
    client.force_login(storage_user)
    res = client.get('/drive/')
    assert res.status_code == 200
    html = res.content.decode('utf-8')
    assert 'modal_storage_plans' in html
    assert 'modal_contact_admin' in html
    assert '15 GB' in html
    assert '100 GB' in html
    assert '500 GB' in html

    # 3. Superuser access to Admin Console and UserProfile changelist
    admin_client = Client()
    admin_client.force_login(admin_user)
    res_admin = admin_client.get('/admin/')
    assert res_admin.status_code == 200
    assert 'Google Drive Admin Console' in res_admin.content.decode('utf-8')

    res_profiles = admin_client.get('/admin/drive/userprofile/')
    assert res_profiles.status_code == 200
    assert 'storage_tier_user' in res_profiles.content.decode('utf-8')

    # Cleanup
    storage_user.delete()
    print("  -> Section 3 PASSED: Storage plans, quota calculation & admin console confirmed.")


def test_batch_operations_and_sharing():
    print("\n--- [Section 4] Testing Public Sharing, Reading Modes & Batch Operations ---")
    user, _ = User.objects.get_or_create(username='batch_share_test_user')
    user.set_password('BatchPass123!')
    user.save()

    client = Client()
    client.force_login(user)

    # 1. Setup folder hierarchy and files
    root_folder = DriveItem.objects.create(owner=user, name='Root Batch Folder', is_folder=True)
    subfolder = DriveItem.objects.create(owner=user, name='Nested Subfolder', is_folder=True, parent=root_folder)
    deep_folder = DriveItem.objects.create(owner=user, name='Deep Subfolder', is_folder=True, parent=subfolder)

    pdf_content = b"%PDF-1.4 Mock PDF stream for preview verification"
    pdf_file = DriveItem.objects.create(
        owner=user, name='test_doc.pdf', is_folder=False, parent=subfolder,
        file_size=len(pdf_content), mime_type='application/pdf', file_extension='pdf'
    )
    pdf_file.file.save('test_doc.pdf', SimpleUploadedFile('test_doc.pdf', pdf_content), save=True)

    img_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    img_file = DriveItem.objects.create(
        owner=user, name='test_img.png', is_folder=False, parent=root_folder,
        file_size=len(img_content), mime_type='image/png', file_extension='png'
    )
    img_file.file.save('test_img.png', SimpleUploadedFile('test_img.png', img_content), save=True)

    vid_content = b"\x00\x00\x00\x18ftypmp42"
    vid_file = DriveItem.objects.create(
        owner=user, name='test_vid.mp4', is_folder=False, parent=root_folder,
        file_size=len(vid_content), mime_type='video/mp4', file_extension='mp4'
    )
    vid_file.file.save('test_vid.mp4', SimpleUploadedFile('test_vid.mp4', vid_content), save=True)

    # 2. Public Folder Sharing & Anonymous Subfolder Navigation
    share_res = client.post(f'/api/items/{root_folder.id}/share/', {'is_shared': 'true'})
    assert share_res.status_code == 200
    root_folder.refresh_from_db()
    token = root_folder.share_token
    assert token

    anon_client = Client()
    # Root share
    res_share = anon_client.get(f'/share/{token}/')
    assert res_share.status_code == 200
    html_share = res_share.content.decode('utf-8')
    assert 'Root Batch Folder' in html_share
    assert 'Nested Subfolder' in html_share

    # Subfolder navigation
    res_sub = anon_client.get(f'/share/{token}/?subfolder={subfolder.id}')
    assert res_sub.status_code == 200
    html_sub = res_sub.content.decode('utf-8')
    assert 'Nested Subfolder' in html_sub
    assert 'test_doc.pdf' in html_sub

    # Shared Folder Recursive ZIP Download
    res_zip = anon_client.get(f'/share/{token}/download-zip/')
    assert res_zip.status_code == 200
    assert res_zip['Content-Type'] == 'application/zip'
    with zipfile.ZipFile(io.BytesIO(b"".join(res_zip.streaming_content)), 'r') as zf:
        names = zf.namelist()
        assert any('test_doc.pdf' in n for n in names)
        assert any('test_img.png' in n for n in names)

    # 3. Direct File Share Modes: PDF, Image, Video
    client.post(f'/api/items/{pdf_file.id}/share/', {'is_shared': 'true'})
    pdf_file.refresh_from_db()
    res_pdf = anon_client.get(f'/share/{pdf_file.share_token}/')
    assert res_pdf.status_code == 200
    pdf_html = res_pdf.content.decode('utf-8')
    assert 'PDF Reading Mode' in pdf_html
    assert 'pdf-reading-iframe' in pdf_html
    assert 'zoomPdf' in pdf_html

    client.post(f'/api/items/{img_file.id}/share/', {'is_shared': 'true'})
    img_file.refresh_from_db()
    res_img = anon_client.get(f'/share/{img_file.share_token}/')
    assert res_img.status_code == 200
    img_html = res_img.content.decode('utf-8')
    assert 'share-preview-img' in img_html
    assert 'zoomImage' in img_html

    client.post(f'/api/items/{vid_file.id}/share/', {'is_shared': 'true'})
    vid_file.refresh_from_db()
    res_vid = anon_client.get(f'/share/{vid_file.share_token}/')
    assert res_vid.status_code == 200
    vid_html = res_vid.content.decode('utf-8')
    assert 'share-video-player' in vid_html
    assert 'setVideoSpeed' in vid_html

    # 4. Batch Operations: Star, Move, Download ZIP, Trash, Restore, Permanent Delete
    # Batch Star
    res_star = client.post('/api/batch/star/', json.dumps({
        'item_ids': [str(pdf_file.id), str(img_file.id)],
        'action': 'star'
    }), content_type='application/json')
    assert res_star.status_code == 200
    pdf_file.refresh_from_db()
    img_file.refresh_from_db()
    assert pdf_file.is_starred is True and img_file.is_starred is True

    # Batch Move
    res_move = client.post('/api/batch/move/', json.dumps({
        'item_ids': [str(img_file.id), str(vid_file.id)],
        'destination_id': str(deep_folder.id)
    }), content_type='application/json')
    assert res_move.status_code == 200
    img_file.refresh_from_db()
    vid_file.refresh_from_db()
    assert img_file.parent_id == deep_folder.id and vid_file.parent_id == deep_folder.id

    # Batch Download ZIP
    res_bzip = client.get(f'/api/batch/download-zip/?item_ids={img_file.id}&item_ids={vid_file.id}')
    assert res_bzip.status_code == 200
    assert res_bzip['Content-Type'] == 'application/zip'
    with zipfile.ZipFile(io.BytesIO(b"".join(res_bzip.streaming_content)), 'r') as zf:
        bnames = zf.namelist()
        assert 'test_img.png' in bnames and 'test_vid.mp4' in bnames

    # Batch Trash
    res_trash = client.post('/api/batch/trash/', json.dumps({
        'item_ids': [str(img_file.id), str(vid_file.id)]
    }), content_type='application/json')
    assert res_trash.status_code == 200
    img_file.refresh_from_db()
    vid_file.refresh_from_db()
    assert img_file.is_trashed is True and vid_file.is_trashed is True

    # Batch Restore
    res_restore = client.post('/api/batch/restore/', json.dumps({
        'item_ids': [str(img_file.id), str(vid_file.id)]
    }), content_type='application/json')
    assert res_restore.status_code == 200
    img_file.refresh_from_db()
    vid_file.refresh_from_db()
    assert img_file.is_trashed is False and vid_file.is_trashed is False

    # Batch Delete
    res_del = client.post('/api/batch/delete/', json.dumps({
        'item_ids': [str(img_file.id), str(vid_file.id)]
    }), content_type='application/json')
    assert res_del.status_code == 200
    assert not DriveItem.objects.filter(id__in=[img_file.id, vid_file.id]).exists()

    # Cleanup
    root_folder.delete()
    user.delete()
    print("  -> Section 4 PASSED: Public sharing, reading modes & batch operations confirmed.")


def run_all_validations():
    print("=" * 70)
    print("STARTING SQUEEZED CONSOLIDATED VALIDATION SUITE")
    print("=" * 70)
    test_account_lifecycle_and_validation()
    test_account_admin_sync_and_management()
    test_storage_plans_and_admin_system()
    test_batch_operations_and_sharing()
    print("\n" + "=" * 70)
    print("ALL CONSOLIDATED FUNCTIONAL & FEATURE VALIDATIONS PASSED (100% OK)!")
    print("=" * 70)


if __name__ == '__main__':
    run_all_validations()
