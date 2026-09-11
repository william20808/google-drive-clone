# Google Drive Clone (Django Full-Stack)

A modern, high-performance, single-port Google Drive web application built with **Python 3**, **Django 5**, and a sleek **Tailwind CSS / DaisyUI** interface.

![Google Drive Clone Dashboard Preview](static/img/dashboard_preview.png)

---

## 1. Prerequisites

- **Python 3.10+** (Python 3.11 or 3.12 or 3.13 recommended)
- **Git**
- *(Optional)* **Docker & Docker Compose** (for one-command containerized launch)

---

## 2. Contribution & Attribution

This project is built upon the conceptual layout and visual design of **[google-drive-clone](https://github.com/EzeibekweEmma/google-drive-clone)** created by **[Ezeibekwe Emmanuel](https://github.com/EzeibekweEmma)** (MIT License). Sincere gratitude is extended to the original author for the design inspiration. This project honors that original interface while completely re-architecting the application from React / Next.js / Prisma into a pure Python 3 / Django 5 monolith.

### Architectural Evolution & Key Differences:

| Aspect | Original Implementation | This Rebuild Project |
| :--- | :--- | :--- |
| **Backend & Stack** | Node.js / Next.js, NextAuth, Prisma ORM, PostgreSQL | Pure Python 3 & Django 5 monolith, SQLite (or PostgreSQL), Django Auth |
| **Media Delivery** | Relied on third-party Cloudinary API | Self-contained, single-port zero-build local/server storage |
| **Confidentiality & Privacy** | Plaintext unencrypted storage | **Zero-Knowledge At-Rest Media Encryption** (AES-128-CBC + HMAC-SHA256) — host servers & cloud providers cannot read or inspect user uploads |
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

### ⚡ 1-Click Configuration (.env)
Copy the template configuration file before launching:
```bash
cp .env.example .env
```
*(All variables have secure, working defaults out-of-the-box. If using PostgreSQL, AWS S3, or a custom encryption key, simply fill in your values in `.env`).*

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
All test suites are located in the [`tests/`](file:///tests/) directory:

1. **Standard Django Unit Tests** (19 tests)
   ```bash
   python manage.py test
   ```
   - **File:** `tests/test_unit.py` (~40s)
   - Verifies permissions, workspace data isolation, quotas, trash lifecycle, and public sharing.

2. **Rapid Feature Validation** (Consolidated 4-part suite)
   ```bash
   python tests/test_comprehensive_validation.py
   ```
   - **File:** `tests/test_comprehensive_validation.py` (**~2.5s**)
   - Fast developer checks for profiles, passwords, admin sync, quota tiers, and batch ZIPs.

3. **Live Server Integration** (Real HTTP network test)
   ```bash
   python tests/test_live_server.py
   ```
   - **File:** `tests/test_live_server.py` (~2s, requires `runserver` running)
   - Tests live HTTP requests, session cookies, CSRF tokens, AJAX APIs, and file downloads.

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

## 5. Tech Stack

- **Backend:** Python 3.11, Django 5.1 (ORM, Authentication, Admin Console, WSGI)
- **Frontend:** Vanilla JavaScript, HTML5, Tailwind CSS, DaisyUI (zero-build asset pipeline)
- **Database:** SQLite (default development) / PostgreSQL (production deployment ready)
- **Containerization:** Docker & Docker Compose with Gunicorn WSGI HTTP server
- **Optimizations:** In-memory graph traversal ($O(1)$ folder descent), database composite indexing, and process-level email caching

---

## 6. Features

### Ultra-Lightweight Showcase Media (< 20 KB)
Both `demo` and `admin` accounts come pre-seeded with 5 sample files (~16.5 KB total):

| File Name | Format | Size | Showcase Feature |
| :--- | :--- | :--- | :--- |
| `Getting_Started_Guide.pdf` | PDF Document | ~850 B | PDF Reading Mode (zoom & print) |
| `Google_Drive_Banner.png` | PNG Image | ~1.4 KB | Photo Viewer (rotation & zoom) |
| `Welcome_Notes.txt` | Plain Text | ~580 B | Text Viewer & copy to clipboard |
| `Project_Roadmap.csv` | Tabular Data | ~366 B | Interactive spreadsheet table |
| `Sample_Video.mp4` | MP4 Video | ~13.7 KB | HTML5 Video Player (0.5x–2x speed) |

### Key Features
- **Multi-Format In-Browser Previews:** Instant viewing for PDF, images, MP4 video, CSV spreadsheets, and text files without external dependencies.
- **Drag-and-Drop Uploads:** Seamless multi-file upload zone with live progress indicators.
- **Infinite Folder Hierarchy:** Recursive nested folders with dynamic breadcrumb path navigation.
- **Multi-Select Batch Actions:** Batch Star, Move, Trash, Restore, Permanent Delete, and ZIP archive download.
- **Public Link Sharing:** UUID-based public links for files and folder subtrees with anonymous browsing.
- **Save to My Drive:** Authenticated users can clone publicly shared files directly into their own drive with a single click.
- **Live Search & Category Filters:** Real-time autocomplete suggestions and quick filters (Documents, Images, Audio, Videos).
- **Tiered Storage Management:** Configurable 15GB, 100GB, and 500GB storage plans with visual progress bars.
- **Django Admin Console:** Complete administrative interface at `/admin/` for user management and quota adjustments.
- **Zero-Lag Dark / Light Mode:** Instant theme switcher with browser local persistence.
- **Enterprise-Grade Security:** Strict workspace isolation, CSRF protection, and unpopulated login forms.

---

## 7. Database & Security

### Database Configuration (SQLite vs. PostgreSQL)
- **Default Database (SQLite):** Pre-configured out of the box for zero-setup local development and rapid testing (`db.sqlite3`).
- **Production Server Database (PostgreSQL):** To deploy on cloud platforms (e.g., Render, Railway, AWS RDS, Supabase, Neon):
  1. Install PostgreSQL driver:
     ```bash
     pip install psycopg2-binary
     # Or install all production packages:
     pip install -r requirements-prod.txt
     ```
  2. Set `DATABASE_URL` in your `.env` (or environment variables):
     ```bash
     DATABASE_URL=postgres://postgres:password@localhost:5432/gdrive_db
     ```
     *(Or configure individual parameters: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`).*
  3. Run migrations and seed data:
     ```bash
     python manage.py migrate
     python seed_demo.py
     ```
  4. *(Optional)* **Docker Compose with PostgreSQL:**
     ```bash
     docker compose -f docker-compose.prod.yml up -d
     ```

### 🛡️ Zero-Knowledge Media Encryption (Confidentiality & Privacy)
- **At-Rest AES Encryption:** All user files uploaded to the server (or S3 bucket) are encrypted prior to being written to storage using AES-128 in CBC mode with HMAC-SHA256 authentication (`cryptography.fernet`).
- **Zero Company / Host Visibility:** Server administrators, cloud providers (AWS, Supabase, Render), and host machines cannot view, read, or inspect user files — files on disk are unreadable ciphertext starting with `ENC_FERNET_V1::`.
- **On-The-Fly In-Memory Decryption:** Decryption happens strictly in RAM during authorized streaming (`/drive/view/<id>/`) or downloads (`/drive/download/<id>/`).
- **Key Configuration:** A 256-bit encryption key is automatically derived from `DJANGO_SECRET_KEY`, or you can supply a custom `MEDIA_ENCRYPTION_KEY` in `.env`:
  ```bash
  # Generate a key:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

### Production Security & Deployment Checklist

- **⚠️ Disable Debug Mode in Production (`DEBUG = False`):**
  - Always set `DJANGO_DEBUG=False` in environment variables before deploying publicly.
  - *Why:* Running with `DEBUG = True` leaks internal file paths, database queries, and environment settings in browser traceback screens if an error occurs.
- **Allowed Hosts (`ALLOWED_HOSTS`):** Restrict `ALLOWED_HOSTS = ['yourdomain.com']` in production instead of using the development wildcard `['*']`.
- **Static Assets Compilation:** When running with `DEBUG = False`, compile static assets into `staticfiles/`:
  ```bash
  python manage.py collectstatic --noinput
  ```
- **Database Migrations:** Apply all schema migrations to your database:
  ```bash
  python manage.py migrate --noinput
  ```
- **Secret Key Protection:** Provide a strong, unique `DJANGO_SECRET_KEY` via environment variables.
- **Form Hardening:** Forms use `autocomplete="off"` to prevent automatic browser credential pre-population.
- **Workspace Data Isolation:** Strict user isolation ensures users can never access, modify, or download other users' files without an explicit share token.

