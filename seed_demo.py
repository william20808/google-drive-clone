"""
Database Seed & Clean State Script
Initializes the database to a clean, production-ready state with:
- Exactly two users: 'demo' (DemoPassword123!) and 'admin' (AdminPassword123!)
- All other users deleted
- All existing DriveItems removed
- Media directory cleaned of orphan files
- Exactly 5 ultra-lightweight showcase files (< 20 KB total):
    1. Getting_Started_Guide.pdf (~1 KB)
    2. Google_Drive_Banner.png (~3 KB)
    3. Welcome_Notes.txt (~0.5 KB)
    4. Project_Roadmap.csv (~0.3 KB)
    5. Sample_Video.mp4 (~13.7 KB)
"""

import os
import sys
import shutil
import urllib.request
import io
from PIL import Image, ImageDraw

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gdrive_project.settings')
import django
django.setup()

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from drive.models import DriveItem, UserProfile


def generate_minimal_pdf():
    """Generates a valid, ultra-lightweight PDF 1.4 document."""
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"5 0 obj\n<< /Length 260 >>\nstream\n"
        b"BT\n"
        b"/F1 22 Tf\n"
        b"50 720 Td\n"
        b"(Google Drive Clone - Welcome Guide) Tj\n"
        b"/F1 12 Tf\n"
        b"0 -36 Td\n"
        b"(This document demonstrates the dedicated PDF Reading Mode.) Tj\n"
        b"0 -22 Td\n"
        b"(Features available: Zoom In, Zoom Out, Fit to Page, and Instant Print.) Tj\n"
        b"0 -22 Td\n"
        b"(Ultra-lightweight vector PDF ideal for GitHub deployment.) Tj\n"
        b"ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000242 00000 n \n"
        b"0000000318 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n632\n%%EOF\n"
    )
    return pdf_bytes


def generate_minimal_png():
    """Generates a sharp, lightweight modern banner PNG using Pillow."""
    img = Image.new('RGB', (480, 270), color='#1a73e8')
    draw = ImageDraw.Draw(img)

    # Decorative geometric patterns
    draw.rectangle([12, 12, 468, 258], outline='#ffffff', width=2)
    draw.ellipse([190, 65, 290, 165], fill='#ffffff')
    draw.ellipse([205, 80, 275, 150], fill='#1a73e8')
    draw.polygon([(240, 95), (265, 135), (215, 135)], fill='#ffffff')

    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def get_minimal_mp4():
    """Fetches the official W3C web-platform-tests 13KB sample MP4 video."""
    url = "https://raw.githubusercontent.com/web-platform-tests/wpt/master/media/white.mp4"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as res:
            return res.read()
    except Exception as e:
        print(f"Note: Online video fetch skipped ({e}), using valid fallback container.")
        # Minimal valid MP4 container fallback
        return b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x08free\x00\x00\x00\x08mdat"


def seed():
    print("=" * 60)
    print("STARTING DATABASE RESET & SEEDING")
    print("=" * 60)

    # 1. Clean Users - retain only 'demo' and 'admin'
    deleted_users, _ = User.objects.exclude(username__in=['demo', 'admin']).delete()
    print(f"1. Removed non-essential users: {deleted_users} deleted.")

    # Configure 'demo'
    demo_user, _ = User.objects.get_or_create(username='demo')
    demo_user.email = 'demo@example.com'
    demo_user.first_name = 'Demo'
    demo_user.last_name = 'User'
    demo_user.is_staff = False
    demo_user.is_superuser = False
    demo_user.set_password('DemoPassword123!')
    demo_user.save()
    UserProfile.objects.get_or_create(user=demo_user, defaults={'storage_plan': '15GB'})
    print(f"   Configured demo user: '{demo_user.username}' (password: DemoPassword123!)")

    # Configure 'admin'
    admin_user, _ = User.objects.get_or_create(username='admin')
    admin_user.email = 'admin@gmail.com'
    admin_user.first_name = 'Admin'
    admin_user.last_name = 'Administrator'
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.set_password('AdminPassword123!')
    admin_user.save()
    UserProfile.objects.get_or_create(user=admin_user, defaults={'storage_plan': '15GB'})
    print(f"   Configured admin user: '{admin_user.username}' (password: AdminPassword123!)")

    # 2. Clean DriveItem table completely
    deleted_items, _ = DriveItem.objects.all().delete()
    print(f"2. Cleared existing database files/folders ({deleted_items} items deleted).")

    # 3. Clean media/uploads directory
    media_uploads = os.path.join(BASE_DIR, 'media', 'uploads')
    if os.path.exists(media_uploads):
        for entry in os.listdir(media_uploads):
            if entry == '.gitkeep':
                continue
            entry_path = os.path.join(media_uploads, entry)
            if os.path.isdir(entry_path):
                shutil.rmtree(entry_path, ignore_errors=True)
            else:
                try:
                    os.remove(entry_path)
                except OSError:
                    pass
    print("3. Cleaned media/uploads directory.")

    # 4. Generate & Save Exactly 5 Lightweight Showcase Files for both 'demo' and 'admin'
    print("4. Generating showcase files for both 'demo' and 'admin'...")

    pdf_data = generate_minimal_pdf()
    png_data = generate_minimal_png()
    txt_content = (
        "Google Drive Clone - Welcome Notes\n"
        "===================================\n\n"
        "Welcome to your personal cloud storage application!\n\n"
        "Key Capabilities:\n"
        "- Zero-lag Theme Switcher (Light & Dark mode)\n"
        "- File upload with drag-and-drop overlay\n"
        "- Multi-format previews (PDF Reading Mode, Photo Zoom/Rotate, Video Player, CSV Table Viewer)\n"
        "- Nested folder creation, renaming, and in-memory fast traversal\n"
        "- Multi-item selection: star, move, trash, restore, delete, download as ZIP\n"
        "- Public token sharing for both files and folder subtrees\n"
        "- Quota and storage plan management (15GB, 100GB, 500GB)\n"
    ).encode('utf-8')
    csv_content = (
        "Project Milestone,Category,Assigned To,Status,Quarter\n"
        "Architecture Setup,Engineering,Team,Completed,2026-Q1\n"
        "Modern Responsive UI,Frontend,Team,Completed,2026-Q1\n"
        "Dedicated Reading Modes,Features,Team,Completed,2026-Q2\n"
        "Database Indexing & Caching,Performance,Team,Completed,2026-Q2\n"
        "GitHub Deployment & Delivery,DevOps,Team,In Progress,2026-Q3\n"
    ).encode('utf-8')
    mp4_data = get_minimal_mp4()

    def seed_files_for_user(target_user):
        print(f"   -> Seeding files for '{target_user.username}'...")
        # 1. PDF
        item_pdf = DriveItem(
            owner=target_user,
            name='Getting_Started_Guide.pdf',
            is_folder=False,
            file_size=len(pdf_data),
            mime_type='application/pdf',
            file_extension='pdf',
            is_starred=True,
        )
        item_pdf.file.save('Getting_Started_Guide.pdf', ContentFile(pdf_data), save=True)

        # 2. Photo
        item_png = DriveItem(
            owner=target_user,
            name='Google_Drive_Banner.png',
            is_folder=False,
            file_size=len(png_data),
            mime_type='image/png',
            file_extension='png',
            is_starred=True,
        )
        item_png.file.save('Google_Drive_Banner.png', ContentFile(png_data), save=True)

        # 3. TXT
        item_txt = DriveItem(
            owner=target_user,
            name='Welcome_Notes.txt',
            is_folder=False,
            file_size=len(txt_content),
            mime_type='text/plain',
            file_extension='txt',
        )
        item_txt.file.save('Welcome_Notes.txt', ContentFile(txt_content), save=True)

        # 4. CSV
        item_csv = DriveItem(
            owner=target_user,
            name='Project_Roadmap.csv',
            is_folder=False,
            file_size=len(csv_content),
            mime_type='text/csv',
            file_extension='csv',
        )
        item_csv.file.save('Project_Roadmap.csv', ContentFile(csv_content), save=True)

        # 5. Video
        item_mp4 = DriveItem(
            owner=target_user,
            name='Sample_Video.mp4',
            is_folder=False,
            file_size=len(mp4_data),
            mime_type='video/mp4',
            file_extension='mp4',
        )
        item_mp4.file.save('Sample_Video.mp4', ContentFile(mp4_data), save=True)
        print(f"      Seeded 5 documents for '{target_user.username}' successfully.")

    seed_files_for_user(demo_user)
    seed_files_for_user(admin_user)

    total_single = len(pdf_data) + len(png_data) + len(txt_content) + len(csv_content) + len(mp4_data)
    print(f"\nTotal media size per user: {total_single / 1024:.2f} KB | Total combined (10 files): {(total_single * 2) / 1024:.2f} KB")
    print("=" * 60)
    print("DATABASE RESET & SEED COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == '__main__':
    seed()
