// --- Error Handling ---
window.onerror = function(msg, url, line, col, error) {
    if (msg.includes('ResizeObserver')) return; // Ignore noisy ResizeObserver errors
    alert(`JS Error: ${msg}\nat ${line}:${col}\n${url}`);
    return false;
};

document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let currentVault = null;
    let currentNote = null;
    let currentTasks = [];
    let currentTagFilter = null;
    let editingNoteContent = '';
    let saveTimeout = null;
    let activeView = 'notes'; // 'notes' or 'tasks'
    let lastOrchestratorStatus = null;

    // --- DOM Elements ---
    const vaultListEl = document.getElementById('vault-list');
    const noteListEl = document.getElementById('note-list');
    const tagListEl = document.getElementById('tag-list');
    const taskBoardEl = document.getElementById('task-board');
    
    const currentVaultLabel = document.getElementById('current-vault-label');
    const currentNoteTitle = document.getElementById('current-note-title');
    
    const editorContainer = document.getElementById('editor-container');
    const taskBoardContainer = document.getElementById('task-board-container');
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
    const orchestratorStatusDot = orchestratorSyncBtn ? orchestratorSyncBtn.querySelector('.status-dot') : null;
    
    const viewNotesBtn = document.getElementById('view-notes-btn');
    const viewTasksBtn = document.getElementById('view-tasks-btn');

    // Modals
    const newVaultModal = document.getElementById('new-vault-modal');
    const newVaultInput = document.getElementById('new-vault-input');
    const submitVaultBtn = document.getElementById('submit-vault-btn');
    const cancelVaultBtn = document.getElementById('cancel-vault-btn');
    
    const newNoteModal = document.getElementById('new-note-modal');
    const newNoteInput = document.getElementById('new-note-input');
    const submitNoteBtn = document.getElementById('submit-note-btn');
    const cancelNoteBtn = document.getElementById('cancel-note-btn');

    const newTaskModal = document.getElementById('new-task-modal');
    const taskNameInput = document.getElementById('task-name-input');
    const taskDescInput = document.getElementById('task-desc-input');
    const taskPriorityInput = document.getElementById('task-priority-input');
    const taskDeadlineInput = document.getElementById('task-deadline-input');
    const taskTagsInput = document.getElementById('task-tags-input');
    const submitTaskBtn = document.getElementById('submit-task-btn');
    const cancelTaskBtn = document.getElementById('cancel-task-btn');

    let editingTaskId = null;
    let isMobile = window.innerWidth <= 768;

    // --- Mobile Controls ---
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    function toggleSidebar() {
        sidebar.classList.toggle('open');
        sidebarOverlay.classList.toggle('active');
    }

    function closeSidebarOnMobile() {
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
        }
    }

    console.log('App v10 Init');

    // --- API Calls ---
    async function fetchVaults() {
        if (!vaultListEl) return;
        vaultListEl.innerHTML = '<div class="empty-state-text">Loading...</div>';
        try {
            const res = await fetch('/vaults');
            if (res.ok) {
                const vaults = await res.json();
                renderVaults(vaults);
            } else {
                vaultListEl.innerHTML = '<div class="empty-state-text">Fetch failed</div>';
            }
        } catch (err) {
            vaultListEl.innerHTML = '<div class="empty-state-text">Connection error</div>';
        }
    }

    async function fetchNotes(vaultPath) {
        if (!vaultPath || !noteListEl) return;
        noteListEl.innerHTML = '<div class="empty-state-text">Loading...</div>';
        try {
            const res = await fetch(`/notes?vault_path=${encodeURIComponent(vaultPath)}`);
            if (res.ok) {
                const notes = await res.json();
                renderNotes(notes);
            } else {
                noteListEl.innerHTML = '<div class="empty-state-text">Failed to load notes</div>';
            }
        } catch (err) {
            noteListEl.innerHTML = '<div class="empty-state-text">Error loading notes</div>';
        }
    }

    async function fetchTasks(vaultPath) {
        if (!vaultPath) return;
        try {
            const res = await fetch(`/vaults/tasks?vault_path=${encodeURIComponent(vaultPath)}`);
            if (res.ok) {
                currentTasks = await res.json();
                renderTasks();
            }
        } catch (err) {}
    }
    
    async function pollOrchestratorStatus() {
        try {
            const res = await fetch('/orchestrator/status');
            if (res.ok) {
                const state = await res.json();
                
                // Auto-refresh tasks if sync just finished
                if (lastOrchestratorStatus === 'Processing' && state.current_status === 'Idle' && currentVault) {
                    console.log('Sync finished, refreshing tasks...');
                    fetchTasks(currentVault);
                }
                
                lastOrchestratorStatus = state.current_status;
                updateOrchestratorUI(state);
            }
        } catch (err) {}
    }
    
    async function triggerOrchestratorGenerate() {
        if (!currentVault || !orchestratorSyncBtn || !orchestratorStatusText) return;
        try {
            orchestratorSyncBtn.disabled = true;
            orchestratorStatusText.textContent = "Initiating...";
            const res = await fetch('/orchestrator/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vault_path: currentVault })
            });
            if (res.ok) {
                orchestratorStatusText.textContent = "Sent!";
            } else {
                pollOrchestratorStatus();
            }
        } catch (err) {
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
                const data = await res.json();
                closeModal(newVaultModal);
                await fetchVaults();
                selectVault(data.path || path);
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail || 'Could not create vault'}`);
            }
        } catch (err) {}
    }

    async function deleteVault(vaultPath) {
        if (!confirm(`Delete vault: ${vaultPath}?`)) return;
        try {
            const res = await fetch(`/vault?vault_path=${encodeURIComponent(vaultPath)}`, { method: 'DELETE' });
            if (res.ok) {
                if (currentVault === vaultPath) {
                    currentVault = null;
                    deselectNote();
                    if (currentVaultLabel) currentVaultLabel.classList.add('hidden');
                    if (noteListEl) noteListEl.innerHTML = '<div class="empty-state-text">Select a vault first</div>';
                    if (newNoteBtn) newNoteBtn.disabled = true;
                }
                await fetchVaults();
            }
        } catch (err) {}
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
                closeModal(newNoteModal);
                await fetchNotes(currentVault);
                selectNote(filename);
            }
        } catch (err) {}
    }

    async function deleteNoteSpecific(filename) {
        if (!currentVault || !confirm(`Delete note: ${filename}?`)) return;
        try {
            const res = await fetch(`/notes/${encodeURIComponent(filename)}?vault_path=${encodeURIComponent(currentVault)}`, { method: 'DELETE' });
            if (res.ok) {
                if (currentNote === filename) deselectNote();
                await fetchNotes(currentVault);
            }
        } catch (err) {}
    }

    async function loadNote(filename) {
        if (!currentVault || !markdownEditor) return;
        try {
            const res = await fetch(`/notes/${encodeURIComponent(filename)}?vault_path=${encodeURIComponent(currentVault)}`);
            if (res.ok) {
                const data = await res.json();
                editingNoteContent = data.content;
                markdownEditor.value = editingNoteContent;
                renderMarkdown();
            }
        } catch (err) {}
    }

    async function saveNote() {
        if (!currentVault || !currentNote || !markdownEditor || !saveNoteBtn) return;
        const content = markdownEditor.value;
        const previousText = saveNoteBtn.innerText;
        saveNoteBtn.innerText = 'Saving...';
        saveNoteBtn.disabled = true;
        try {
            const res = await fetch(`/notes/${encodeURIComponent(currentNote)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vault_path: currentVault, content: content })
            });
            if (res.ok) {
                saveNoteBtn.innerText = 'Saved!';
                setTimeout(() => {
                    saveNoteBtn.innerText = 'Save Note';
                    saveNoteBtn.disabled = false;
                }, 2000);
            }
        } catch (err) {
            saveNoteBtn.innerText = 'Error';
            saveNoteBtn.disabled = false;
        }
    }

    async function upsertTask(overrideData = null) {
        if (!currentVault) return;
        let taskData;
        if (overrideData) {
            taskData = overrideData;
        } else {
            if (!taskNameInput || !taskDescInput || !taskPriorityInput || !taskDeadlineInput || !taskTagsInput) return;
            taskData = {
                id: editingTaskId || undefined,
                name: taskNameInput.value.trim(),
                description: taskDescInput.value.trim(),
                priority: taskPriorityInput.value,
                status: 'TODO',
                deadline: taskDeadlineInput.value || null,
                tags: taskTagsInput.value.split(',').map(tag => tag.trim()).filter(tag => tag !== "")
            };
        }
        
        if (!taskData.name) {
            alert("Task name is required");
            return;
        }
        try {
            const res = await fetch(`/vaults/tasks?vault_path=${encodeURIComponent(currentVault)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
            if (res.ok) {
                if (!overrideData) closeModal(newTaskModal);
                await fetchTasks(currentVault);
            }
        } catch (err) {}
    }

    async function deleteTask(taskId) {
        if (!currentVault) return;
        try {
            const res = await fetch(`/vaults/tasks/${taskId}?vault_path=${encodeURIComponent(currentVault)}`, { method: 'DELETE' });
            if (res.ok) await fetchTasks(currentVault);
        } catch (err) {}
    }

    // --- UI Rendering ---
    function renderVaults(vaults) {
        if (!vaultListEl) return;
        vaultListEl.innerHTML = '';
        if (vaults.length === 0) {
            vaultListEl.innerHTML = '<div class="empty-state-text">No vaults found</div>';
            return;
        }
        vaults.forEach(vaultPath => {
            // Filter out internal hidden dirs if they managed to sneak in
            if (vaultPath.includes('.OllamaCreator')) {
                const parts = vaultPath.split(/[/\\]/).filter(p => p !== "");
                const lastPart = parts.pop();
                if (lastPart === '.OllamaCreator') return; // Skip the base dir itself
            }

            const div = document.createElement('div');
            div.className = `nav-item vault-item ${currentVault === vaultPath ? 'active' : ''}`;
            div.dataset.path = vaultPath;
            
            const vaultName = vaultPath.split(/[/\\]/).filter(p => p !== "").pop() || vaultPath;
            div.innerHTML = `
                <span class="vault-name" title="${vaultPath}">${vaultName}</span>
                <button class="icon-btn delete-vault-btn" title="Delete Vault">🗑</button>
            `;
            vaultListEl.appendChild(div);
        });
    }

    function renderNotes(notes) {
        if (!noteListEl) return;
        noteListEl.innerHTML = '';
        if (notes.length === 0) {
            noteListEl.innerHTML = '<div class="empty-state-text">No notes in this vault</div>';
            return;
        }
        notes.forEach(noteName => {
            const div = document.createElement('div');
            div.className = `nav-item note-item ${currentNote === noteName ? 'active' : ''}`;
            div.dataset.name = noteName;
            div.innerHTML = `<span class="note-name" title="${noteName}">${noteName}</span><button class="icon-btn delete-note-btn" title="Delete Note">🗑</button>`;
            noteListEl.appendChild(div);
        });
    }

    function renderTasks() {
        if (!taskBoardEl) return;
        
        // Extract and render tags for the sidebar
        renderTags();
        
        const filteredTasks = currentTagFilter 
            ? currentTasks.filter(t => t.tags && t.tags.includes(currentTagFilter)) 
            : currentTasks;

        taskBoardEl.innerHTML = `
            <div class="task-list-header-row">
                <div></div>
                <div>TASK NAME ${currentTagFilter ? `<span class="badge" style="font-size: 0.6rem; margin-left: 0.5rem;">TAG: ${currentTagFilter} <span style="cursor: pointer; color: var(--accent-danger);" onclick="window.clearTagFilter()">×</span></span>` : ''}</div>
                <div>STATUS</div>
                <div style="text-align: center;">PRIORITY</div>
                <div>DEADLINE</div>
                <div style="text-align: right;">ACTIONS</div>
            </div>
        `;
        
        if (filteredTasks.length === 0) {
            taskBoardEl.innerHTML += '<div class="empty-state-text" style="padding: 2rem; text-align: center;">No tasks found matching the filter.</div>';
            return;
        }

        filteredTasks.forEach((task, index) => {
            const item = document.createElement('div');
            const statusClass = `status-${(task.status || 'TODO').toLowerCase()}`;
            item.className = `task-list-item ${statusClass}`;
            item.id = `task-${task.id}`;
            
            const taskKey = `T-${index + 1}`;
            
            item.innerHTML = `
                <div class="task-list-header">
                    <div class="task-key">${taskKey}</div>
                    <span class="task-list-name">${task.name}</span>
                    <div>
                        <select class="task-status-select" style="width: 100%;">
                            <option value="TODO" ${task.status === 'TODO' ? 'selected' : ''}>TODO</option>
                            <option value="DOING" ${task.status === 'DOING' ? 'selected' : ''}>DOING</option>
                            <option value="DONE" ${task.status === 'DONE' ? 'selected' : ''}>DONE</option>
                        </select>
                    </div>
                    <div>
                        <span class="task-priority-badge priority-${task.priority.toLowerCase()}">${task.priority}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-tertiary);">
                        ${task.deadline || '-'}
                    </div>
                    <div class="task-list-actions">
                        <button class="icon-btn edit-task-btn" title="Edit">✎</button>
                        <button class="icon-btn delete-task-btn" title="Delete">🗑</button>
                    </div>
                </div>
                <div class="task-expanded-content">
                    <div class="task-meta" style="margin-bottom: 0.5rem;">
                        <div class="task-tags">${task.tags.map(tag => `<span class="tag-badge">${tag}</span>`).join('')}</div>
                    </div>
                    <p style="white-space: pre-wrap; font-size: 0.9rem; border-left: 2px solid var(--border-color); padding-left: 1rem; margin-top: 0.5rem;">${task.description || 'No description provided.'}</p>
                </div>
            `;
            
            // Interaction logic
            item.addEventListener('click', (e) => {
                if (e.target.closest('.task-status-select') || e.target.closest('.task-list-actions')) return;
                item.classList.toggle('expanded');
            });
            
            const statusSelect = item.querySelector('.task-status-select');
            statusSelect.addEventListener('change', (e) => {
                task.status = e.target.value;
                upsertTask(task);
            });
            
            const editBtn = item.querySelector('.edit-task-btn');
            const delBtn = item.querySelector('.delete-task-btn');
            
            if (editBtn) editBtn.addEventListener('click', (e) => { e.stopPropagation(); openEditTaskModal(task); });
            if (delBtn) delBtn.addEventListener('click', (e) => { e.stopPropagation(); deleteTask(task.id); });
            
            taskBoardEl.appendChild(item);
        });
    }

    function renderTags() {
        if (!tagListEl) return;
        tagListEl.innerHTML = '';
        
        const uniqueTags = new Set();
        currentTasks.forEach(t => {
            if (t.tags) t.tags.forEach(tag => uniqueTags.add(tag));
        });

        if (uniqueTags.size === 0) {
            tagListEl.innerHTML = '<div class="empty-state-text">No tags found</div>';
            return;
        }

        // Add "All Tasks" option if filter is active
        if (currentTagFilter) {
            const allBtn = document.createElement('div');
            allBtn.className = 'nav-item';
            allBtn.innerHTML = '<span>All Tasks</span>';
            allBtn.addEventListener('click', () => clearTagFilter());
            tagListEl.appendChild(allBtn);
        }

        uniqueTags.forEach(tag => {
            const div = document.createElement('div');
            div.className = `nav-item tag-item ${currentTagFilter === tag ? 'active' : ''}`;
            div.innerHTML = `<span class="tag-name">#${tag}</span>`;
            div.addEventListener('click', () => selectTag(tag));
            tagListEl.appendChild(div);
        });
    }

    function selectTag(tag) {
        currentTagFilter = tag;
        switchView('tasks');
        renderTasks();
        closeSidebarOnMobile();
    }

    window.clearTagFilter = function() {
        currentTagFilter = null;
        renderTasks();
    };

    function switchView(view) {
        activeView = view;
        if (view === 'notes') {
            if (viewNotesBtn) viewNotesBtn.classList.add('active');
            if (viewTasksBtn) viewTasksBtn.classList.remove('active');
            if (currentNote) {
                if (editorContainer) editorContainer.classList.remove('hidden');
                if (emptyState) emptyState.classList.add('hidden');
                if (noteActions) noteActions.classList.remove('hidden');
            } else {
                if (editorContainer) editorContainer.classList.add('hidden');
                if (emptyState) emptyState.classList.remove('hidden');
                if (noteActions) noteActions.classList.add('hidden');
            }
            if (taskBoardContainer) taskBoardContainer.classList.add('hidden');
        } else {
            if (viewNotesBtn) viewNotesBtn.classList.remove('active');
            if (viewTasksBtn) viewTasksBtn.classList.add('active');
            if (editorContainer) editorContainer.classList.add('hidden');
            if (emptyState) emptyState.classList.add('hidden');
            if (noteActions) noteActions.classList.add('hidden');
            if (taskBoardContainer) taskBoardContainer.classList.remove('hidden');
            if (currentVault) fetchTasks(currentVault);
        }
    }

    function scrollToTask(taskId) {
        const el = document.getElementById(`task-${taskId}`);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('expanded');
        }
    }

    function selectVault(vaultPath) {
        currentVault = vaultPath;
        deselectNote();
        const vaultName = vaultPath.split(/[/\\]/).filter(p => p !== "").pop() || vaultPath;
        if (currentVaultLabel) {
            currentVaultLabel.textContent = vaultName;
            currentVaultLabel.classList.remove('hidden');
        }
        if (newNoteBtn) newNoteBtn.disabled = false;
        renderVaultsHighlightOnly(vaultPath);
        fetchNotes(vaultPath);
        fetchTasks(vaultPath);
        closeSidebarOnMobile();
    }

    function renderVaultsHighlightOnly(activePath) {
        if (!vaultListEl) return;
        const items = vaultListEl.querySelectorAll('.vault-item');
        items.forEach(item => {
            if (item.dataset.path === activePath) item.classList.add('active');
            else item.classList.remove('active');
        });
    }

    function selectNote(noteName) {
        currentNote = noteName;
        if (currentNoteTitle) currentNoteTitle.textContent = noteName;
        if (emptyState) emptyState.classList.add('hidden');
        if (editorContainer) editorContainer.classList.remove('hidden');
        if (noteActions) noteActions.classList.remove('hidden');
        if (noteListEl) {
            const noteItems = noteListEl.querySelectorAll('.note-item');
            noteItems.forEach(el => {
                if(el.dataset.name === noteName) el.classList.add('active');
                else el.classList.remove('active');
            });
        }
        loadNote(noteName);
        closeSidebarOnMobile();
    }

    function deselectNote() {
        currentNote = null;
        if (currentNoteTitle) currentNoteTitle.textContent = 'Welcome';
        if (emptyState) emptyState.classList.remove('hidden');
        if (editorContainer) editorContainer.classList.add('hidden');
        if (noteActions) noteActions.classList.add('hidden');
        if (noteListEl) {
            const noteItems = noteListEl.querySelectorAll('.note-item');
            noteItems.forEach(el => el.classList.remove('active'));
        }
    }

    function renderMarkdown() {
        if (typeof marked === 'undefined') return;
        const raw = markdownEditor ? markdownEditor.value : '';
        const html = marked.parse(raw);
        const cleanHtml = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
        if (markdownPreview) markdownPreview.innerHTML = cleanHtml;
    }

    function updateOrchestratorUI(state) {
        if (!orchestratorStatusDot || !orchestratorStatusText || !orchestratorSyncBtn) return;
        orchestratorStatusDot.className = 'status-dot'; 
        if (!state.is_connected) {
            orchestratorStatusDot.classList.add('disconnected');
            orchestratorStatusText.textContent = 'Disconnected';
            orchestratorSyncBtn.disabled = true;
            return;
        }
        if (state.current_status === "Processing") {
            orchestratorStatusDot.classList.add('processing');
            orchestratorStatusText.textContent = 'Syncing...';
            orchestratorSyncBtn.disabled = true;
        } else {
            orchestratorStatusDot.classList.add('connected');
            orchestratorStatusText.textContent = 'Sync Tasks';
            orchestratorSyncBtn.disabled = !currentVault;
        }
    }

    function openModal(modalEl, inputEl) {
        if (modalEl) modalEl.classList.remove('hidden');
        if (inputEl) {
            inputEl.value = '';
            inputEl.focus();
        }
    }

    function openEditTaskModal(task) {
        if (!newTaskModal) return;
        editingTaskId = task.id;
        if (taskNameInput) taskNameInput.value = task.name;
        if (taskDescInput) taskDescInput.value = task.description || '';
        if (taskPriorityInput) taskPriorityInput.value = task.priority;
        if (taskDeadlineInput) taskDeadlineInput.value = task.deadline || '';
        if (taskTagsInput) taskTagsInput.value = task.tags.join(', ');
        newTaskModal.classList.remove('hidden');
    }

    function closeModal(modalEl) {
        if (modalEl) modalEl.classList.add('hidden');
        editingTaskId = null;
    }

    // --- Event Delegation ---
    if (vaultListEl) {
        vaultListEl.addEventListener('click', (e) => {
            const item = e.target.closest('.vault-item');
            if (!item) return;
            const deleteBtn = e.target.closest('.delete-vault-btn');
            if (deleteBtn) {
                e.stopPropagation();
                deleteVault(item.dataset.path);
            } else {
                selectVault(item.dataset.path);
            }
        });
    }

    if (noteListEl) {
        noteListEl.addEventListener('click', (e) => {
            const item = e.target.closest('.note-item');
            if (!item) return;
            const deleteBtn = e.target.closest('.delete-note-btn');
            if (deleteBtn) {
                e.stopPropagation();
                deleteNoteSpecific(item.dataset.name);
            } else {
                switchView('notes');
                selectNote(item.dataset.name);
            }
        });
    }

    // --- Static Event Listeners ---
    if (newVaultBtn) newVaultBtn.addEventListener('click', () => openModal(newVaultModal, newVaultInput));
    if (cancelVaultBtn) cancelVaultBtn.addEventListener('click', () => closeModal(newVaultModal));
    if (submitVaultBtn) submitVaultBtn.addEventListener('click', () => {
        const path = newVaultInput ? newVaultInput.value.trim() : '';
        if (path) createVault(path);
    });

    if (newNoteBtn) newNoteBtn.addEventListener('click', () => {
        if (!newNoteBtn.disabled) openModal(newNoteModal, newNoteInput);
    });
    if (cancelNoteBtn) cancelNoteBtn.addEventListener('click', () => closeModal(newNoteModal));
    if (submitNoteBtn) submitNoteBtn.addEventListener('click', () => {
        const filename = newNoteInput ? newNoteInput.value.trim() : '';
        if (filename) createNote(filename);
    });

    if (cancelTaskBtn) cancelTaskBtn.addEventListener('click', () => closeModal(newTaskModal));
    if (submitTaskBtn) submitTaskBtn.addEventListener('click', () => upsertTask());

    if (viewNotesBtn) viewNotesBtn.addEventListener('click', () => switchView('notes'));
    if (viewTasksBtn) viewTasksBtn.addEventListener('click', () => switchView('tasks'));

    if (saveNoteBtn) saveNoteBtn.addEventListener('click', saveNote);
    if (deleteNoteBtn) deleteNoteBtn.addEventListener('click', () => { if (currentNote) deleteNoteSpecific(currentNote); });
    if (orchestratorSyncBtn) orchestratorSyncBtn.addEventListener('click', triggerOrchestratorGenerate);

    if (menuToggle) menuToggle.addEventListener('click', toggleSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', toggleSidebar);

    window.addEventListener('resize', () => {
        const wasMobile = isMobile;
        isMobile = window.innerWidth <= 768;
        // When transitioning from mobile to desktop, ensure mobile-only sidebar state is cleared
        if (wasMobile && !isMobile) {
            if (typeof sidebar !== 'undefined' && sidebar) {
                sidebar.classList.remove('open');
            }
            if (sidebarOverlay) {
                sidebarOverlay.classList.remove('active');
            }
            if (menuToggle) {
                menuToggle.classList.remove('active');
            }
            document.body.classList.remove('sidebar-open');
        }
    });

    if (markdownEditor) {
        markdownEditor.addEventListener('input', () => {
            renderMarkdown();
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(saveNote, 1000);
        });
    }

    // --- Init ---
    fetchVaults();
    pollOrchestratorStatus();
    setInterval(pollOrchestratorStatus, 5000); 
});
