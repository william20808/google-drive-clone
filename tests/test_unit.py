import os
import io
import json
import zipfile
import uuid
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from drive.models import DriveItem
from drive.utils import get_user_storage_usage, format_bytes

class GoogleDriveCloneTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create two isolated users
        self.user1 = User.objects.create_user(username='alice', email='alice@example.com', password='AlicePassword123!')
        self.user2 = User.objects.create_user(username='bob', email='bob@example.com', password='BobPassword123!')

    def test_user_registration_and_login(self):
        """Test registration and authentication flow."""
        register_url = reverse('register')
        res = self.client.post(register_url, {
            'username': 'charlie',
            'email': 'charlie@example.com',
            'password1': 'CharliePass123!',
            'password2': 'CharliePass123!',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(username='charlie').exists())

        # Test login
        login_url = reverse('login')
        res = self.client.post(login_url, {
            'username': 'alice',
            'password': 'AlicePassword123!',
        })
        self.assertEqual(res.status_code, 302)

    def test_workspace_data_isolation(self):
        """Ensure User A cannot see, access, or manipulate User B's files."""
        # Alice creates a folder and a file
        self.client.login(username='alice', password='AlicePassword123!')
        folder_a = DriveItem.objects.create(name='Alice Private Folder', is_folder=True, owner=self.user1)
        file_a = DriveItem.objects.create(
            name='alice_secrets.txt',
            is_folder=False,
            owner=self.user1,
            file_size=100,
            file=SimpleUploadedFile('alice_secrets.txt', b'Alice private data')
        )

        # Alice sees her items
        res = self.client.get(reverse('drive_root'))
        self.assertContains(res, 'Alice Private Folder')
        self.assertContains(res, 'alice_secrets.txt')

        # Bob logs in
        self.client.login(username='bob', password='BobPassword123!')

        # Bob should NOT see Alice's items in his drive
        res = self.client.get(reverse('drive_root'))
        self.assertNotContains(res, 'Alice Private Folder')
        self.assertNotContains(res, 'alice_secrets.txt')

        # Bob cannot access Alice's folder directly
        res = self.client.get(reverse('folder_view', args=[folder_a.id]))
        self.assertEqual(res.status_code, 404)

        # Bob cannot download Alice's unshared file
        res = self.client.get(reverse('download_file', args=[file_a.id]))
        self.assertEqual(res.status_code, 404)

        # Bob cannot rename Alice's file
        res = self.client.post(reverse('api_rename_item', args=[file_a.id]), {'name': 'Hacked.txt'})
        self.assertEqual(res.status_code, 404)

    def test_folder_hierarchy_and_breadcrumbs(self):
        """Test recursive infinite folder nesting and breadcrumb generation."""
        self.client.login(username='alice', password='AlicePassword123!')

        # Create Root Folder
        res = self.client.post(reverse('api_create_folder'), {'name': 'Documents'})
        self.assertEqual(res.status_code, 200)
        doc_folder = DriveItem.objects.get(name='Documents', owner=self.user1)

        # Create Nested Folder 1
        res = self.client.post(reverse('api_create_folder'), {'name': 'Work', 'parent_id': str(doc_folder.id)})
        self.assertEqual(res.status_code, 200)
        work_folder = DriveItem.objects.get(name='Work', owner=self.user1)

        # Create Nested Folder 2
        res = self.client.post(reverse('api_create_folder'), {'name': '2026', 'parent_id': str(work_folder.id)})
        self.assertEqual(res.status_code, 200)
        year_folder = DriveItem.objects.get(name='2026', owner=self.user1)

        # Check breadcrumbs of deepest folder
        crumbs = year_folder.get_breadcrumbs()
        self.assertEqual(len(crumbs), 3)
        self.assertEqual(crumbs[0]['name'], 'Documents')
        self.assertEqual(crumbs[1]['name'], 'Work')
        self.assertEqual(crumbs[2]['name'], '2026')

        # Verify duplicate folder prevention in same directory
        res = self.client.post(reverse('api_create_folder'), {'name': 'Work', 'parent_id': str(doc_folder.id)})
        self.assertEqual(res.status_code, 409)

    def test_file_upload_and_quota(self):
        """Test single and multi file uploads, mime detection, and quota check."""
        self.client.login(username='alice', password='AlicePassword123!')

        test_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 mock pdf content", content_type="application/pdf")
        res = self.client.post(reverse('api_upload_file'), {'files': [test_file]})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['name'], 'report.pdf')
        self.assertEqual(data['items'][0]['preview_type'], 'pdf')

        # Test duplicate upload appends counter: report (1).pdf
        test_file_dup = SimpleUploadedFile("report.pdf", b"%PDF-1.4 second content", content_type="application/pdf")
        res = self.client.post(reverse('api_upload_file'), {'files': [test_file_dup]})
        self.assertEqual(res.status_code, 200)
        dup_data = res.json()
        self.assertEqual(dup_data['items'][0]['name'], 'report (1).pdf')

        # Verify storage usage updated
        usage = get_user_storage_usage(self.user1)
        self.assertGreater(usage['used_bytes'], 0)

    def test_move_cycle_prevention(self):
        """Test moving files and preventing folders from moving into their own descendants."""
        self.client.login(username='alice', password='AlicePassword123!')

        folder_parent = DriveItem.objects.create(name='ParentFolder', is_folder=True, owner=self.user1)
        folder_child = DriveItem.objects.create(name='ChildFolder', is_folder=True, parent=folder_parent, owner=self.user1)
        folder_grandchild = DriveItem.objects.create(name='GrandChildFolder', is_folder=True, parent=folder_child, owner=self.user1)

        # Attempt to move folder_parent into folder_grandchild -> MUST fail with 400
        res = self.client.post(reverse('api_move_item', args=[folder_parent.id]), {
            'destination_id': str(folder_grandchild.id)
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('cannot be moved into itself or its subfolders', res.json()['error'])

        # Moving grandchild to root should succeed
        res = self.client.post(reverse('api_move_item', args=[folder_grandchild.id]), {
            'destination_id': ''
        })
        self.assertEqual(res.status_code, 200)
        folder_grandchild.refresh_from_db()
        self.assertIsNone(folder_grandchild.parent)

    def test_copy_tree_and_files(self):
        """Test recursive copying of folder trees and files."""
        self.client.login(username='alice', password='AlicePassword123!')

        folder_src = DriveItem.objects.create(name='SourceFolder', is_folder=True, owner=self.user1)
        file_inside = DriveItem.objects.create(
            name='doc.txt',
            is_folder=False,
            parent=folder_src,
            owner=self.user1,
            file_size=25,
            file=SimpleUploadedFile('doc.txt', b'Some text to copy over')
        )

        res = self.client.post(reverse('api_copy_item', args=[folder_src.id]), {
            'destination_id': ''
        })
        self.assertEqual(res.status_code, 200)

        # Verify copied folder exists
        copy_folder = DriveItem.objects.filter(name='SourceFolder (Copy)', owner=self.user1).first()
        self.assertIsNotNone(copy_folder)
        # Verify copied file exists inside copied folder
        copy_file = DriveItem.objects.filter(parent=copy_folder, owner=self.user1).first()
        self.assertIsNotNone(copy_file)
        self.assertEqual(copy_file.name, 'doc.txt')

    def test_star_and_starred_view(self):
        """Test starring items and viewing them in Starred view."""
        self.client.login(username='alice', password='AlicePassword123!')

        item = DriveItem.objects.create(name='StarredDoc.pdf', is_folder=False, owner=self.user1)
        res = self.client.post(reverse('api_toggle_star', args=[item.id]))
        self.assertEqual(res.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_starred)

        res = self.client.get(reverse('starred_view'))
        self.assertContains(res, 'StarredDoc.pdf')

    def test_trash_restore_and_permanent_delete(self):
        """Test moving to bin, restoring, and permanent deletion with physical file removal."""
        self.client.login(username='alice', password='AlicePassword123!')

        uploaded = SimpleUploadedFile('remove_me.png', b'mock image data')
        file_item = DriveItem.objects.create(
            name='remove_me.png',
            is_folder=False,
            owner=self.user1,
            file_size=15,
            file=uploaded
        )
        physical_path = file_item.file.path
        self.assertTrue(os.path.exists(physical_path))

        # 1. Soft-delete
        res = self.client.post(reverse('api_trash_item', args=[file_item.id]))
        self.assertEqual(res.status_code, 200)
        file_item.refresh_from_db()
        self.assertTrue(file_item.is_trashed)

        # Verify not in My Drive, but in Trash view
        res = self.client.get(reverse('drive_root'))
        self.assertNotContains(res, 'remove_me.png')
        res = self.client.get(reverse('trash_view'))
        self.assertContains(res, 'remove_me.png')

        # 2. Restore
        res = self.client.post(reverse('api_restore_item', args=[file_item.id]))
        self.assertEqual(res.status_code, 200)
        file_item.refresh_from_db()
        self.assertFalse(file_item.is_trashed)

        # 3. Permanent delete
        res = self.client.post(reverse('api_delete_permanent', args=[file_item.id]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(DriveItem.objects.filter(id=file_item.id).exists())
        # Verify physical file is gone
        self.assertFalse(os.path.exists(physical_path))

    def test_public_file_sharing_anonymous_and_authenticated(self):
        """Test public file sharing with anonymous visitors and other logged-in users."""
        self.client.login(username='alice', password='AlicePassword123!')

        file_item = DriveItem.objects.create(
            name='Quarterly_Report.pdf',
            is_folder=False,
            owner=self.user1,
            file_size=64,
            mime_type='application/pdf',
            file_extension='pdf',
            file=SimpleUploadedFile('Quarterly_Report.pdf', b'%PDF-1.4 Fake PDF Content')
        )

        # 1. Alice enables public sharing
        res = self.client.post(reverse('api_share_settings', args=[file_item.id]), {'is_shared': 'true'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['is_shared'])
        self.assertTrue(bool(data['share_url']))

        file_item.refresh_from_db()
        share_token = file_item.share_token
        share_url = reverse('share_view', args=[share_token])

        # 2. Anonymous client accesses public share page
        anon_client = Client()
        res_anon = anon_client.get(share_url)
        self.assertEqual(res_anon.status_code, 200)
        self.assertContains(res_anon, 'Quarterly_Report.pdf')
        self.assertContains(res_anon, 'Shared by')
        self.assertContains(res_anon, 'Download')

        # Anonymous client downloads file
        dl_url = reverse('download_file', args=[file_item.id])
        res_dl = anon_client.get(dl_url)
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl.getvalue(), b'%PDF-1.4 Fake PDF Content')

        # 3. Another authenticated user (Bob) accesses the share link
        bob_client = Client()
        bob_client.login(username='bob', password='BobPassword123!')
        res_bob = bob_client.get(share_url)
        self.assertEqual(res_bob.status_code, 200)
        # Must display the item name and NOT be a blank page!
        self.assertContains(res_bob, 'Quarterly_Report.pdf')
        self.assertContains(res_bob, 'Save to My Drive')

        # Bob saves a copy to his own drive
        save_copy_url = reverse('api_save_shared_copy', args=[file_item.id])
        res_save = bob_client.post(save_copy_url)
        self.assertEqual(res_save.status_code, 200)
        self.assertTrue(res_save.json()['success'])

        # Verify Bob now has this file in his own drive
        bob_copies = DriveItem.objects.filter(owner=self.user2, name='Quarterly_Report.pdf', is_trashed=False)
        self.assertEqual(bob_copies.count(), 1)
        self.assertEqual(bob_copies.first().file.read(), b'%PDF-1.4 Fake PDF Content')

    def test_folder_sharing_hierarchy(self):
        """Test sharing a folder and accessing files inside the shared folder."""
        self.client.login(username='alice', password='AlicePassword123!')

        folder = DriveItem.objects.create(
            name='Shared_Project_Folder',
            is_folder=True,
            owner=self.user1
        )
        child_file = DriveItem.objects.create(
            name='Spec.txt',
            is_folder=False,
            owner=self.user1,
            parent=folder,
            file_size=20,
            file=SimpleUploadedFile('Spec.txt', b'Project specifications')
        )

        # Enable sharing on the folder
        res = self.client.post(reverse('api_share_settings', args=[folder.id]), {'is_shared': 'true'})
        self.assertEqual(res.status_code, 200)
        folder.refresh_from_db()

        # Anonymous client accesses shared folder page
        anon_client = Client()
        res_folder = anon_client.get(reverse('share_view', args=[folder.share_token]))
        self.assertEqual(res_folder.status_code, 200)
        self.assertContains(res_folder, 'Shared_Project_Folder')
        self.assertContains(res_folder, 'Spec.txt')

        # Anonymous client downloads child file inside the shared folder
        res_dl = anon_client.get(reverse('download_file', args=[child_file.id]))
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl.getvalue(), b'Project specifications')

        # Other logged-in user (Bob) accesses shared folder
        bob_client = Client()
        bob_client.login(username='bob', password='BobPassword123!')
        res_bob_folder = bob_client.get(reverse('share_view', args=[folder.share_token]))
        self.assertEqual(res_bob_folder.status_code, 200)
        self.assertContains(res_bob_folder, 'Shared_Project_Folder')
        self.assertContains(res_bob_folder, 'Spec.txt')

    def test_sharing_revocation_and_trash_protection(self):
        """Test that disabling sharing or trashing an item immediately blocks public access."""
        self.client.login(username='alice', password='AlicePassword123!')

        file_item = DriveItem.objects.create(
            name='Secret.txt',
            is_folder=False,
            owner=self.user1,
            file_size=10,
            file=SimpleUploadedFile('Secret.txt', b'Secret data')
        )

        # Share then revoke
        self.client.post(reverse('api_share_settings', args=[file_item.id]), {'is_shared': 'true'})
        file_item.refresh_from_db()
        token = file_item.share_token

        # Revoke
        self.client.post(reverse('api_share_settings', args=[file_item.id]), {'is_shared': 'false'})
        file_item.refresh_from_db()
        self.assertFalse(file_item.is_shared)

        anon_client = Client()
        res_revoked = anon_client.get(reverse('share_view', args=[token]))
        self.assertEqual(res_revoked.status_code, 404)

        res_dl_blocked = anon_client.get(reverse('download_file', args=[file_item.id]))
        self.assertEqual(res_dl_blocked.status_code, 404)

        # Re-share and trash
        self.client.post(reverse('api_share_settings', args=[file_item.id]), {'is_shared': 'true'})
        file_item.refresh_from_db()
        token2 = file_item.share_token

        self.client.post(reverse('api_trash_item', args=[file_item.id]))
        res_trashed = anon_client.get(reverse('share_view', args=[token2]))
        self.assertEqual(res_trashed.status_code, 404)

    def test_instant_search_api(self):
        """Test instant search autocomplete API endpoint."""
        self.client.login(username='alice', password='AlicePassword123!')

        doc = DriveItem.objects.create(name='Annual_Report_2026.pdf', file_extension='pdf', is_folder=False, owner=self.user1)
        img = DriveItem.objects.create(name='Vacation_Photo.jpg', file_extension='jpg', is_folder=False, owner=self.user1)
        folder = DriveItem.objects.create(name='Reports_Folder', is_folder=True, owner=self.user1)

        # Bob's file (should never appear in Alice's search)
        DriveItem.objects.create(name='Bob_Confidential_Report.pdf', file_extension='pdf', is_folder=False, owner=self.user2)

        # Search with query 'Report'
        res = self.client.get(reverse('api_instant_search') + '?q=Report')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        names = [r['name'] for r in data['results']]
        self.assertIn('Annual_Report_2026.pdf', names)
        self.assertIn('Reports_Folder', names)
        self.assertNotIn('Vacation_Photo.jpg', names)
        self.assertNotIn('Bob_Confidential_Report.pdf', names)

        # Empty query returns recent items
        res_empty = self.client.get(reverse('api_instant_search'))
        self.assertEqual(res_empty.status_code, 200)
        self.assertGreaterEqual(res_empty.json()['count'], 3)

    def test_search_and_category_filtering(self):
        """Test search query and category filtering."""
        self.client.login(username='alice', password='AlicePassword123!')

        DriveItem.objects.create(name='Invoice_2026.pdf', file_extension='pdf', is_folder=False, owner=self.user1)
        DriveItem.objects.create(name='Family_Vacation.png', file_extension='png', is_folder=False, owner=self.user1)
        DriveItem.objects.create(name='Tutorial.mp4', file_extension='mp4', is_folder=False, owner=self.user1)

        # Category filter: documents
        res = self.client.get(reverse('drive_root') + '?category=documents')
        self.assertContains(res, 'Invoice_2026.pdf')
        self.assertNotContains(res, 'Family_Vacation.png')

        # Category filter: images
        res = self.client.get(reverse('drive_root') + '?category=images')
        self.assertContains(res, 'Family_Vacation.png')
        self.assertNotContains(res, 'Invoice_2026.pdf')

        # Search query
        res = self.client.get(reverse('drive_root') + '?q=Invoice')
        self.assertContains(res, 'Invoice_2026.pdf')
        self.assertNotContains(res, 'Family_Vacation.png')

    def test_empty_trash_endpoint(self):
        """Test the empty trash API endpoint removes all trashed items permanently."""
        self.client.login(username='alice', password='AlicePassword123!')

        DriveItem.objects.create(name='trash1.txt', is_trashed=True, owner=self.user1)
        DriveItem.objects.create(name='trash2.txt', is_trashed=True, owner=self.user1)
        DriveItem.objects.create(name='keep_me.txt', is_trashed=False, owner=self.user1)

        res = self.client.post(reverse('api_empty_trash'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(DriveItem.objects.filter(owner=self.user1, is_trashed=True).count(), 0)
        self.assertEqual(DriveItem.objects.filter(owner=self.user1, is_trashed=False).count(), 1)

    def test_available_destination_folders_api(self):
        """Test the available folders endpoint excludes item and its descendants."""
        self.client.login(username='alice', password='AlicePassword123!')

        parent = DriveItem.objects.create(name='RootF', is_folder=True, owner=self.user1)
        child = DriveItem.objects.create(name='ChildF', is_folder=True, parent=parent, owner=self.user1)
        other = DriveItem.objects.create(name='OtherF', is_folder=True, owner=self.user1)

        res = self.client.get(reverse('api_available_folders_filtered', args=[parent.id]))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        folder_names = [f['name'] for f in data['folders']]
        self.assertIn('My Drive (Root)', folder_names)
        self.assertIn('OtherF', folder_names)
        self.assertNotIn('RootF', folder_names)
        self.assertNotIn('ChildF', folder_names)

    def test_shared_folder_subfolder_navigation_and_breadcrumbs(self):
        """
        Rigorously test shared folder subfolder traversal, breadcrumbs,
        ancestor validation, and ZIP archive download.
        """
        self.client.login(username='alice', password='AlicePassword123!')

        root_folder = DriveItem.objects.create(name='Public Master Folder', is_folder=True, owner=self.user1)
        sub_folder = DriveItem.objects.create(name='Subfolder Level 1', is_folder=True, parent=root_folder, owner=self.user1)
        DriveItem.objects.create(
            name='nested_doc.txt',
            is_folder=False,
            parent=sub_folder,
            owner=self.user1,
            file=SimpleUploadedFile('nested_doc.txt', b'Nested document data'),
            file_size=20
        )

        # Share root folder
        res_share = self.client.post(reverse('api_share_settings', args=[root_folder.id]), {'is_shared': 'true'})
        self.assertEqual(res_share.status_code, 200)
        root_folder.refresh_from_db()
        token = root_folder.share_token
        self.assertTrue(root_folder.is_shared)
        self.assertTrue(bool(token))

        # Anonymous visitor opens root shared folder
        anon = Client()
        res_root = anon.get(reverse('share_view', args=[token]))
        self.assertEqual(res_root.status_code, 200)
        self.assertContains(res_root, 'Public Master Folder')
        self.assertContains(res_root, 'Subfolder Level 1')
        self.assertContains(res_root, f'?subfolder={sub_folder.id}')

        # Anonymous visitor navigates into subfolder via ?subfolder=<uuid>
        res_sub = anon.get(f"{reverse('share_view', args=[token])}?subfolder={sub_folder.id}")
        self.assertEqual(res_sub.status_code, 200)
        self.assertContains(res_sub, 'Subfolder Level 1')
        self.assertContains(res_sub, 'nested_doc.txt')
        self.assertContains(res_sub, 'modal_share_folder_preview')

        # Test ancestor security: an unrelated folder ID should not expose foreign folders
        unrelated_folder = DriveItem.objects.create(name='Bob Secret Folder', is_folder=True, owner=self.user2)
        res_hack = anon.get(f"{reverse('share_view', args=[token])}?subfolder={unrelated_folder.id}")
        self.assertEqual(res_hack.status_code, 200)
        self.assertNotContains(res_hack, 'Bob Secret Folder')
        self.assertContains(res_hack, 'Public Master Folder')

        # Test download shared folder as ZIP
        res_zip = anon.get(reverse('share_folder_download_zip', args=[token]))
        self.assertEqual(res_zip.status_code, 200)
        self.assertEqual(res_zip['Content-Type'], 'application/zip')
        buf = io.BytesIO(b''.join(res_zip.streaming_content))
        with zipfile.ZipFile(buf, 'r') as zf:
            files_in_zip = zf.namelist()
            self.assertTrue(any('nested_doc.txt' in f for f in files_in_zip))

    def test_pdf_photo_video_reading_mode_rendering(self):
        """
        Rigorously test dedicated reading mode for shared PDFs,
        photo controls for images, and video controls for videos.
        """
        self.client.login(username='alice', password='AlicePassword123!')

        # PDF file
        pdf_file = DriveItem.objects.create(
            name='Manual.pdf',
            is_folder=False,
            owner=self.user1,
            file_extension='pdf',
            mime_type='application/pdf',
            file=SimpleUploadedFile('Manual.pdf', b'%PDF-1.4 Mock PDF Content'),
            file_size=25
        )
        self.client.post(reverse('api_share_settings', args=[pdf_file.id]), {'is_shared': 'true'})
        pdf_file.refresh_from_db()

        # Image file
        img_file = DriveItem.objects.create(
            name='Artwork.png',
            is_folder=False,
            owner=self.user1,
            file_extension='png',
            mime_type='image/png',
            file=SimpleUploadedFile('Artwork.png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'),
            file_size=16
        )
        self.client.post(reverse('api_share_settings', args=[img_file.id]), {'is_shared': 'true'})
        img_file.refresh_from_db()

        # Video file
        vid_file = DriveItem.objects.create(
            name='Clip.mp4',
            is_folder=False,
            owner=self.user1,
            file_extension='mp4',
            mime_type='video/mp4',
            file=SimpleUploadedFile('Clip.mp4', b'\x00\x00\x00\x18ftypmp42'),
            file_size=12
        )
        self.client.post(reverse('api_share_settings', args=[vid_file.id]), {'is_shared': 'true'})
        vid_file.refresh_from_db()

        anon = Client()

        # Verify PDF Reading Mode UI elements
        res_pdf = anon.get(reverse('share_view', args=[pdf_file.share_token]))
        self.assertEqual(res_pdf.status_code, 200)
        self.assertContains(res_pdf, 'PDF Reading Mode')
        self.assertContains(res_pdf, 'zoomPdf')
        self.assertContains(res_pdf, 'printDocument')
        self.assertContains(res_pdf, 'pdf-reading-iframe')

        # Verify Photo Mode UI elements
        res_img = anon.get(reverse('share_view', args=[img_file.share_token]))
        self.assertEqual(res_img.status_code, 200)
        self.assertContains(res_img, 'rotateImage')
        self.assertContains(res_img, 'zoomImage')
        self.assertContains(res_img, 'share-preview-img')

        # Verify Video Mode UI elements
        res_vid = anon.get(reverse('share_view', args=[vid_file.share_token]))
        self.assertEqual(res_vid.status_code, 200)
        self.assertContains(res_vid, 'setVideoSpeed')
        self.assertContains(res_vid, 'share-video-player')

    def test_batch_operations_api_suite(self):
        """
        Rigorously test batch operations: batch star, batch move, batch zip download,
        batch trash, batch restore, batch permanent delete, and user security isolation.
        """
        self.client.login(username='alice', password='AlicePassword123!')

        f1 = DriveItem.objects.create(name='Doc1.txt', is_folder=False, owner=self.user1, file=SimpleUploadedFile('Doc1.txt', b'Doc 1'), file_size=5)
        f2 = DriveItem.objects.create(name='Doc2.txt', is_folder=False, owner=self.user1, file=SimpleUploadedFile('Doc2.txt', b'Doc 2'), file_size=5)
        dest_folder = DriveItem.objects.create(name='ArchiveFolder', is_folder=True, owner=self.user1)

        # 1. Batch Star
        res_star = self.client.post(reverse('api_batch_star'), json.dumps({
            'item_ids': [str(f1.id), str(f2.id)],
            'action': 'star'
        }), content_type='application/json')
        self.assertEqual(res_star.status_code, 200)
        f1.refresh_from_db()
        f2.refresh_from_db()
        self.assertTrue(f1.is_starred)
        self.assertTrue(f2.is_starred)

        # 2. Batch Move
        res_move = self.client.post(reverse('api_batch_move'), json.dumps({
            'item_ids': [str(f1.id), str(f2.id)],
            'destination_id': str(dest_folder.id)
        }), content_type='application/json')
        self.assertEqual(res_move.status_code, 200)
        f1.refresh_from_db()
        f2.refresh_from_db()
        self.assertEqual(f1.parent_id, dest_folder.id)
        self.assertEqual(f2.parent_id, dest_folder.id)

        # 3. Batch Download ZIP
        res_zip = self.client.get(f"{reverse('api_batch_download_zip')}?item_ids={f1.id}&item_ids={f2.id}")
        self.assertEqual(res_zip.status_code, 200)
        self.assertEqual(res_zip['Content-Type'], 'application/zip')
        buf = io.BytesIO(b''.join(res_zip.streaming_content))
        with zipfile.ZipFile(buf, 'r') as zf:
            self.assertIn('Doc1.txt', zf.namelist())
            self.assertIn('Doc2.txt', zf.namelist())

        # 4. Batch Trash
        res_trash = self.client.post(reverse('api_batch_trash'), json.dumps({
            'item_ids': [str(f1.id), str(f2.id)]
        }), content_type='application/json')
        self.assertEqual(res_trash.status_code, 200)
        f1.refresh_from_db()
        f2.refresh_from_db()
        self.assertTrue(f1.is_trashed)
        self.assertTrue(f2.is_trashed)

        # 5. Batch Restore
        res_restore = self.client.post(reverse('api_batch_restore'), json.dumps({
            'item_ids': [str(f1.id), str(f2.id)]
        }), content_type='application/json')
        self.assertEqual(res_restore.status_code, 200)
        f1.refresh_from_db()
        f2.refresh_from_db()
        self.assertFalse(f1.is_trashed)
        self.assertFalse(f2.is_trashed)

        # 6. Security Isolation: Bob cannot batch delete Alice's items
        bob_client = Client()
        bob_client.login(username='bob', password='BobPassword123!')
        res_bob_hack = bob_client.post(reverse('api_batch_delete'), json.dumps({
            'item_ids': [str(f1.id), str(f2.id)]
        }), content_type='application/json')
        self.assertEqual(res_bob_hack.status_code, 200)
        # Alice's items must NOT have been deleted
        self.assertTrue(DriveItem.objects.filter(id=f1.id).exists())
        self.assertTrue(DriveItem.objects.filter(id=f2.id).exists())

        # 7. Batch Delete by Alice
        res_del = self.client.post(reverse('api_batch_delete'), json.dumps({
            'item_ids': [str(f1.id), str(f2.id)]
        }), content_type='application/json')
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(DriveItem.objects.filter(id=f1.id).exists())
        self.assertFalse(DriveItem.objects.filter(id=f2.id).exists())

    def test_full_preview_alignment_suite(self):
        """
        Verify that all preview types (PDF, Photo, Video, Audio, Text, Code, CSV, Markdown)
        are fully supported and aligned between public share links and in-app drive modals.
        """
        self.client.login(username='alice', password='AlicePassword123!')

        # 1. Verify Model Preview Types
        csv_item = DriveItem.objects.create(
            name='sales_data.csv',
            is_folder=False,
            owner=self.user1,
            file_extension='csv',
            mime_type='text/csv',
            file=SimpleUploadedFile('sales_data.csv', b'Year,Revenue,Profit\n2025,100000,25000\n2026,150000,45000\n'),
            file_size=65
        )
        md_item = DriveItem.objects.create(
            name='GUIDE.md',
            is_folder=False,
            owner=self.user1,
            file_extension='md',
            mime_type='text/markdown',
            file=SimpleUploadedFile('GUIDE.md', b'# Getting Started\n\nWelcome to **Google Drive** clone!\n- Fast\n- Secure\n'),
            file_size=75
        )
        py_item = DriveItem.objects.create(
            name='script.py',
            is_folder=False,
            owner=self.user1,
            file_extension='py',
            mime_type='text/x-python',
            file=SimpleUploadedFile('script.py', b'def hello():\n    print("Hello Drive")\n'),
            file_size=40
        )
        audio_item = DriveItem.objects.create(
            name='podcast.mp3',
            is_folder=False,
            owner=self.user1,
            file_extension='mp3',
            mime_type='audio/mpeg',
            file=SimpleUploadedFile('podcast.mp3', b'ID3MockAudioData'),
            file_size=16
        )

        self.assertEqual(csv_item.preview_type, 'text')
        self.assertEqual(md_item.preview_type, 'text')
        self.assertEqual(py_item.preview_type, 'text')
        self.assertEqual(audio_item.preview_type, 'audio')

        # Share items publicly
        for it in [csv_item, md_item, py_item, audio_item]:
            self.client.post(reverse('api_share_settings', args=[it.id]), {'is_shared': 'true'})
            it.refresh_from_db()

        anon = Client()

        # 2. Test CSV Direct Share View
        res_csv = anon.get(reverse('share_view', args=[csv_item.share_token]))
        self.assertEqual(res_csv.status_code, 200)
        self.assertContains(res_csv, 'sales_data.csv')
        self.assertContains(res_csv, 'direct_text_view_tabs')
        self.assertContains(res_csv, 'renderCsvTableHtml')
        self.assertContains(res_csv, 'direct-text-code-body')
        self.assertContains(res_csv, 'copyTextToClipboard')
        self.assertContains(res_csv, 'adjustTextFontSize')

        # 3. Test Markdown Direct Share View
        res_md = anon.get(reverse('share_view', args=[md_item.share_token]))
        self.assertEqual(res_md.status_code, 200)
        self.assertContains(res_md, 'GUIDE.md')
        self.assertContains(res_md, 'renderSimpleMarkdownHtml')
        self.assertContains(res_md, 'direct_text_view_tabs')

        # 4. Test Python Code Direct Share View
        res_py = anon.get(reverse('share_view', args=[py_item.share_token]))
        self.assertEqual(res_py.status_code, 200)
        self.assertContains(res_py, 'script.py')
        self.assertContains(res_py, 'toggleTextWordWrap')
        self.assertContains(res_py, 'adjustTextFontSize')
        self.assertContains(res_py, 'direct-text-code-body')

        # 5. Test Audio Direct Share View
        res_audio = anon.get(reverse('share_view', args=[audio_item.share_token]))
        self.assertEqual(res_audio.status_code, 200)
        self.assertContains(res_audio, 'podcast.mp3')
        self.assertContains(res_audio, 'share-audio-player')
        self.assertContains(res_audio, 'setAudioSpeed')

        # 6. Test Shared Folder containing Text, CSV, Code, and Audio
        folder = DriveItem.objects.create(name='ProjectFolder', is_folder=True, owner=self.user1)
        csv_item.parent = folder
        csv_item.save()
        md_item.parent = folder
        md_item.save()
        py_item.parent = folder
        py_item.save()
        audio_item.parent = folder
        audio_item.save()

        self.client.post(reverse('api_share_settings', args=[folder.id]), {'is_shared': 'true'})
        folder.refresh_from_db()

        res_folder = anon.get(reverse('share_view', args=[folder.share_token]))
        self.assertEqual(res_folder.status_code, 200)
        self.assertContains(res_folder, 'sales_data.csv')
        self.assertContains(res_folder, 'GUIDE.md')
        self.assertContains(res_folder, 'script.py')
        self.assertContains(res_folder, 'podcast.mp3')
        # Check that folder preview modal includes text preview handler
        self.assertContains(res_folder, 'openShareFilePreview')
        self.assertContains(res_folder, 'setSfTextViewMode')
        self.assertContains(res_folder, 'modal_share_folder_preview')



