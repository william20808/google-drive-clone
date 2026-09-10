# Google Drive Clone (Django Full-Stack)

A modern, high-performance, single-port Google Drive web application built with **Python 3**, **Django 5**, and a sleek **Tailwind CSS / DaisyUI** interface. Designed for CS50W (Web Programming with Python and JavaScript) as a complete cloud storage and document preview platform.

> **🙏 Attribution & Project Citation:** All core UI/UX concepts and foundational ideas are inspired by and credited to the open-source [Google Drive Clone by Ezeibekwe Emmanuel](https://github.com/EzeibekweEmma/google-drive-clone). This project honors that original design while completely rewriting the stack from React / Next.js / Prisma into a Python / Django 5 monolith, adding multi-format reading suites, batch operations, tiered quotas, and backend performance optimizations. See [Attribution & Acknowledgments](#-attribution-inspiration--original-project-citation) for full details.

---

## 🌟 Key Features

### 1. Multi-Format Reading & Preview Engines
- **PDF Reading Mode**: Dedicated high-productivity reading mode featuring interactive zoom (50% to 200%), fit-to-width, document printing, and responsive canvas thumbnail generation.
- **Photo & Graphic Viewer**: Smooth image preview modal equipped with lossless rotation (90-degree steps) and granular zoom controls.
- **HTML5 Video Player**: Clean video player supporting variable playback speeds (0.5x, 1x, 1.25x, 1.5x, 2x) with responsive sizing.
- **Interactive CSV Table Viewer**: Parses delimited tabular data directly into a searchable, scrollable spreadsheet-style grid.
- **Text & Code Viewer**: Monospace text rendering with font size adjustments, word-wrap toggling, and one-click clipboard copying.

### 2. File & Folder Lifecycle Management
- **Drag-and-Drop Uploads**: Drag multiple files anywhere onto the screen to trigger an animated upload dropzone.
- **Nested Folder Hierarchies**: Unlimited folder depth with breadcrumb navigation and recursive folder tree navigation.
- **Multi-Item Batch Selection**: Select multiple items with Ctrl/Cmd or checkboxes to perform batch actions:
  - Batch Star / Unstar
  - Batch Move to any destination folder
  - Batch Trash & Batch Restore
  - Batch Permanent Delete (with storage reclaim)
  - Batch Download as compressed `.zip` archive
- **Instant Search & Autocomplete**: Real-time search dropdown showing matches across all folders with direct navigation.
- **Zero-Lag Theme Switcher**: Instant transition-optimized Dark Mode & Light Mode switcher using `data-theme` persistence.

### 3. Sharing & Public Collaboration
- **Tokenized Public Links**: Share files or complete folder trees securely via unique cryptographic URL tokens without exposing internal IDs.
- **Anonymous Folder Browsing**: Unauthenticated recipients can browse shared folders, traverse nested subfolders via breadcrumbs, and download the entire tree as a ZIP file.

### 4. Storage Quotas & Admin Console
- **Tiered Storage Plans**: Free 15 GB, 100 GB, and 500 GB plans with dynamic progress bars and modal contact prompts.
- **Custom Admin Console**: Modern Google Drive branded Django Admin interface (`/admin/`) with integrated `UserProfileInline` to configure user quotas and account properties.

---

## 📦 Ultra-Lightweight Showcase Media (< 20 KB)

To ensure rapid GitHub deployment, fast clone times, and minimal repository weight, this project includes exactly **5 lightweight showcase files** totaling only **~16.5 KB**:

| File Name | Format | Size | Showcase Feature |
| :--- | :--- | :--- | :--- |
| `Getting_Started_Guide.pdf` | PDF Document | ~850 B | Demonstrates PDF Reading Mode, Zoom & Print |
| `Google_Drive_Banner.png` | PNG Image | ~1.4 KB | Demonstrates Photo Viewer & Rotation |
| `Welcome_Notes.txt` | Plain Text | ~580 B | Demonstrates Text Mode & Clipboard Copying |
| `Project_Roadmap.csv` | Tabular Data | ~366 B | Demonstrates Interactive CSV Table Grid |
| `Sample_Video.mp4` | MP4 Video (W3C WPT) | ~13.7 KB | Demonstrates HTML5 Video Player & Speeds |

---

## 🔐 Default Showcase Credentials

For testing and grading, the database comes pre-seeded with two standardized accounts:

| Account Role | Username | Password | Purpose & Access |
| :--- | :--- | :--- | :--- |
| **Demo User** | `demo` | `DemoPassword123!` | Standard user with the 5 pre-loaded showcase files in their drive |
| **Administrator** | `admin` | `AdminPassword123!` | Superuser with the 5 showcase files in their drive + full Django Admin Console access (`/admin/`) |

> **Security Note:** Both `demo` and `admin` accounts have identical copies of the 5 showcase documents in their individual drives. Login forms do not contain hardcoded or pre-filled credentials. Enter the credentials manually on the sign-in page.

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **Git**

### Step-by-Step Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/william20808/google-drive-clone.git
   cd google-drive-clone
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Seed clean database with showcase files:**
   ```bash
   python seed_demo.py
   ```
   *Output confirms the creation of `demo` and `admin` accounts alongside the 5 lightweight files.*

6. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Open your browser:**
   - Main Application: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (Sign in with `demo` / `DemoPassword123!`)
   - Admin Console: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) (Sign in with `admin` / `AdminPassword123!`)

---

## 🧪 Automated Testing & Verification

The codebase includes two comprehensive test suites:

### 1. Standard Django Test Suite
Runs all unit and integration tests across authentication, file storage, data isolation, and preview contracts:
```bash
python manage.py test
```
*Expected: `Ran 19 tests in ~32s (OK)`*

### 2. Squeezed Consolidated Validation Suite
Validates account lifecycles, validation rules, bidirectional admin sync, storage tiers, and batch APIs:
```bash
python test_comprehensive_validation.py
```
*Expected: `ALL CONSOLIDATED FUNCTIONAL & FEATURE VALIDATIONS PASSED (100% OK)` in ~2.5s.*

---

## 🌐 Production & GitHub Deployment Notes

When deploying this project to production (e.g. Render, Railway, Fly.io, Heroku, or a VPS):

1. **Environment Variables**:
   - Set `DEBUG=False` in production.
   - Configure a secret `SECRET_KEY`.
   - Update `ALLOWED_HOSTS` in `gdrive_project/settings.py` with your custom domain or deployment hostname.

2. **Static Assets**:
   - Collect static files for production serving:
     ```bash
     python manage.py collectstatic --noinput
     ```

3. **Media Storage**:
   - Uploaded media is organized under `media/uploads/user_<id>/`. For containerized or ephemeral platforms, mount a persistent volume at `/media/` or configure S3-compatible cloud storage (e.g., AWS S3, Cloudflare R2).

---

## 🙏 Attribution, Inspiration & Original Project Citation

This project draws its foundational conceptual layout, visual aesthetics, and interaction model from the open-source **[google-drive-clone](https://github.com/EzeibekweEmma/google-drive-clone)** created by **[Ezeibekwe Emmanuel](https://github.com/EzeibekweEmma)** (released under the MIT License). Sincere respect, gratitude, and acknowledgment are extended to the original author for the design vision and UI inspiration.

### Architectural Evolution & Key Differences:

| Aspect | Original Implementation | This Rebuild Project |
| :--- | :--- | :--- |
| **Backend & Architecture** | Multi-service Node.js / Next.js, NextAuth, Prisma ORM, PostgreSQL | Pure Python 3 & Django 5 monolith, SQLite, native Django Auth |
| **Cloud Dependency** | Relied on external third-party Cloudinary API for media | Self-contained, single-port zero-build execution with local storage |
| **Document Previews** | Basic link views | Dedicated PDF Reading Mode (zoom & print), Image Viewer (90° rotation & zoom), HTML5 Video Player (0.5x–2x speed), and interactive CSV Table Grid |
| **Batch Operations** | Single item interactions | Multi-select toolbar for batch star, move, trash, restore, delete, and ZIP archive download |
| **Storage & Admin** | Fixed 200MB limit | Configurable 15GB / 100GB / 500GB tiers with integrated Django Admin Console (`/admin/`) |
| **Theme System** | Standard CSS | Zero-lag transition-suppressed Dark/Light Mode with instant client persistence |
| **Performance** | Multi-hop network calls | $O(1)$ in-memory graph traversal for nested folder descendants, database composite indexes, and process-level email caching |

---

## 📄 License
This project is licensed under the MIT License.
