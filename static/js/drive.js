/**
 * Google Drive Clone - Core Client Interaction Script
 */

// ==============================================================================
// Theme Switcher (High-Efficiency, Zero-Lag Instant Mode)
// ==============================================================================

function getPreferredTheme() {
    try {
        const stored = localStorage.getItem('theme');
        if (stored === 'dark' || stored === 'light') {
            return stored;
        }
    } catch (e) {}
    return 'light';
}

function disableTransitionsTemporarily() {
    const css = document.createElement('style');
    css.id = 'theme-transition-disabler';
    css.textContent = `
        *, *::before, *::after {
            -webkit-transition: none !important;
            -moz-transition: none !important;
            -o-transition: none !important;
            -ms-transition: none !important;
            transition: none !important;
        }
    `;
    document.head.appendChild(css);

    return function restoreTransitions() {
        if (document.body) {
            window.getComputedStyle(document.body).opacity;
        }
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                const el = document.getElementById('theme-transition-disabler');
                if (el) el.remove();
            });
        });
    };
}

function updateThemeIcons(isDark) {
    const sunIcons = document.querySelectorAll('#theme-icon-sun, .theme-icon-sun');
    const moonIcons = document.querySelectorAll('#theme-icon-moon, .theme-icon-moon');
    const toggleBtns = document.querySelectorAll('#theme-toggle-btn, .theme-toggle-btn');

    for (let i = 0; i < sunIcons.length; i++) {
        if (isDark) sunIcons[i].classList.remove('hidden');
        else sunIcons[i].classList.add('hidden');
    }

    for (let i = 0; i < moonIcons.length; i++) {
        if (isDark) moonIcons[i].classList.add('hidden');
        else moonIcons[i].classList.remove('hidden');
    }

    for (let i = 0; i < toggleBtns.length; i++) {
        toggleBtns[i].setAttribute('title', isDark ? 'Switch to Light mode' : 'Switch to Dark mode');
    }
}

function applyTheme(theme, skipTransition = true) {
    const restore = skipTransition ? disableTransitionsTemporarily() : null;
    const isDark = theme === 'dark';

    if (document.documentElement.getAttribute('data-theme') !== theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }
    if (isDark) {
        if (!document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.add('dark');
        }
    } else {
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
        }
    }

    try {
        localStorage.setItem('theme', theme);
    } catch (e) {}

    updateThemeIcons(isDark);

    if (restore) {
        restore();
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') ||
                   (document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next, true);
}

// Initial sync with DOM without duplicate DOM mutations
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        updateThemeIcons(document.documentElement.classList.contains('dark'));
        renderPdfThumbnails();
    });
} else {
    updateThemeIcons(document.documentElement.classList.contains('dark'));
    renderPdfThumbnails();
}

// Live PDF Document Thumbnail Renderer
function renderPdfThumbnails() {
    if (!window.pdfjsLib) return;
    const canvases = document.querySelectorAll('canvas.pdf-thumbnail-canvas:not([data-rendered])');
    canvases.forEach(canvas => {
        const url = canvas.dataset.pdfUrl;
        if (!url) return;
        canvas.setAttribute('data-rendered', 'true');
        window.pdfjsLib.getDocument(url).promise.then(pdf => {
            pdf.getPage(1).then(page => {
                const parent = canvas.parentElement;
                const width = parent ? parent.clientWidth : 220;
                const unscaledViewport = page.getViewport({ scale: 1.0 });
                const scale = ((width || 220) / unscaledViewport.width);
                const viewport = page.getViewport({ scale: Math.max(scale, 0.45) });
                
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                const ctx = canvas.getContext('2d');
                page.render({ canvasContext: ctx, viewport: viewport }).promise.then(() => {
                    canvas.classList.remove('hidden');
                    if (parent) {
                        const fallback = parent.querySelector('.pdf-fallback-sheet');
                        if (fallback) fallback.classList.add('hidden');
                    }
                });
            });
        }).catch(err => {
            // Keep styled fallback paper sheet visible
            console.debug('PDF thumbnail using styled fallback:', err);
        });
    });
}

// Retrieve CSRF Token
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Toast Notification Helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-error' : 'alert-info';
    
    toast.className = `alert ${alertClass} text-white text-xs py-2.5 px-4 shadow-lg rounded-2xl flex items-center space-x-2 transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto`;
    toast.innerHTML = `
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="font-medium">${message}</span>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    });

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Update Storage UI globally
function updateStorageUI(storage) {
    if (!storage) return;
    const bar = document.getElementById('sidebar-storage-progress');
    const text = document.getElementById('sidebar-storage-text');
    const navText = document.getElementById('nav-storage-used');

    if (bar) bar.value = storage.percent;
    if (text) text.textContent = storage.formatted_used;
    if (navText) navText.textContent = `${storage.formatted_used} / ${storage.formatted_limit}`;
}

// ==============================================================================
// Drag and Drop & File Uploads
// ==============================================================================

const dropzone = document.getElementById('main-dropzone');
const overlay = document.getElementById('drag-overlay');
let dragCounter = 0;

if (dropzone && overlay) {
    window.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragCounter++;
        overlay.classList.remove('hidden');
    });

    window.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            overlay.classList.add('hidden');
        }
    });

    window.addEventListener('dragover', (e) => {
        e.preventDefault();
    });

    window.addEventListener('drop', (e) => {
        e.preventDefault();
        dragCounter = 0;
        overlay.classList.add('hidden');

        if (e.dataTransfer && e.dataTransfer.files.length > 0) {
            const hiddenInput = document.getElementById('hidden-file-input');
            const parentId = hiddenInput ? hiddenInput.dataset.parentId : '';
            uploadFiles(e.dataTransfer.files, parentId);
        }
    });
}

function handleFileInput(event) {
    const input = event.target;
    if (input.files && input.files.length > 0) {
        uploadFiles(input.files, input.dataset.parentId || '');
        input.value = ''; // Reset
    }
}

async function uploadFiles(files, parentId = '') {
    showToast(`Uploading ${files.length} file(s)...`, 'info');
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    if (parentId) {
        formData.append('parent_id', parentId);
    }

    try {
        const response = await fetch('/api/files/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed.');
        }

        showToast(data.message || 'Files uploaded successfully.', 'success');
        updateStorageUI(data.storage);
        setTimeout(() => location.reload(), 700);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==============================================================================
// Folder Operations
// ==============================================================================

function openNewFolderModal() {
    const modal = document.getElementById('modal_new_folder');
    const input = document.getElementById('new_folder_name');
    if (modal && input) {
        input.value = 'Untitled folder';
        modal.showModal();
        setTimeout(() => {
            input.focus();
            input.select();
        }, 100);
    }
}

async function submitNewFolder(event) {
    event.preventDefault();
    const modal = document.getElementById('modal_new_folder');
    const input = document.getElementById('new_folder_name');
    const hiddenInput = document.getElementById('hidden-file-input');
    const parentId = hiddenInput ? hiddenInput.dataset.parentId : '';

    const name = input.value.trim();
    if (!name) return;

    const formData = new FormData();
    formData.append('name', name);
    if (parentId) formData.append('parent_id', parentId);

    try {
        const response = await fetch('/api/folders/create/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to create folder.');

        modal.close();
        showToast(data.message || 'Folder created.', 'success');
        setTimeout(() => location.reload(), 500);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==============================================================================
// Rename Operations
// ==============================================================================

function openRenameModal(itemId, currentName, isFolder) {
    const modal = document.getElementById('modal_rename');
    const idInput = document.getElementById('rename_item_id');
    const nameInput = document.getElementById('rename_input_name');

    if (modal && idInput && nameInput) {
        idInput.value = itemId;
        nameInput.value = currentName;
        modal.showModal();
        setTimeout(() => {
            nameInput.focus();
            if (!isFolder && currentName.includes('.')) {
                nameInput.setSelectionRange(0, currentName.lastIndexOf('.'));
            } else {
                nameInput.select();
            }
        }, 100);
    }
}

async function submitRename(event) {
    event.preventDefault();
    const modal = document.getElementById('modal_rename');
    const id = document.getElementById('rename_item_id').value;
    const name = document.getElementById('rename_input_name').value.trim();

    if (!name) return;

    const formData = new FormData();
    formData.append('name', name);

    try {
        const response = await fetch(`/api/items/${id}/rename/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to rename.');

        modal.close();
        showToast(data.message || 'Renamed successfully.', 'success');
        setTimeout(() => location.reload(), 500);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==============================================================================
// Move & Copy Operations
// ==============================================================================

async function openMoveModal(itemId, itemName, isFolder, mode = 'move') {
    const modal = document.getElementById('modal_move');
    const idInput = document.getElementById('move_item_id');
    const modeInput = document.getElementById('move_mode');
    const title = document.getElementById('move_modal_title');
    const desc = document.getElementById('move_modal_desc');
    const btn = document.getElementById('move_submit_btn');
    const select = document.getElementById('move_destination_select');

    if (!modal) return;

    idInput.value = itemId;
    modeInput.value = mode;

    title.textContent = mode === 'move' ? `Move "${itemName}"` : `Copy "${itemName}"`;
    desc.textContent = `Select destination folder for "${itemName}":`;
    btn.textContent = mode === 'move' ? 'Move' : 'Make a copy';

    // Fetch available destinations
    select.innerHTML = '<option value="">Loading folders...</option>';
    modal.showModal();

    try {
        const url = `/api/folders/available/${itemId}/`;
        const res = await fetch(url);
        const data = await res.json();

        select.innerHTML = '';
        data.folders.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.id;
            opt.textContent = f.path;
            select.appendChild(opt);
        });
    } catch (err) {
        select.innerHTML = '<option value="">My Drive (Root)</option>';
    }
}

async function submitMoveOrCopy(event) {
    event.preventDefault();
    const modal = document.getElementById('modal_move');
    const itemId = document.getElementById('move_item_id').value;
    const mode = document.getElementById('move_mode').value;
    const destId = document.getElementById('move_destination_select').value;

    if (mode === 'batch_move') {
        const itemIds = Array.from(selectedItemIds);
        if (!itemIds.length) {
            showToast('No items selected.', 'warning');
            return;
        }
        const formData = new FormData();
        formData.append('destination_id', destId);
        itemIds.forEach(id => formData.append('item_ids[]', id));

        try {
            const response = await fetch('/api/batch/move/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: formData,
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to move items.');

            modal.close();
            showToast(data.message || `Moved ${data.count} items.`, 'success');
            clearItemSelection();
            setTimeout(() => location.reload(), 500);
        } catch (err) {
            showToast(err.message, 'error');
        }
        return;
    }

    const formData = new FormData();
    formData.append('destination_id', destId);

    const endpoint = mode === 'move' ? `/api/items/${itemId}/move/` : `/api/items/${itemId}/copy/`;

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Failed to ${mode} item.`);

        modal.close();
        showToast(data.message || 'Operation successful.', 'success');
        if (data.storage) updateStorageUI(data.storage);
        setTimeout(() => location.reload(), 600);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==============================================================================
// Star Operations
// ==============================================================================

async function toggleStar(itemId) {
    try {
        const response = await fetch(`/api/items/${itemId}/star/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to update star.');

        showToast(data.message, 'success');
        setTimeout(() => location.reload(), 400);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==============================================================================
// Trash, Restore, and Permanent Deletion
// ==============================================================================

async function trashItem(itemId, itemName) {
    try {
        const response = await fetch(`/api/items/${itemId}/trash/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to move to bin.');

        showToast(data.message || `Moved "${itemName}" to bin.`, 'success');
        setTimeout(() => location.reload(), 400);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function restoreItem(itemId, itemName) {
    try {
        const response = await fetch(`/api/items/${itemId}/restore/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to restore item.');

        showToast(data.message || `Restored "${itemName}".`, 'success');
        setTimeout(() => location.reload(), 400);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function deletePermanent(itemId, itemName) {
    const modal = document.getElementById('modal_confirm_delete');
    const title = document.getElementById('confirm_delete_title');
    const msg = document.getElementById('confirm_delete_message');
    const btn = document.getElementById('confirm_delete_btn');

    title.textContent = `Delete "${itemName}" forever?`;
    msg.textContent = `"${itemName}" will be permanently removed from disk and cannot be recovered.`;
    btn.textContent = 'Delete forever';

    btn.onclick = async () => {
        try {
            const res = await fetch(`/api/items/${itemId}/delete/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed.');

            modal.close();
            showToast(data.message || 'Deleted permanently.', 'success');
            if (data.storage) updateStorageUI(data.storage);
            setTimeout(() => location.reload(), 500);
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    modal.showModal();
}

function confirmEmptyTrash() {
    const modal = document.getElementById('modal_confirm_delete');
    const title = document.getElementById('confirm_delete_title');
    const msg = document.getElementById('confirm_delete_message');
    const btn = document.getElementById('confirm_delete_btn');

    title.textContent = 'Empty trash?';
    msg.textContent = 'All items in trash will be permanently deleted and storage space will be reclaimed.';
    btn.textContent = 'Empty trash';

    btn.onclick = async () => {
        try {
            const res = await fetch('/api/trash/empty/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Empty trash failed.');

            modal.close();
            showToast(data.message || 'Trash emptied.', 'success');
            if (data.storage) updateStorageUI(data.storage);
            setTimeout(() => location.reload(), 500);
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    modal.showModal();
}

// ==============================================================================
// Sharing Operations
// ==============================================================================

let currentShareItemId = null;

function openShareModal(itemId, fileName, isShared, shareToken) {
    currentShareItemId = itemId;
    const modal = document.getElementById('modal_share');
    const title = document.getElementById('share_file_name');
    const radioPrivate = document.getElementById('share_radio_private');
    const radioPublic = document.getElementById('share_radio_public');
    const container = document.getElementById('share_link_container');
    const input = document.getElementById('share_url_input');

    title.textContent = fileName;
    if (isShared && shareToken) {
        radioPublic.checked = true;
        container.classList.remove('hidden');
        input.value = `${window.location.origin}/share/${shareToken}/`;
    } else {
        radioPrivate.checked = true;
        container.classList.add('hidden');
        input.value = '';
    }

    modal.showModal();
}

async function toggleShareAccess(isPublic) {
    if (!currentShareItemId) return;
    const container = document.getElementById('share_link_container');
    const input = document.getElementById('share_url_input');

    const formData = new FormData();
    formData.append('is_shared', isPublic ? 'true' : 'false');

    try {
        const response = await fetch(`/api/items/${currentShareItemId}/share/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to update share settings.');

        if (data.is_shared && data.share_url) {
            container.classList.remove('hidden');
            input.value = data.share_url;
            showToast('Link sharing enabled.', 'success');
        } else {
            container.classList.add('hidden');
            input.value = '';
            showToast('Link sharing disabled.', 'info');
        }

        // Update cached attributes on any trigger buttons for this item
        const buttons = document.querySelectorAll(`button[onclick*="'${currentShareItemId}'"]`);
        buttons.forEach(btn => {
            const oc = btn.getAttribute('onclick');
            if (oc && oc.includes('openShareModal')) {
                const safeName = (data.name || '').replace(/'/g, "\\'");
                btn.setAttribute('onclick', `openShareModal('${currentShareItemId}', '${safeName}', ${data.is_shared}, '${data.share_token || ''}')`);
            }
        });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function copyShareUrl() {
    const input = document.getElementById('share_url_input');
    if (!input || !input.value) return;

    try {
        await navigator.clipboard.writeText(input.value);
        showToast('Link copied to clipboard!', 'success');
    } catch (e) {
        input.select();
        document.execCommand('copy');
        showToast('Link copied to clipboard!', 'success');
    }
}

// ==============================================================================
// File Preview Modal
// ==============================================================================

// ==============================================================================
// File Preview Modal with Dedicated Reading / Photo / Video Modes
// ==============================================================================

let modalPdfScale = 1.0;
let modalImgScale = 1.0;
let modalImgRotate = 0;

function handleFileDblClick(fileId, fileName, previewType, fileUrl, fileSize, fileDate) {
    previewFile(fileId, fileName, previewType, fileUrl, fileSize, fileDate);
}

async function previewFile(fileId, fileName, previewType, fileUrl, fileSize, fileDate) {
    const modal = document.getElementById('modal_preview');
    const title = document.getElementById('preview_file_name');
    const dlBtn = document.getElementById('preview_download_btn');
    const contentArea = document.getElementById('preview_content_area');
    const sizeSpan = document.getElementById('preview_file_size');
    const dateSpan = document.getElementById('preview_file_date');
    const controlsArea = document.getElementById('preview_reading_controls');

    title.textContent = fileName;
    dlBtn.href = `/drive/download/${fileId}/`;
    sizeSpan.textContent = `Size: ${fileSize}`;
    dateSpan.textContent = `Modified: ${fileDate}`;

    // Reset transform states
    modalPdfScale = 1.0;
    modalImgScale = 1.0;
    modalImgRotate = 0;

    contentArea.innerHTML = '<div class="loading loading-spinner text-primary loading-lg"></div>';
    modal.showModal();

    if (previewType === 'image') {
        if (controlsArea) {
            controlsArea.innerHTML = `
                <button type="button" onclick="zoomModalImage(-0.2)" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Zoom out">-</button>
                <span id="modal_img_zoom" class="text-xs text-gray-300 font-mono w-10 text-center">100%</span>
                <button type="button" onclick="zoomModalImage(0.2)" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Zoom in">+</button>
                <button type="button" onclick="rotateModalImage(90)" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Rotate 90°">↻</button>
                <button type="button" onclick="resetModalImageTransform()" class="btn btn-ghost btn-xs text-gray-300 hover:text-white text-xs" title="Reset">Reset</button>
                <a href="${fileUrl}" target="_blank" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Full resolution">↗</a>
            `;
        }
        contentArea.innerHTML = `
            <div class="overflow-hidden flex items-center justify-center p-2 w-full h-full">
                <img id="modal_preview_img" src="${fileUrl}" alt="${fileName}" class="max-w-full max-h-[72vh] object-contain rounded-xl shadow-2xl transition-transform duration-200">
            </div>
        `;
    } else if (previewType === 'pdf') {
        if (controlsArea) {
            controlsArea.innerHTML = `
                <button type="button" onclick="zoomModalPdf(-0.15)" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Zoom out">-</button>
                <span id="modal_pdf_zoom" class="text-xs text-gray-300 font-mono w-10 text-center">100%</span>
                <button type="button" onclick="zoomModalPdf(0.15)" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Zoom in">+</button>
                <button type="button" onclick="resetModalPdfZoom()" class="btn btn-ghost btn-xs text-gray-300 hover:text-white text-xs" title="Reset">Reset</button>
                <button type="button" onclick="toggleModalPdfFitWidth()" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Fit width">⤢</button>
                <a href="${fileUrl}" target="_blank" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Open in new tab">↗</a>
                <button type="button" onclick="printModalPdf()" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Print document">⎙</button>
            `;
        }
        contentArea.innerHTML = `
            <div id="modal_pdf_wrapper" class="w-full h-[72vh] rounded-xl overflow-hidden bg-white shadow-2xl transition-transform duration-200 origin-top">
                <iframe id="modal_pdf_iframe" src="${fileUrl}" class="w-full h-full border-0"></iframe>
            </div>
        `;
    } else if (previewType === 'video') {
        if (controlsArea) {
            controlsArea.innerHTML = `
                <select onchange="setModalVideoSpeed(this.value)" class="select select-xs select-bordered bg-gray-800 text-gray-200 border-gray-700 rounded-lg">
                    <option value="0.75">0.75x</option>
                    <option value="1" selected>1.0x</option>
                    <option value="1.25">1.25x</option>
                    <option value="1.5">1.5x</option>
                    <option value="2">2.0x</option>
                </select>
            `;
        }
        contentArea.innerHTML = `
            <video id="modal_video_player" controls autoplay class="max-w-full max-h-[72vh] rounded-xl shadow-2xl bg-black">
                <source src="${fileUrl}">
                Your browser does not support video playback.
            </video>
        `;
    } else if (previewType === 'audio') {
        if (controlsArea) {
            controlsArea.innerHTML = `
                <div class="flex items-center space-x-1.5 text-xs text-gray-300">
                    <span class="hidden sm:inline">Speed:</span>
                    <select onchange="setModalAudioSpeed(this.value)" class="select select-xs select-bordered bg-gray-800 text-gray-200 border-gray-700 rounded-lg">
                        <option value="0.75">0.75x</option>
                        <option value="1" selected>1.0x</option>
                        <option value="1.25">1.25x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2">2.0x</option>
                    </select>
                </div>
            `;
        }
        contentArea.innerHTML = `
            <div class="flex flex-col items-center space-y-4 bg-gray-900 p-8 rounded-3xl border border-gray-800 shadow-2xl">
                <svg class="w-20 h-20 text-amber-500 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
                <p class="text-sm font-medium text-gray-200">${fileName}</p>
                <audio id="modal_audio_player" controls autoplay class="w-80">
                    <source src="${fileUrl}">
                    Your browser does not support audio playback.
                </audio>
            </div>
        `;
    } else if (previewType === 'text') {
        if (controlsArea) controlsArea.innerHTML = '';
        contentArea.innerHTML = '<div class="p-16 flex flex-col items-center justify-center text-gray-400"><div class="loading loading-spinner text-primary loading-lg mb-3"></div><p class="text-xs">Loading document...</p></div>';
        try {
            const res = await fetch(fileUrl);
            if (!res.ok) throw new Error('Could not read text file.');
            const text = await res.text();
            window.modalCurrentText = text;

            const ext = fileName.split('.').pop().toLowerCase();
            const isCsv = ext === 'csv' || ext === 'tsv';
            const isMd = ext === 'md' || ext === 'markdown' || ext === 'rst';

            let tabsHtml = '';
            if (isCsv) {
                tabsHtml = `
                    <button type="button" id="modal-tab-table" onclick="setModalTextViewMode('table', '${ext}')" class="btn btn-ghost btn-xs bg-white/20 text-white">Table</button>
                    <button type="button" id="modal-tab-raw" onclick="setModalTextViewMode('raw', '${ext}')" class="btn btn-ghost btn-xs text-gray-300 hover:text-white">Raw</button>
                `;
            } else if (isMd) {
                tabsHtml = `
                    <button type="button" id="modal-tab-preview" onclick="setModalTextViewMode('preview')" class="btn btn-ghost btn-xs bg-white/20 text-white">Preview</button>
                    <button type="button" id="modal-tab-raw" onclick="setModalTextViewMode('raw')" class="btn btn-ghost btn-xs text-gray-300 hover:text-white">Raw</button>
                `;
            }

            if (controlsArea) {
                controlsArea.innerHTML = `
                    ${tabsHtml}
                    <button type="button" onclick="adjustModalTextFontSize(-1)" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Decrease font size">A-</button>
                    <button type="button" onclick="adjustModalTextFontSize(1)" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Increase font size">A+</button>
                    <button type="button" id="modal-wrap-btn" onclick="toggleModalTextWordWrap()" class="btn btn-ghost btn-xs text-gray-300 hover:text-white text-xs" title="Toggle word wrap">Wrap</button>
                    <button type="button" onclick="copyModalTextToClipboard()" class="btn btn-ghost btn-xs text-gray-300 hover:text-white" title="Copy text">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/></svg>
                    </button>
                    <button type="button" onclick="printModalText()" class="btn btn-ghost btn-xs text-gray-300 hover:text-white hidden sm:inline-flex" title="Print document">⎙</button>
                `;
            }

            contentArea.innerHTML = `
                <div class="w-full h-full p-2 sm:p-4 overflow-auto">
                    <div id="modal-csv-wrap" class="w-full ${isCsv ? '' : 'hidden'}">
                        ${isCsv ? renderModalCsvTable(text, ext === 'tsv' ? '\t' : ',') : ''}
                    </div>
                    <div id="modal-md-wrap" class="w-full ${isMd ? '' : 'hidden'}">
                        ${isMd ? renderModalMarkdown(text) : ''}
                    </div>
                    <pre id="modal-text-code-body" class="w-full text-xs font-mono text-gray-200 select-text leading-relaxed whitespace-pre-wrap ${(isCsv || isMd) ? 'hidden' : ''}">${escapeHtml(text)}</pre>
                </div>
            `;
        } catch (e) {
            contentArea.innerHTML = `
                <div class="text-center p-8">
                    <p class="text-sm text-gray-400 mb-4">Unable to load text preview.</p>
                    <a href="/drive/download/${fileId}/" download="${fileName}" class="btn btn-sm bg-gdrive-blue hover:bg-gdrive-blueHover text-white rounded-full normal-case">Download File</a>
                </div>
            `;
        }
    } else {
        if (controlsArea) controlsArea.innerHTML = '';
        contentArea.innerHTML = `
            <div class="text-center p-8 bg-gray-900 border border-gray-800 rounded-3xl max-w-sm w-full">
                <svg class="w-16 h-16 text-gray-500 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p class="text-sm text-gray-300 font-medium mb-1 truncate">${fileName}</p>
                <p class="text-xs text-gray-500 mb-5">No preview available for this file type.</p>
                <a href="/drive/download/${fileId}/" download class="btn bg-gdrive-blue hover:bg-gdrive-blueHover text-white rounded-full normal-case w-full text-xs">Download file</a>
            </div>
        `;
    }
}

// Modal reading mode helpers
function zoomModalPdf(delta) {
    modalPdfScale = Math.min(Math.max(0.5, modalPdfScale + delta), 2.5);
    const wrapper = document.getElementById('modal_pdf_wrapper');
    const label = document.getElementById('modal_pdf_zoom');
    if (wrapper) wrapper.style.transform = `scale(${modalPdfScale})`;
    if (label) label.textContent = `${Math.round(modalPdfScale * 100)}%`;
}

function resetModalPdfZoom() {
    modalPdfScale = 1.0;
    const wrapper = document.getElementById('modal_pdf_wrapper');
    const label = document.getElementById('modal_pdf_zoom');
    if (wrapper) wrapper.style.transform = 'scale(1)';
    if (label) label.textContent = '100%';
}

function toggleModalPdfFitWidth() {
    const wrapper = document.getElementById('modal_pdf_wrapper');
    if (!wrapper) return;
    if (wrapper.style.width === '100%') {
        wrapper.style.width = '850px';
    } else {
        wrapper.style.width = '100%';
    }
}

function printModalPdf() {
    const iframe = document.getElementById('modal_pdf_iframe');
    if (iframe && iframe.contentWindow) {
        try {
            iframe.contentWindow.print();
        } catch (e) {
            window.print();
        }
    } else {
        window.print();
    }
}

function zoomModalImage(delta) {
    modalImgScale = Math.min(Math.max(0.4, modalImgScale + delta), 3.0);
    updateModalImageTransform();
}

function rotateModalImage(deg) {
    modalImgRotate = (modalImgRotate + deg) % 360;
    updateModalImageTransform();
}

function resetModalImageTransform() {
    modalImgScale = 1.0;
    modalImgRotate = 0;
    updateModalImageTransform();
}

function updateModalImageTransform() {
    const img = document.getElementById('modal_preview_img');
    const label = document.getElementById('modal_img_zoom');
    if (img) img.style.transform = `scale(${modalImgScale}) rotate(${modalImgRotate}deg)`;
    if (label) label.textContent = `${Math.round(modalImgScale * 100)}%`;
}

function setModalVideoSpeed(rate) {
    const video = document.getElementById('modal_video_player');
    if (video) video.playbackRate = parseFloat(rate);
}

function setModalAudioSpeed(rate) {
    const audio = document.getElementById('modal_audio_player');
    if (audio) audio.playbackRate = parseFloat(rate);
}

let modalTextFontSize = 13;
function adjustModalTextFontSize(delta) {
    modalTextFontSize = Math.min(Math.max(10, modalTextFontSize + delta), 24);
    const el = document.getElementById('modal-text-code-body');
    if (el) el.style.fontSize = `${modalTextFontSize}px`;
}

function toggleModalTextWordWrap() {
    const el = document.getElementById('modal-text-code-body');
    const btn = document.getElementById('modal-wrap-btn');
    if (!el) return;
    if (el.classList.contains('whitespace-pre-wrap')) {
        el.classList.remove('whitespace-pre-wrap');
        el.classList.add('whitespace-pre');
        if (btn) btn.classList.remove('bg-white/20', 'text-white');
    } else {
        el.classList.remove('whitespace-pre');
        el.classList.add('whitespace-pre-wrap');
        if (btn) btn.classList.add('bg-white/20', 'text-white');
    }
}

function copyModalTextToClipboard() {
    if (!window.modalCurrentText) return;
    navigator.clipboard.writeText(window.modalCurrentText).then(() => {
        showToast('Copied content to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy to clipboard', 'error');
    });
}

function printModalText() {
    const printWin = window.open('', '_blank');
    const textToPrint = window.modalCurrentText || '';
    printWin.document.write(`
        <html>
            <head><title>Print Document</title><style>body { font-family: monospace; font-size: 12px; white-space: pre-wrap; padding: 20px; }</style></head>
            <body>${escapeHtml(textToPrint)}</body>
        </html>
    `);
    printWin.document.close();
    printWin.focus();
    printWin.print();
    printWin.close();
}

function setModalTextViewMode(mode, ext) {
    const csvWrap = document.getElementById('modal-csv-wrap');
    const mdWrap = document.getElementById('modal-md-wrap');
    const codeBody = document.getElementById('modal-text-code-body');
    const btnTable = document.getElementById('modal-tab-table');
    const btnPreview = document.getElementById('modal-tab-preview');
    const btnRaw = document.getElementById('modal-tab-raw');

    if (mode === 'table') {
        if (csvWrap) csvWrap.classList.remove('hidden');
        if (codeBody) codeBody.classList.add('hidden');
        if (btnTable) btnTable.classList.add('bg-white/20', 'text-white');
        if (btnRaw) btnRaw.classList.remove('bg-white/20', 'text-white');
    } else if (mode === 'preview') {
        if (mdWrap) mdWrap.classList.remove('hidden');
        if (codeBody) codeBody.classList.add('hidden');
        if (btnPreview) btnPreview.classList.add('bg-white/20', 'text-white');
        if (btnRaw) btnRaw.classList.remove('bg-white/20', 'text-white');
    } else {
        if (csvWrap) csvWrap.classList.add('hidden');
        if (mdWrap) mdWrap.classList.add('hidden');
        if (codeBody) codeBody.classList.remove('hidden');
        if (btnTable) btnTable.classList.remove('bg-white/20', 'text-white');
        if (btnPreview) btnPreview.classList.remove('bg-white/20', 'text-white');
        if (btnRaw) btnRaw.classList.add('bg-white/20', 'text-white');
    }
}

function parseModalCsv(text, delimiter = ',') {
    const lines = text.trim().split(/\r\n|\n|\r/);
    const rows = [];
    for (let line of lines) {
        if (!line.trim()) continue;
        const row = [];
        let inQuotes = false;
        let cell = '';
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                if (inQuotes && line[i+1] === '"') {
                    cell += '"';
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (char === delimiter && !inQuotes) {
                row.push(cell.trim());
                cell = '';
            } else {
                cell += char;
            }
        }
        row.push(cell.trim());
        rows.push(row);
    }
    return rows;
}

function renderModalCsvTable(text, delimiter = ',') {
    const rows = parseModalCsv(text, delimiter);
    if (!rows || rows.length === 0) {
        return '<p class="text-gray-400 p-4 text-center text-xs">No tabular data found.</p>';
    }
    const headers = rows[0];
    const dataRows = rows.slice(1);
    let html = '<div class="overflow-auto max-h-[70vh] w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">';
    html += '<table class="w-full text-left text-xs border-collapse font-mono">';
    html += '<thead class="bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 sticky top-0 border-b border-gray-300 dark:border-gray-700">';
    html += '<tr>';
    html += '<th class="py-2 px-3 border-r border-gray-200 dark:border-gray-700 text-gray-400 select-none text-right w-12">#</th>';
    headers.forEach((h) => {
        html += `<th class="py-2 px-3 border-r border-gray-200 dark:border-gray-700 font-semibold whitespace-nowrap">${escapeHtml(h)}</th>`;
    });
    html += '</tr></thead>';
    html += '<tbody class="divide-y divide-gray-100 dark:divide-gray-800 text-gray-800 dark:text-gray-200">';
    dataRows.forEach((row, idx) => {
        html += '<tr class="hover:bg-blue-50/50 dark:hover:bg-white/5 transition">';
        html += `<td class="py-1.5 px-3 border-r border-gray-200 dark:border-gray-700 text-gray-400 select-none text-right">${idx + 1}</td>`;
        headers.forEach((_, cIdx) => {
            const val = row[cIdx] !== undefined ? row[cIdx] : '';
            html += `<td class="py-1.5 px-3 border-r border-gray-200 dark:border-gray-700 whitespace-nowrap">${escapeHtml(val)}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table></div>';
    return html;
}

function renderModalMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-900 text-gray-100 p-4 rounded-xl text-xs font-mono my-3 overflow-auto"><code>$1</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 dark:bg-gray-800 text-pink-600 dark:text-pink-400 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>');
    html = html.replace(/^### (.*$)/gim, '<h3 class="text-base font-semibold text-gray-900 dark:text-white mt-4 mb-2">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 class="text-lg font-bold text-gray-900 dark:text-white mt-5 mb-2 pb-1 border-b border-gray-200 dark:border-gray-700">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 class="text-xl font-bold text-gray-900 dark:text-white mt-6 mb-3 pb-2 border-b border-gray-200 dark:border-gray-700">$1</h1>');
    html = html.replace(/^\> (.*$)/gim, '<blockquote class="border-l-4 border-blue-500 pl-4 py-1 my-2 text-gray-600 dark:text-gray-300 italic bg-blue-50/50 dark:bg-blue-900/10 rounded-r">$1</blockquote>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-900 dark:text-white">$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>');
    html = html.replace(/^[\*\-] (.*$)/gim, '<li class="ml-4 list-disc">$1</li>');
    html = html.replace(/^---$/gim, '<hr class="my-4 border-gray-200 dark:border-gray-700">');
    html = html.replace(/\n\n/g, '<br><br>');
    return `<div class="prose dark:prose-invert max-w-none text-sm leading-relaxed p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-xs">${html}</div>`;
}

function escapeHtml(string) {
    return String(string)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ==============================================================================
// Dynamic Full-Page Layout Engine
// Renders and stretches containers across the entire viewport height first,
// even when below is empty, and only allows scrolling when content overflows.
// ==============================================================================

function fitWholePageLayout() {
    const mainDropzone = document.getElementById('main-dropzone');
    const contentContainer = document.getElementById('drive-content-container');
    const listContainer = document.getElementById('drive-list-container');
    const gridContainer = document.getElementById('drive-grid-container');

    if (!mainDropzone) return;

    // Viewport height
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;

    // Set dropzone to take up full available vertical space
    const dropzoneRect = mainDropzone.getBoundingClientRect();
    const minDropzoneHeight = Math.max(400, windowHeight - dropzoneRect.top);
    mainDropzone.style.minHeight = `${minDropzoneHeight}px`;

    if (contentContainer) {
        // Measure where contentContainer starts relative to viewport top
        const contentRect = contentContainer.getBoundingClientRect();
        // 24px bottom buffer to provide breathing room above the viewport bottom edge
        const availableHeight = Math.max(320, windowHeight - contentRect.top - 24);
        
        contentContainer.style.minHeight = `${availableHeight}px`;

        // If list view container is active, stretch it to fill the entire remaining page height
        if (listContainer) {
            listContainer.style.minHeight = `${availableHeight}px`;
            // Remove any vertical scrollbars inside the list container so whole page scrolls naturally
            listContainer.style.overflowY = 'visible';
            const tableWrapper = listContainer.querySelector('.table-wrapper');
            if (tableWrapper && window.innerWidth >= 768) {
                tableWrapper.style.overflowY = 'visible';
                tableWrapper.style.overflowX = 'visible';
            }
        }

        // If grid view container is active, ensure it spans the whole page height as well
        if (gridContainer) {
            gridContainer.style.minHeight = `${availableHeight}px`;
        }
    }
}

// Automatically run layout calculation on DOMContentLoaded, window load, and window resize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fitWholePageLayout);
} else {
    fitWholePageLayout();
}

window.addEventListener('load', fitWholePageLayout);
window.addEventListener('resize', fitWholePageLayout);

// ==============================================================================
// Google Drive Instant Search Overlay & Autocomplete Engine
// ==============================================================================

let searchDebounceTimer = null;
let currentSearchQuery = '';
let currentSearchCategory = '';
let searchResultsData = [];
let searchSelectedResultIndex = -1;

function initSearchAutocomplete() {
    const searchInput = document.getElementById('search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const searchOptionsBtn = document.getElementById('search-options-btn');
    const searchOptionsFooterBtn = document.getElementById('search-options-footer-btn');
    const searchDropdown = document.getElementById('search-autocomplete-dropdown');
    const searchForm = document.getElementById('search-form');
    const searchContainer = document.getElementById('search-container');

    if (!searchInput || !searchDropdown) return;

    // Show clear button if input has initial value
    if (searchInput.value.trim().length > 0 && searchClearBtn) {
        searchClearBtn.classList.remove('hidden');
    }

    // Input typing listener with debounce
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        currentSearchQuery = query;

        if (query.length > 0) {
            if (searchClearBtn) searchClearBtn.classList.remove('hidden');
        } else {
            if (searchClearBtn) searchClearBtn.classList.add('hidden');
        }

        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            fetchInstantSearchResults(query, currentSearchCategory);
        }, 160);
    });

    // Input focus listener: open dropdown
    searchInput.addEventListener('focus', () => {
        const query = searchInput.value.trim();
        fetchInstantSearchResults(query, currentSearchCategory);
    });

    // Clear button listener
    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            searchInput.value = '';
            currentSearchQuery = '';
            searchClearBtn.classList.add('hidden');
            searchInput.focus();
            fetchInstantSearchResults('', currentSearchCategory);
        });
    }

    // Search options buttons: trigger full search or open filters
    if (searchOptionsBtn) {
        searchOptionsBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const query = searchInput.value.trim();
            fetchInstantSearchResults(query, currentSearchCategory);
        });
    }

    if (searchOptionsFooterBtn) {
        searchOptionsFooterBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (searchForm) searchForm.submit();
        });
    }

    // Keyboard navigation (ArrowDown, ArrowUp, Enter, Escape)
    searchInput.addEventListener('keydown', (e) => {
        if (searchDropdown.classList.contains('hidden')) {
            if (e.key === 'ArrowDown') {
                fetchInstantSearchResults(searchInput.value.trim(), currentSearchCategory);
            }
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (searchResultsData.length === 0) return;
            searchSelectedResultIndex = (searchSelectedResultIndex + 1) % searchResultsData.length;
            highlightSearchResult(searchSelectedResultIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (searchResultsData.length === 0) return;
            searchSelectedResultIndex = (searchSelectedResultIndex - 1 + searchResultsData.length) % searchResultsData.length;
            highlightSearchResult(searchSelectedResultIndex);
        } else if (e.key === 'Enter') {
            if (searchSelectedResultIndex >= 0 && searchSelectedResultIndex < searchResultsData.length) {
                e.preventDefault();
                selectSearchResult(searchResultsData[searchSelectedResultIndex]);
            }
            // Otherwise let form submit normally
        } else if (e.key === 'Escape') {
            e.preventDefault();
            closeSearchDropdown();
        }
    });

    // Dismiss when clicking outside
    document.addEventListener('click', (e) => {
        if (searchContainer && !searchContainer.contains(e.target)) {
            closeSearchDropdown();
        }
    });
}

function closeSearchDropdown() {
    const searchDropdown = document.getElementById('search-autocomplete-dropdown');
    if (searchDropdown) {
        searchDropdown.classList.add('hidden');
    }
    searchSelectedResultIndex = -1;
}

function setQuickSearchFilter(category, btnElement) {
    if (currentSearchCategory === category) {
        currentSearchCategory = '';
    } else {
        currentSearchCategory = category === 'all' ? '' : category;
    }

    const buttons = document.querySelectorAll('#search-type-filters button');
    buttons.forEach(btn => {
        btn.classList.remove('bg-gdrive-active', 'text-gdrive-blue', 'font-semibold', 'border-gdrive-blue');
    });

    if (btnElement && currentSearchCategory) {
        btnElement.classList.add('bg-gdrive-active', 'text-gdrive-blue', 'font-semibold', 'border-gdrive-blue');
    }

    const searchInput = document.getElementById('search-input');
    const query = searchInput ? searchInput.value.trim() : '';
    fetchInstantSearchResults(query, currentSearchCategory);
}

async function fetchInstantSearchResults(query, category) {
    const searchDropdown = document.getElementById('search-autocomplete-dropdown');
    const searchResultsList = document.getElementById('search-results-list');
    const searchLoading = document.getElementById('search-loading');
    const searchEmpty = document.getElementById('search-empty');
    const searchChipSection = document.getElementById('search-chip-section');
    const searchChipAvatar = document.getElementById('search-chip-avatar');
    const searchChipText = document.getElementById('search-chip-text');

    if (!searchDropdown || !searchResultsList) return;

    searchDropdown.classList.remove('hidden');
    if (searchLoading) searchLoading.classList.remove('hidden');
    if (searchEmpty) searchEmpty.classList.add('hidden');
    searchResultsList.innerHTML = '';
    searchSelectedResultIndex = -1;

    // Handle suggestion chip (e.g. Hiring, or email query like in user screenshot)
    if (query && query.length >= 2) {
        if (searchChipSection && searchChipAvatar && searchChipText) {
            searchChipSection.classList.remove('hidden');
            const cleanText = query.split('@')[0];
            searchChipText.textContent = query;
            searchChipAvatar.textContent = cleanText.charAt(0).toUpperCase();
            searchChipSection.onclick = () => {
                const searchInput = document.getElementById('search-input');
                if (searchInput) searchInput.value = query;
                const searchForm = document.getElementById('search-form');
                if (searchForm) searchForm.submit();
            };
        }
    } else {
        if (searchChipSection) searchChipSection.classList.add('hidden');
    }

    try {
        let url = `/api/search/?q=${encodeURIComponent(query)}`;
        if (category) {
            url += `&category=${encodeURIComponent(category)}`;
        }

        const res = await fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (!res.ok) throw new Error('Search failed');

        const data = await res.json();
        searchResultsData = data.results || [];

        if (searchLoading) searchLoading.classList.add('hidden');

        if (searchResultsData.length === 0) {
            if (searchEmpty) searchEmpty.classList.remove('hidden');
        } else {
            renderSearchResults(searchResultsData);
        }
    } catch (e) {
        if (searchLoading) searchLoading.classList.add('hidden');
        if (searchEmpty) searchEmpty.classList.remove('hidden');
    }
}

function getFileTypeSvgBadge(item) {
    if (item.is_folder) {
        return `
            <div class="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0 text-amber-500">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                </svg>
            </div>
        `;
    }

    const ext = (item.extension || '').toLowerCase();
    const previewType = item.preview_type || '';

    if (ext === 'pdf' || previewType === 'pdf') {
        return `
            <div class="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0 text-red-500">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"/>
                </svg>
            </div>
        `;
    }

    if (['csv', 'xlsx', 'xls', 'sheet'].includes(ext)) {
        return `
            <div class="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0 text-emerald-500">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5 4a3 3 0 00-3 3v6a3 3 0 003 3h10a3 3 0 003-3V7a3 3 0 00-3-3H5zm-1 9v-1h5v2H5a1 1 0 01-1-1zm7 1v-2h5v1a1 1 0 01-1 1h-4zm5-4h-5V8h4a1 1 0 011 1v1zm-7-2v2H4V9a1 1 0 011-1h4z" clip-rule="evenodd"/>
                </svg>
            </div>
        `;
    }

    if (['ppt', 'pptx', 'slide', 'presentation'].includes(ext)) {
        return `
            <div class="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0 text-amber-500">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm1 4a1 1 0 00-1 1v6a1 1 0 001 1h12a1 1 0 001-1V9a1 1 0 00-1-1H4zm3 2a1 1 0 011-1h4a1 1 0 110 2H8a1 1 0 01-1-1z" clip-rule="evenodd"/>
                </svg>
            </div>
        `;
    }

    if (previewType === 'image') {
        return `
            <div class="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center flex-shrink-0 text-rose-500">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
                </svg>
            </div>
        `;
    }

    if (previewType === 'video') {
        return `
            <div class="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center flex-shrink-0 text-purple-500">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
            </div>
        `;
    }

    if (previewType === 'audio') {
        return `
            <div class="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0 text-amber-500">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
                </svg>
            </div>
        `;
    }

    // Default document badge
    return `
        <div class="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0 text-blue-500">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
        </div>
    `;
}

function renderSearchResults(results) {
    const list = document.getElementById('search-results-list');
    if (!list) return;

    list.innerHTML = results.map((item, index) => {
        const badge = getFileTypeSvgBadge(item);
        const ownerInfo = `${item.owner_name || 'You'} • ${escapeHtml(item.parent_name || 'My Drive')}`;

        return `
            <div 
                class="search-result-item flex items-center justify-between px-4 py-3 cursor-pointer select-none transition"
                data-index="${index}"
                onclick="handleSearchResultClick(${index})"
            >
                <div class="flex items-center space-x-3 min-w-0 flex-1">
                    ${badge}
                    <div class="min-w-0 flex-1">
                        <p class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">${escapeHtml(item.name)}</p>
                        <p class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">${ownerInfo}</p>
                    </div>
                </div>
                <div class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap ml-4 flex-shrink-0">
                    ${item.updated_at}
                </div>
            </div>
        `;
    }).join('');
}

function highlightSearchResult(index) {
    const items = document.querySelectorAll('.search-result-item');
    items.forEach((el, i) => {
        if (i === index) {
            el.classList.add('selected');
            el.scrollIntoView({ block: 'nearest' });
        } else {
            el.classList.remove('selected');
        }
    });
}

function handleSearchResultClick(index) {
    if (searchResultsData[index]) {
        selectSearchResult(searchResultsData[index]);
    }
}

function selectSearchResult(item) {
    closeSearchDropdown();
    if (item.is_folder) {
        window.location.href = item.folder_url;
    } else {
        previewFile(item.id, item.name, item.preview_type, item.file_url, item.formatted_size, item.updated_at);
    }
}

// Initialize on DOM load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearchAutocomplete);
} else {
    initSearchAutocomplete();
}


// ==============================================================================
// Multi-Select Manager & Batch Action Handlers
// ==============================================================================

const selectedItemIds = new Set();

function handleItemCheckboxChange(checkbox, event) {
    if (event) event.stopPropagation();
    const itemId = checkbox.dataset.itemId;
    if (!itemId) return;

    if (checkbox.checked) {
        selectedItemIds.add(itemId);
    } else {
        selectedItemIds.delete(itemId);
    }
    updateSelectionUI();
}

function handleRowClick(event, itemId) {
    if (event.target.closest('button, a, input, select, .dropdown')) return;
    if (event.ctrlKey || event.metaKey) {
        toggleItemSelection(itemId);
    }
}

function handleCardClick(event, itemId) {
    if (event.target.closest('button, a, input, select, .dropdown, .item-checkbox')) return;
    if (event.ctrlKey || event.metaKey) {
        toggleItemSelection(itemId);
    } else {
        if (selectedItemIds.has(itemId) && selectedItemIds.size === 1) {
            clearItemSelection();
        } else {
            selectedItemIds.clear();
            selectedItemIds.add(itemId);
            updateSelectionUI();
        }
    }
}

function toggleItemSelection(itemId) {
    if (selectedItemIds.has(itemId)) {
        selectedItemIds.delete(itemId);
    } else {
        selectedItemIds.add(itemId);
    }
    updateSelectionUI();
}

function selectAllItems(checked) {
    const checkboxes = document.querySelectorAll('.item-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checked;
        const id = cb.dataset.itemId;
        if (id) {
            if (checked) selectedItemIds.add(id);
            else selectedItemIds.delete(id);
        }
    });
    updateSelectionUI();
}

function clearItemSelection() {
    selectedItemIds.clear();
    const checkboxes = document.querySelectorAll('.item-checkbox');
    checkboxes.forEach(cb => cb.checked = false);
    const selectAll = document.getElementById('select-all-checkbox');
    if (selectAll) {
        selectAll.checked = false;
        selectAll.indeterminate = false;
    }
    updateSelectionUI();
}

// Cached DOM references for selection bar
let _cachedBatchBar = null;
let _cachedBatchCount = null;
let _cachedSelectAll = null;

function getBatchUIElements() {
    if (!_cachedBatchBar) _cachedBatchBar = document.getElementById('batch-action-bar');
    if (!_cachedBatchCount) _cachedBatchCount = document.getElementById('batch-selected-count');
    if (!_cachedSelectAll) _cachedSelectAll = document.getElementById('select-all-checkbox');
    return { bar: _cachedBatchBar, counter: _cachedBatchCount, selectAll: _cachedSelectAll };
}

function updateSelectionUI() {
    const count = selectedItemIds.size;
    const { bar, counter, selectAll } = getBatchUIElements();

    if (counter) counter.textContent = count;

    if (bar) {
        if (count > 0) {
            bar.classList.remove('hidden');
            requestAnimationFrame(() => {
                bar.classList.remove('scale-95', 'opacity-0');
                bar.classList.add('scale-100', 'opacity-100');
            });
        } else {
            bar.classList.remove('scale-100', 'opacity-100');
            bar.classList.add('scale-95', 'opacity-0');
            setTimeout(() => {
                if (selectedItemIds.size === 0) bar.classList.add('hidden');
            }, 200);
        }
    }

    const allCheckboxes = document.querySelectorAll('.item-checkbox');
    let allChecked = allCheckboxes.length > 0;
    for (let i = 0; i < allCheckboxes.length; i++) {
        const cb = allCheckboxes[i];
        const isSelected = selectedItemIds.has(cb.dataset.itemId);
        cb.checked = isSelected;
        if (!isSelected) allChecked = false;

        const row = cb.closest('.item-row');
        if (row) {
            row.classList.toggle('bg-blue-50/70', isSelected);
            row.classList.toggle('dark:bg-blue-900/20', isSelected);
        }

        const card = cb.closest('.item-card');
        if (card) {
            card.classList.toggle('ring-2', isSelected);
            card.classList.toggle('ring-blue-500', isSelected);
            card.classList.toggle('border-blue-500', isSelected);
            card.classList.toggle('bg-blue-50/40', isSelected);
            card.classList.toggle('dark:bg-[#004a77]/30', isSelected);
            const cardHeader = card.querySelector('.card-header-bar');
            if (cardHeader) {
                cardHeader.classList.toggle('bg-[#c2e7ff]', isSelected);
                cardHeader.classList.toggle('dark:bg-[#004a77]', isSelected);
                cardHeader.classList.toggle('text-blue-950', isSelected);
                cardHeader.classList.toggle('dark:text-white', isSelected);
                cardHeader.classList.toggle('bg-gray-50/80', !isSelected);
                cardHeader.classList.toggle('dark:bg-[#1e1f20]', !isSelected);
            }
        }
    }

    if (selectAll) {
        selectAll.checked = allChecked && allCheckboxes.length > 0;
        selectAll.indeterminate = count > 0 && !allChecked;
    }
}

async function sendBatchAction(endpoint, extraFields = {}, defaultMsg = 'Action completed.', reloadDelay = 450) {
    const itemIds = Array.from(selectedItemIds);
    if (!itemIds.length) {
        showToast('No items selected.', 'warning');
        return;
    }
    const formData = new FormData();
    itemIds.forEach(id => formData.append('item_ids[]', id));
    for (const [key, val] of Object.entries(extraFields)) {
        formData.append(key, val);
    }
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Batch operation failed.');

        showToast(data.message || defaultMsg, 'success');
        if (data.storage) updateStorageUI(data.storage);
        clearItemSelection();
        setTimeout(() => location.reload(), reloadDelay);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function executeBatchTrash() {
    await sendBatchAction('/api/batch/trash/', {}, 'Moved items to bin.', 500);
}

async function executeBatchRestore() {
    await sendBatchAction('/api/batch/restore/', {}, 'Restored items.', 500);
}

function executeBatchDelete() {
    const itemIds = Array.from(selectedItemIds);
    if (!itemIds.length) {
        showToast('No items selected.', 'warning');
        return;
    }

    const modal = document.getElementById('modal_confirm_delete');
    const title = document.getElementById('confirm_delete_title');
    const message = document.getElementById('confirm_delete_message');
    const btn = document.getElementById('confirm_delete_btn');

    title.textContent = `Delete ${itemIds.length} item(s) forever?`;
    message.textContent = `These ${itemIds.length} item(s) will be permanently deleted and cannot be recovered.`;

    btn.onclick = async () => {
        modal.close();
        await sendBatchAction('/api/batch/delete/', {}, 'Permanently deleted items.', 500);
    };

    modal.showModal();
}

async function executeBatchStar() {
    await sendBatchAction('/api/batch/star/', { action: 'toggle' }, 'Updated star status.', 400);
}

async function openBatchMoveModal() {
    if (!selectedItemIds.size) {
        showToast('No items selected.', 'warning');
        return;
    }
    const modal = document.getElementById('modal_move');
    const title = document.getElementById('move_modal_title');
    const desc = document.getElementById('move_modal_desc');
    const modeInput = document.getElementById('move_mode');
    const submitBtn = document.getElementById('move_submit_btn');
    const select = document.getElementById('move_destination_select');

    title.textContent = `Move ${selectedItemIds.size} item(s)`;
    desc.textContent = 'Select destination folder for selected items:';
    modeInput.value = 'batch_move';
    submitBtn.textContent = 'Move all here';

    select.innerHTML = '<option value="">Loading destinations...</option>';
    modal.showModal();

    try {
        const response = await fetch('/api/folders/available/');
        const data = await response.json();
        select.innerHTML = '';
        data.folders.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.id;
            opt.textContent = f.path;
            select.appendChild(opt);
        });
    } catch (e) {
        select.innerHTML = '<option value="">My Drive (Root)</option>';
    }
}

function executeBatchDownloadZip() {
    const itemIds = Array.from(selectedItemIds);
    if (!itemIds.length) {
        showToast('No items selected.', 'warning');
        return;
    }

    const params = new URLSearchParams();
    itemIds.forEach(id => params.append('item_ids', id));
    const url = `/api/batch/download-zip/?${params.toString()}`;

    const a = document.createElement('a');
    a.href = url;
    a.download = 'drive_items.zip';
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast(`Starting ZIP download of ${itemIds.length} item(s)...`, 'info');
}

// ==============================================================================
// Storage Plans & Admin Contact
// ==============================================================================
function openStoragePlansModal() {
    const modal = document.getElementById('modal_storage_plans');
    if (modal) {
        if (typeof modal.showModal === 'function') {
            try {
                modal.showModal();
                return;
            } catch (err) {}
        }
        modal.classList.add('modal-open');
        modal.setAttribute('open', '');
    }
}

function closeStoragePlansModal() {
    const modal = document.getElementById('modal_storage_plans');
    if (modal) {
        if (typeof modal.close === 'function') {
            try { modal.close(); } catch (err) {}
        }
        modal.classList.remove('modal-open');
        modal.removeAttribute('open');
    }
}

function openContactAdminModal(targetPlan) {
    const contactModal = document.getElementById('modal_contact_admin');
    const label = document.getElementById('target_storage_plan_label');
    const mailLink = document.getElementById('send_admin_email_link');
    const emailElem = document.getElementById('admin_email_address');
    const adminEmail = (emailElem && emailElem.textContent.trim()) ? emailElem.textContent.trim() : 'admin@gmail.com';

    if (label && targetPlan) {
        label.textContent = targetPlan;
    }

    if (mailLink && targetPlan) {
        const subject = encodeURIComponent(`Storage Limit Upgrade Request: ${targetPlan}`);
        const body = encodeURIComponent(`Hi Administrator,\n\nI would like to request an upgrade to the ${targetPlan} storage plan for my account.\n\nThank you!`);
        mailLink.href = `mailto:${encodeURIComponent(adminEmail)}?subject=${subject}&body=${body}`;
    }

    if (contactModal) {
        contactModal.showModal();
    }
}

async function copyAdminEmail() {
    const emailElem = document.getElementById('admin_email_address');
    const copyBtn = document.getElementById('copy_email_btn');
    const email = emailElem ? emailElem.textContent.trim() : 'admin@gmail.com';

    try {
        await navigator.clipboard.writeText(email);
        showToast('Admin email copied to clipboard!', 'success');
        if (copyBtn) {
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '<span>Copied!</span>';
            setTimeout(() => { copyBtn.innerHTML = originalHTML; }, 2000);
        }
    } catch (err) {
        showToast(`Admin email: ${email}`, 'info');
    }
}

// ==============================================================================
// User Account, Name & Password Management
// ==============================================================================
function openAccountModal(tab = 'profile') {
    const modal = document.getElementById('modal_account');
    if (modal) {
        switchAccountTab(tab);
        modal.showModal();
    }
}

function switchAccountTab(tab) {
    const btnProfile = document.getElementById('tab-btn-profile');
    const btnPassword = document.getElementById('tab-btn-password');
    const contentProfile = document.getElementById('tab-content-profile');
    const contentPassword = document.getElementById('tab-content-password');

    if (!btnProfile || !btnPassword || !contentProfile || !contentPassword) return;

    if (tab === 'password') {
        btnPassword.classList.add('border-[#1a73e8]', 'text-[#1a73e8]', 'dark:text-[#8ab4f8]');
        btnPassword.classList.remove('border-transparent', 'text-gray-500', 'dark:text-gray-400');

        btnProfile.classList.remove('border-[#1a73e8]', 'text-[#1a73e8]', 'dark:text-[#8ab4f8]');
        btnProfile.classList.add('border-transparent', 'text-gray-500', 'dark:text-gray-400');

        contentPassword.classList.remove('hidden');
        contentProfile.classList.add('hidden');
    } else {
        btnProfile.classList.add('border-[#1a73e8]', 'text-[#1a73e8]', 'dark:text-[#8ab4f8]');
        btnProfile.classList.remove('border-transparent', 'text-gray-500', 'dark:text-gray-400');

        btnPassword.classList.remove('border-[#1a73e8]', 'text-[#1a73e8]', 'dark:text-[#8ab4f8]');
        btnPassword.classList.add('border-transparent', 'text-gray-500', 'dark:text-gray-400');

        contentProfile.classList.remove('hidden');
        contentPassword.classList.add('hidden');
    }
}

async function submitUpdateProfile(event) {
    event.preventDefault();
    const form = event.target;
    const btn = document.getElementById('btn-save-profile');
    const originalText = btn ? btn.textContent : 'Save';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading loading-spinner loading-xs"></span> Saving...';
    }

    const formData = new FormData(form);

    try {
        const response = await fetch('/api/account/profile/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to update profile.');
        }

        showToast(data.message || 'Profile updated successfully!', 'success');

        // Update UI dynamically across the page
        const modalTitle = document.getElementById('account-modal-title');
        const modalSubtitle = document.getElementById('account-modal-email-preview');
        const modalAvatar = document.getElementById('account-modal-avatar-preview');
        const usernameInput = document.getElementById('profile_username');
        const emailInput = document.getElementById('profile_email');
        const navFullname = document.getElementById('nav-user-fullname');
        const navEmail = document.getElementById('nav-user-email');
        const navAvatar = document.getElementById('nav-dropdown-avatar');
        const navAvatarInit = document.getElementById('nav-avatar-initial');

        if (modalTitle) modalTitle.textContent = data.full_name;
        if (modalSubtitle) modalSubtitle.textContent = data.email || data.username;
        if (modalAvatar) modalAvatar.textContent = data.initial;
        if (usernameInput && data.username) usernameInput.value = data.username;
        if (emailInput && data.email) emailInput.value = data.email;
        if (navFullname) navFullname.textContent = data.full_name;
        if (navEmail) navEmail.textContent = data.email || data.username;
        if (navAvatar) navAvatar.textContent = data.initial;
        if (navAvatarInit) navAvatarInit.textContent = data.initial;

        if (data.admin_email) {
            const adminEmailElem = document.getElementById('admin_email_address');
            if (adminEmailElem) {
                adminEmailElem.textContent = data.admin_email;
            }
            const mailLink = document.getElementById('send_admin_email_link');
            if (mailLink && mailLink.href.startsWith('mailto:')) {
                mailLink.href = mailLink.href.replace(/mailto:[^?]+/, `mailto:${encodeURIComponent(data.admin_email)}`);
            }
        }

        setTimeout(() => {
            document.getElementById('modal_account')?.close();
        }, 700);
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

async function submitChangePassword(event) {
    event.preventDefault();
    const form = event.target;
    const btn = document.getElementById('btn-save-password');
    const originalText = btn ? btn.textContent : 'Update Password';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading loading-spinner loading-xs"></span> Updating...';
    }

    const formData = new FormData(form);

    try {
        const response = await fetch('/api/account/change-password/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to update password.');
        }

        showToast(data.message || 'Password updated successfully!', 'success');
        form.reset();

        setTimeout(() => {
            document.getElementById('modal_account')?.close();
        }, 700);
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}


