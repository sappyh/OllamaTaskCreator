document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let currentVault = null;
    let currentNote = null;
    let editingNoteContent = '';
    let saveTimeout = null;

    // --- DOM Elements ---
    const vaultListEl = document.getElementById('vault-list');
    const noteListEl = document.getElementById('note-list');
    
    const currentVaultLabel = document.getElementById('current-vault-label');
    const currentNoteTitle = document.getElementById('current-note-title');
    
    const editorContainer = document.getElementById('editor-container');
    const emptyState = document.getElementById('empty-state');
    const noteActions = document.getElementById('note-actions');
    
    const markdownEditor = document.getElementById('markdown-editor');
    const markdownPreview = document.getElementById('markdown-preview');
    
    const newVaultBtn = document.getElementById('new-vault-btn');
    const newNoteBtn = document.getElementById('new-note-btn');
    const saveNoteBtn = document.getElementById('save-note-btn');
    const deleteNoteBtn = document.getElementById('delete-note-btn');
    const orchestratorSyncBtn = document.getElementById('orchestrator-sync-btn');
    const orchestratorStatusText = document.getElementById('orchestrator-status-text');
    const orchestratorStatusDot = orchestratorSyncBtn.querySelector('.status-dot');
    
    // Modals
    const newVaultModal = document.getElementById('new-vault-modal');
    const newVaultInput = document.getElementById('new-vault-input');
    const submitVaultBtn = document.getElementById('submit-vault-btn');
    const cancelVaultBtn = document.getElementById('cancel-vault-btn');
    
    const newNoteModal = document.getElementById('new-note-modal');
    const newNoteInput = document.getElementById('new-note-input');
    const submitNoteBtn = document.getElementById('submit-note-btn');
    const cancelNoteBtn = document.getElementById('cancel-note-btn');

    // --- API Calls ---
    async function fetchVaults() {
        try {
            const res = await fetch('/vaults');
            if (res.ok) {
                const vaults = await res.json();
                renderVaults(vaults);
            }
        } catch (err) {
            console.error('Failed to fetch vaults:', err);
        }
    }

    async function fetchNotes(vaultPath) {
        try {
            const res = await fetch(`/notes?vault_path=${encodeURIComponent(vaultPath)}`);
            if (res.ok) {
                const notes = await res.json();
                renderNotes(notes);
            } else {
                noteListEl.innerHTML = '<div class="empty-state-text">Failed to load notes</div>';
            }
        } catch (err) {
            console.error('Failed to fetch notes:', err);
        }
    }
    
    async function pollOrchestratorStatus() {
        try {
            const res = await fetch('/orchestrator/status');
            if (res.ok) {
                const state = await res.json();
                updateOrchestratorUI(state);
            } else {
                updateOrchestratorUI({ is_connected: false, current_status: "Error" });
            }
        } catch (err) {
            console.error('Failed to fetch orchestrator status:', err);
            updateOrchestratorUI({ is_connected: false, current_status: "Disconnected" });
        }
    }
    
    async function triggerOrchestratorGenerate() {
        if (!currentVault) {
            alert("No vault selected to process!");
            return;
        }
        
        try {
            orchestratorSyncBtn.disabled = true;
            const originalText = orchestratorStatusText.textContent;
            orchestratorStatusText.textContent = "Initiating...";
            
            const res = await fetch('/orchestrator/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vault_path: currentVault })
            });
            
            if (res.ok) {
                orchestratorStatusText.textContent = "Sent!";
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail || 'Could not initiate task sync'}`);
                orchestratorStatusText.textContent = originalText;
                orchestratorSyncBtn.disabled = false;
            }
        } catch (err) {
            console.error('Failed to trigger task generation:', err);
            orchestratorSyncBtn.disabled = false;
        }
    }

    async function createVault(path) {
        try {
            const res = await fetch('/vault', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vault_path: path })
            });
            if (res.ok) {
                await fetchVaults();
                selectVault(path);
                closeModal(newVaultModal);
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail || 'Could not create vault'}`);
            }
        } catch (err) {
            console.error('Failed to create vault:', err);
        }
    }

    async function createNote(filename) {
        if (!currentVault) return;
        if (!filename.endsWith('.md')) filename += '.md';
        
        try {
            const res = await fetch('/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    vault_path: currentVault,
                    filename: filename,
                    content: "# " + filename.replace('.md', '') + "\n\nStart typing..."
                })
            });
            
            if (res.ok) {
                await fetchNotes(currentVault);
                selectNote(filename);
                closeModal(newNoteModal);
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail || 'Could not create note'}`);
            }
        } catch (err) {
            console.error('Failed to create note:', err);
        }
    }

    async function loadNote(filename) {
        if (!currentVault) return;
        try {
            const res = await fetch(`/notes/${encodeURIComponent(filename)}?vault_path=${encodeURIComponent(currentVault)}`);
            if (res.ok) {
                const data = await res.json();
                editingNoteContent = data.content;
                markdownEditor.value = editingNoteContent;
                renderMarkdown();
            }
        } catch (err) {
            console.error('Failed to load note:', err);
        }
    }

    async function saveNote() {
        if (!currentVault || !currentNote) return;
        
        const content = markdownEditor.value;
        const previousText = saveNoteBtn.innerText;
        saveNoteBtn.innerText = 'Saving...';
        saveNoteBtn.disabled = true;
        
        try {
            const res = await fetch(`/notes/${encodeURIComponent(currentNote)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vault_path: currentVault,
                    content: content
                })
            });
            
            if (res.ok) {
                saveNoteBtn.innerText = 'Saved!';
                setTimeout(() => {
                    saveNoteBtn.innerText = previousText;
                    saveNoteBtn.disabled = false;
                }, 2000);
            }
        } catch (err) {
            console.error('Failed to save note:', err);
            saveNoteBtn.innerText = 'Error';
            saveNoteBtn.disabled = false;
        }
    }
    
    async function deleteNote() {
        if (!currentVault || !currentNote) return;
        
        if (!confirm(`Are you sure you want to delete ${currentNote}? This cannot be undone.`)) {
            return;
        }
        
        try {
            const res = await fetch(`/notes/${encodeURIComponent(currentNote)}?vault_path=${encodeURIComponent(currentVault)}`, {
                method: 'DELETE'
            });
            
            if (res.ok) {
                await fetchNotes(currentVault);
                deselectNote();
            }
        } catch (err) {
            console.error('Failed to delete note:', err);
        }
    }

    // --- UI Rendering ---
    function renderVaults(vaults) {
        vaultListEl.innerHTML = '';
        if (vaults.length === 0) {
            vaultListEl.innerHTML = '<div class="empty-state-text">No vaults tracked yet</div>';
            return;
        }
        
        vaults.forEach(vaultPath => {
            const div = document.createElement('div');
            div.className = `nav-item ${currentVault === vaultPath ? 'active' : ''}`;
            const vaultName = vaultPath.split(/[/\\]/).pop() || vaultPath;
            div.textContent = vaultName;
            div.title = vaultPath;
            
            div.addEventListener('click', () => selectVault(vaultPath));
            vaultListEl.appendChild(div);
        });
    }

    function renderNotes(notes) {
        noteListEl.innerHTML = '';
        if (notes.length === 0) {
            noteListEl.innerHTML = '<div class="empty-state-text">No notes in this vault</div>';
            return;
        }
        
        notes.forEach(noteName => {
            const div = document.createElement('div');
            div.className = `nav-item ${currentNote === noteName ? 'active' : ''}`;
            div.textContent = noteName;
            div.title = noteName;
            
            div.addEventListener('click', () => selectNote(noteName));
            noteListEl.appendChild(div);
        });
    }

    function selectVault(vaultPath) {
        currentVault = vaultPath;
        deselectNote();
        
        currentVaultLabel.textContent = vaultPath.split(/[/\\]/).pop();
        currentVaultLabel.classList.remove('hidden');
        newNoteBtn.disabled = false;
        
        fetchVaults(); // Re-render to highlight active
        fetchNotes(vaultPath);
    }

    function selectNote(noteName) {
        currentNote = noteName;
        currentNoteTitle.textContent = noteName;
        
        emptyState.classList.add('hidden');
        editorContainer.classList.remove('hidden');
        noteActions.classList.remove('hidden');
        
        // Re-render notes to highlight active
        const noteItems = noteListEl.querySelectorAll('.nav-item');
        noteItems.forEach(el => {
            if(el.textContent === noteName) el.classList.add('active');
            else el.classList.remove('active');
        });
        
        loadNote(noteName);
    }

    function deselectNote() {
        currentNote = null;
        currentNoteTitle.textContent = 'Welcome';
        
        emptyState.classList.remove('hidden');
        editorContainer.classList.add('hidden');
        noteActions.classList.add('hidden');
        
        const noteItems = noteListEl.querySelectorAll('.nav-item');
        noteItems.forEach(el => el.classList.remove('active'));
    }

    function renderMarkdown() {
        const raw = markdownEditor.value;
        const html = marked.parse(raw);
        const cleanHtml = DOMPurify.sanitize(html);
        markdownPreview.innerHTML = cleanHtml;
    }

    function updateOrchestratorUI(state) {
        orchestratorStatusDot.className = 'status-dot'; // reset
        
        if (!state.is_connected) {
            orchestratorStatusDot.classList.add('disconnected');
            orchestratorStatusText.textContent = 'Disconnected';
            orchestratorSyncBtn.disabled = true;
            orchestratorSyncBtn.title = "Start the Orchestrator service to sync tasks";
            return;
        }
        
        if (state.current_status === "Processing") {
            orchestratorStatusDot.classList.add('processing');
            orchestratorStatusText.textContent = 'Syncing Tasks...';
            orchestratorSyncBtn.disabled = true;
            orchestratorSyncBtn.title = "Tasks are currently being pushed to Vikunja";
        } else {
            orchestratorStatusDot.classList.add('connected');
            orchestratorStatusText.textContent = 'Sync Tasks';
            
            // Only enable button if a vault is actually selected
            if (currentVault) {
                orchestratorSyncBtn.disabled = false;
                orchestratorSyncBtn.title = "Process all notes in this vault via Ollama";
            } else {
                orchestratorSyncBtn.disabled = true;
                orchestratorSyncBtn.title = "Select a vault first";
            }
        }
    }

    function openModal(modalEl, inputEl) {
        modalEl.classList.remove('hidden');
        if (inputEl) {
            inputEl.value = '';
            inputEl.focus();
        }
    }

    function closeModal(modalEl) {
        modalEl.classList.add('hidden');
    }

    // --- Event Listeners ---
    newVaultBtn.addEventListener('click', () => openModal(newVaultModal, newVaultInput));
    cancelVaultBtn.addEventListener('click', () => closeModal(newVaultModal));
    submitVaultBtn.addEventListener('click', () => {
        const path = newVaultInput.value.trim();
        if (path) createVault(path);
    });
    newVaultInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitVaultBtn.click();
        if (e.key === 'Escape') cancelVaultBtn.click();
    });

    newNoteBtn.addEventListener('click', () => openModal(newNoteModal, newNoteInput));
    cancelNoteBtn.addEventListener('click', () => closeModal(newNoteModal));
    submitNoteBtn.addEventListener('click', () => {
        const filename = newNoteInput.value.trim();
        if (filename) createNote(filename);
    });
    newNoteInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitNoteBtn.click();
        if (e.key === 'Escape') cancelNoteBtn.click();
    });

    saveNoteBtn.addEventListener('click', saveNote);
    deleteNoteBtn.addEventListener('click', deleteNote);
    orchestratorSyncBtn.addEventListener('click', triggerOrchestratorGenerate);

    markdownEditor.addEventListener('input', () => {
        renderMarkdown();
        // Auto-save debounce (optional)
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            saveNoteBtn.classList.add('secondary-btn');
            saveNoteBtn.classList.remove('primary-btn');
        }, 500);
    });

    // --- Init ---
    fetchVaults();
    pollOrchestratorStatus();
    setInterval(pollOrchestratorStatus, 2000); // Poll ZMQ bridge every 2s
});
