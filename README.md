# Google Drive Clone (Django Full-Stack)

A modern, high-performance, single-port Google Drive web application built with **Python 3**, **Django 5**, and a sleek **Tailwind CSS / DaisyUI** interface.

> **🙏 Attribution & Project Citation:** All core UI/UX concepts and foundational ideas are inspired by and credited to the open-source [Google Drive Clone by Ezeibekwe Emmanuel](https://github.com/EzeibekweEmma/google-drive-clone) (MIT License). This project honors that original design while completely rewriting the stack from React / Next.js / Prisma into a pure Python / Django 5 monolith.

---

## 1. Prerequisites

- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **Git**
- *(Optional)* **Docker & Docker Compose** (for one-command containerized launch)

---

## 2. Contribution & Attribution

This project is built upon the conceptual layout and visual design of **[google-drive-clone](https://github.com/EzeibekweEmma/google-drive-clone)** created by **[Ezeibekwe Emmanuel](https://github.com/EzeibekweEmma)** (MIT License). Sincere gratitude is extended to the original author for the design inspiration.

### Architectural Evolution & Key Differences:

| Aspect | Original Implementation | This Rebuild Project |
| :--- | :--- | :--- |
| **Backend & Stack** | Node.js / Next.js, NextAuth, Prisma ORM, PostgreSQL | Pure Python 3 & Django 5 monolith, SQLite (or PostgreSQL), Django Auth |
| **Media Delivery** | Relied on third-party Cloudinary API | Self-contained, single-port zero-build local/server storage |
| **Document Previews** | Basic link views | Dedicated PDF Reading Mode (zoom & print), Image Viewer (90° rotation & zoom), HTML5 Video Player (0.5x–2x speed), and interactive CSV Table Grid |
| **Batch Operations** | Single item interactions | Multi-select toolbar for batch star, move, trash, restore, delete, and ZIP archive download |
| **Storage & Admin** | Fixed 200MB limit | Configurable 15GB / 100GB / 500GB tiers with integrated Django Admin Console (`/admin/`) |
| **Theme System** | Standard CSS | Zero-lag transition-suppressed Dark/Light Mode with instant client persistence |
| **Performance** | Multi-hop network calls | $O(1)$ in-memory graph traversal for nested folder descendants, database composite indexes, and process-level email caching |

- **Contributing:** Pull requests and feedback are welcome! Please ensure all tests pass before submitting PRs.
- **License:** Distributed under the **MIT License**.

---

## 3. Setup & How to Run

Clone the repository first:
```bash
git clone https://github.com/william20808/google-drive-clone.git
cd google-drive-clone
```

Choose **Option A** (Docker — fastest) or **Option B** (Local Python):

### 🐳 Option A: Docker (One Command — No Python Setup Needed)
If you have Docker installed, you do not need to install Python, create a virtual environment, or run migrations manually:

```bash
docker compose up --build
```
- **App URL:** [http://localhost:8000/](http://localhost:8000/)
- **Admin Console:** [http://localhost:8000/admin/](http://localhost:8000/admin/)
- Database (`db.sqlite3`) and uploads (`media/`) automatically persist on your host machine.
- Stop container with: `docker compose down`

---

### 💻 Option B: Local Python Setup (Without Docker)
If running directly on your host machine with Python:

1. **Create and activate virtual environment:**
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

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations & seed initial database:**
   ```bash
   python manage.py migrate
   python seed_demo.py
   ```
   *Seeds `demo` and `admin` accounts with identical copies of the 5 lightweight sample files.*

4. **Start the local server:**
   ```bash
   python manage.py runserver
   ```
   - **App URL:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - **Admin Console:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

### Default Showcase Credentials
| Account Role | Username | Password | Purpose & Access |
| :--- | :--- | :--- | :--- |
| **Demo User** | `demo` | `DemoPassword123!` | Standard user with the 5 pre-loaded showcase files in their drive |
| **Administrator** | `admin` | `AdminPassword123!` | Superuser with the 5 showcase files in their drive + full Django Admin Console access (`/admin/`) |

> **Security Note:** Both accounts have identical copies of the 5 showcase documents in their individual drives. Login forms do not contain hardcoded or pre-filled credentials.

---

### Automated Testing
All automated tests are organized together in the [`tests/`](file:///tests/) directory to support both formal grading and fast developer verification:

| Command | File Location | Speed | What It Tests & When to Use |
| :--- | :--- | :--- | :--- |
| `python manage.py test` | [`tests/test_unit.py`](file:///tests/test_unit.py) | ~33s | **Standard Django Test Suite (19 tests):** Formal evaluation and CI/CD. Runs in an isolated temporary database testing workspace isolation, upload quotas, trash lifecycle, permissions, and sharing tokens. |
| `python tests/test_comprehensive_validation.py` | [`tests/test_comprehensive_validation.py`](file:///tests/test_comprehensive_validation.py) | **~2.5s** | **Rapid Feature Validation Suite:** Day-to-day coding checks. Validates account profile changes, password lifecycle, Django Admin bidirectional sync, quota upgrades (15GB/100GB/500GB), and multi-file ZIP downloads. |
| `python tests/test_live_server.py` | [`tests/test_live_server.py`](file:///tests/test_live_server.py) | ~2s | **Live HTTP Browser Integration:** End-to-end socket testing over HTTP (`http://127.0.0.1:8000`), testing real CSRF tokens, session cookies, folder creation, and anonymous public downloads *(requires `runserver` active)*. |

---

### Optional: Deploying with PostgreSQL (Production Server Database)
By default, the project runs on **SQLite** for zero-configuration simplicity. To deploy with a server database like **PostgreSQL** (e.g., Render, Railway, Supabase, AWS RDS):

1. Install PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```
2. Update `DATABASES` in `gdrive_project/settings.py` (or use `DATABASE_URL` with `dj-database-url`):
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'gdrive_db',
           'USER': 'postgres',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',  # or cloud database host
           'PORT': '5432',
       }
   }
   ```
3. Run migrations and seed data:
   ```bash
   python manage.py migrate
   python seed_demo.py
   ```

---

## 4. Structure

```text
google-drive-clone/
├── drive/                  # Core Django application
│   ├── models.py           # DriveItem & UserProfile models (with indexing)
│   ├── views.py            # File views, API endpoints, batch handlers
│   ├── utils.py            # Storage calculation & email cache
│   ├── forms.py            # Authentication & profile forms
│   └── tests.py            # Test discovery delegate (imports from tests/)
├── gdrive_project/         # Django project configuration (settings, URLs, WSGI)
├── media/                  # Uploaded files storage (media/uploads/user_<id>/)
├── static/                 # Static CSS, JS preview engine, images
├── templates/              # HTML templates (drive views, modals, admin, auth)
├── tests/                  # Consolidated automated test suite
│   ├── test_unit.py        # 19 core Django unit & isolation test cases
│   ├── test_comprehensive_validation.py # Fast consolidated feature validation
│   └── test_live_server.py # Live HTTP server & AJAX integration tests
├── Dockerfile              # Docker container definition (Python 3.11-slim)
├── docker-compose.yml      # Docker Compose setup with persistent volumes
├── manage.py               # Django management script
├── seed_demo.py            # Database reset & seed script
├── requirements.txt        # Python package dependencies
├── LICENSE                 # MIT License
└── README.md               # Project documentation
```

---

## 5. Indexing and Web Application

### Database Indexing & Query Optimizations
- **Composite Index:** Added `models.Index(fields=['owner', 'is_folder'])` in `DriveItem` to accelerate quota queries and filter scans.
- **$O(1)$ In-Memory Graph Traversal:** Replaced recursive database queries in `DriveItem.get_all_descendants()` with a single-query fetch and in-memory child traversal, reducing $O(N)$ cascading queries to $O(1)$.
- **In-Memory Collision Checking:** Batch upload, move, and copy operations query existing names once as a `set()`, eliminating sequential database round-trips.
- **Process-Level Caching:** Added `_ADMIN_EMAIL_CACHE` in `drive/utils.py` to prevent repeated superuser lookups on every page render.

### Web Application Architecture
- **Single-Port Architecture:** Unified Python/Django 5 monolith serving frontend HTML/JS and backend JSON APIs together without requiring separate Node/proxy servers.
- **Zero-Lag Theme Switcher:** Instant transition-suppressed Dark Mode & Light Mode switcher using `data-theme` with client persistence.
- **Hardened Forms:** Authentication forms do not contain pre-filled default credentials, ensuring secure login inputs.

---

## 6. Feature

### Ultra-Lightweight Showcase Media (< 20 KB)
To ensure fast GitHub deployment, quick clone speeds, and minimal repository weight, both `demo` and `admin` drives come pre-seeded with exactly **5 lightweight showcase files** totaling only **~16.5 KB**:

| File Name | Format | Size | Showcase Feature |
| :--- | :--- | :--- | :--- |
| `Getting_Started_Guide.pdf` | PDF Document | ~850 B | Demonstrates PDF Reading Mode, Zoom & Print |
| `Google_Drive_Banner.png` | PNG Image | ~1.4 KB | Demonstrates Photo Viewer & Rotation |
| `Welcome_Notes.txt` | Plain Text | ~580 B | Demonstrates Text Mode & Clipboard Copying |
| `Project_Roadmap.csv` | Tabular Data | ~366 B | Demonstrates Interactive CSV Table Grid |
| `Sample_Video.mp4` | MP4 Video (W3C WPT) | ~13.7 KB | Demonstrates HTML5 Video Player & Speeds |

### Core Functionality
- **Dedicated Multi-Format Previews:**
  - **PDF Reading Mode:** Document zoom (50% to 200%), fit-to-width, instant printing.
  - **Photo Viewer:** Lossless 90° image rotation and granular zoom controls.
  - **HTML5 Video Player:** Clean video player with speed controls (0.5x, 1x, 1.25x, 1.5x, 2x).
  - **Interactive CSV Table:** Formats delimited data into a scrollable spreadsheet grid.
  - **Text Viewer:** Monospace view with font size adjustments and clipboard copying.
- **File Management:** Drag-and-drop upload zone, nested folders, instant search with dropdown autocomplete.
- **Multi-Select Batch Actions:** Batch Star, Move, Trash, Restore, Permanent Delete, and ZIP archive download.
- **Public Sharing:** Token-based public links for files and folder subtrees with anonymous breadcrumb navigation.
- **Storage Plans & Admin Console:** 15GB, 100GB, and 500GB plans with branded Django Admin management (`/admin/`).
