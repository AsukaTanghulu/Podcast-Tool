// API 基础 URL
const API_BASE = '/api';
const HIDDEN_NOTES_STORAGE_KEY = 'podcast_hidden_note_records';

// 全局变量：存储所有播客数据
let allPodcasts = [];

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initModalGuards();
    loadPodcasts();
    initSubmitForm();
    initUploadForm();
});

// 初始化模态框保护（防止遮罩残留导致灰屏不可点击）
function initModalGuards() {
    const cleanupTargets = ['detailModal', 'previewModal', 'providerModal', 'chatModal', 'loadingModal', 'speakerModal'];
    cleanupTargets.forEach(modalId => {
        const modalEl = document.getElementById(modalId);
        if (!modalEl) return;
        modalEl.addEventListener('hidden.bs.modal', function() {
            try {
                const instance = bootstrap.Modal.getInstance(this);
                if (instance) {
                    instance.dispose();
                }
            } catch (e) {
                // ignore
            }
            cleanupModalBackdrop();
        });
    });
}

function cleanupModalBackdrop() {
    const visibleModals = document.querySelectorAll('.modal.show');
    if (visibleModals.length > 0) return;

    document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('padding-right');
}

// 初始化提交表单
function initSubmitForm() {
    const form = document.getElementById('submitForm');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const url = document.getElementById('podcastUrl').value;
        const submitBtn = document.getElementById('submitBtn');
        const submitSpinner = document.getElementById('submitSpinner');
        const submitAlert = document.getElementById('submitAlert');

        // 显示加载状态
        submitBtn.disabled = true;
        submitSpinner.classList.remove('d-none');
        submitAlert.classList.add('d-none');

        try {
            const response = await fetch(`${API_BASE}/podcasts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url })
            });

            const result = await response.json();

            if (result.success) {
                showAlert(submitAlert, 'success', '任务提交成功！正在处理...');
                form.reset();
                // 刷新列表
                setTimeout(() => loadPodcasts(), 1000);
            } else {
                showAlert(submitAlert, 'danger', `错误: ${result.error}`);
            }
        } catch (error) {
            showAlert(submitAlert, 'danger', `请求失败: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            submitSpinner.classList.add('d-none');
        }
    });
}

// 初始化上传表单
function initUploadForm() {
    const form = document.getElementById('uploadForm');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const fileInput = document.getElementById('documentaryFile');
        const titleInput = document.getElementById('documentaryTitle');
        const uploadBtn = document.getElementById('uploadBtn');
        const uploadSpinner = document.getElementById('uploadSpinner');
        const submitAlert = document.getElementById('submitAlert');
        const progressBar = document.getElementById('uploadProgress');

        if (!fileInput.files || fileInput.files.length === 0) {
            showAlert(submitAlert, 'danger', '请选择文件');
            return;
        }

        const file = fileInput.files[0];
        const title = titleInput.value.trim();

        // 显示加载状态
        uploadBtn.disabled = true;
        uploadSpinner.classList.remove('d-none');
        submitAlert.classList.add('d-none');
        progressBar.classList.remove('d-none');

        try {
            const formData = new FormData();
            formData.append('file', file);
            if (title) {
                formData.append('title', title);
            }

            const xhr = new XMLHttpRequest();

            // 监听上传进度
            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    const progressBarInner = progressBar.querySelector('.progress-bar');
                    progressBarInner.style.width = percentComplete + '%';
                    progressBarInner.textContent = Math.round(percentComplete) + '%';
                }
            });

            // 监听完成
            xhr.addEventListener('load', function() {
                if (xhr.status === 200) {
                    const result = JSON.parse(xhr.responseText);
                    if (result.success) {
                        showAlert(submitAlert, 'success', '文件上传成功！正在处理...');
                        form.reset();
                        progressBar.classList.add('d-none');
                        // 刷新列表
                        setTimeout(() => loadPodcasts(), 1000);
                    } else {
                        showAlert(submitAlert, 'danger', `错误: ${result.error}`);
                        progressBar.classList.add('d-none');
                    }
                } else {
                    showAlert(submitAlert, 'danger', `上传失败: HTTP ${xhr.status}`);
                    progressBar.classList.add('d-none');
                }
                uploadBtn.disabled = false;
                uploadSpinner.classList.add('d-none');
            });

            // 监听错误
            xhr.addEventListener('error', function() {
                showAlert(submitAlert, 'danger', '上传失败，请检查网络连接');
                progressBar.classList.add('d-none');
                uploadBtn.disabled = false;
                uploadSpinner.classList.add('d-none');
            });

            // 发送请求
            xhr.open('POST', `${API_BASE}/documentaries`);
            xhr.send(formData);

        } catch (error) {
            showAlert(submitAlert, 'danger', `上传失败: ${error.message}`);
            progressBar.classList.add('d-none');
            uploadBtn.disabled = false;
            uploadSpinner.classList.add('d-none');
        }
    });
}

// 加载播客列表
async function loadPodcasts() {
    const listContainer = document.getElementById('podcastList');

    try {
        const response = await fetch(`${API_BASE}/podcasts`);
        const result = await response.json();

        if (result.success && result.data.length > 0) {
            allPodcasts = result.data;  // 保存到全局变量
            updateCategoryFilter();     // 更新栏目筛选器
            renderPodcasts(allPodcasts); // 渲染列表
        } else {
            allPodcasts = [];
            listContainer.innerHTML = '<p class="text-muted text-center">暂无播客记录</p>';
        }
    } catch (error) {
        listContainer.innerHTML = `<div class="alert alert-danger">加载失败: ${error.message}</div>`;
    }
}

// 渲染播客列表
function renderPodcasts(podcasts) {
    const listContainer = document.getElementById('podcastList');
    if (podcasts.length > 0) {
        listContainer.innerHTML = podcasts.map(podcast => createPodcastCard(podcast)).join('');
    } else {
        listContainer.innerHTML = '<p class="text-muted text-center">没有符合条件的播客</p>';
    }
}

// 更新栏目筛选器
function updateCategoryFilter() {
    const filterSelect = document.getElementById('categoryFilter');
    if (!filterSelect) return;

    // 提取所有唯一的栏目
    const categories = [...new Set(allPodcasts
        .map(p => p.category)
        .filter(c => c && c.trim() !== '')
    )].sort();

    // 更新下拉选项
    filterSelect.innerHTML = '<option value="">全部栏目</option>' +
        categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
}

// 按栏目筛选
function filterByCategory() {
    const filterSelect = document.getElementById('categoryFilter');
    const selectedCategory = filterSelect.value;

    if (selectedCategory === '') {
        // 显示全部
        renderPodcasts(allPodcasts);
    } else {
        // 筛选指定栏目
        const filtered = allPodcasts.filter(p => p.category === selectedCategory);
        renderPodcasts(filtered);
    }
}

// 创建播客卡片
function createPodcastCard(podcast) {
    const statusBadge = getStatusBadge(podcast.status);
    const createdAt = new Date(podcast.created_at).toLocaleString('zh-CN');
    const categoryBadge = podcast.category ?
        `<span class="badge bg-info me-1">${podcast.category}</span>` : '';

    // 内容类型徽章
    const contentType = podcast.content_type || 'podcast';
    const contentTypeBadge = contentType === 'documentary' ?
        `<span class="badge bg-secondary me-1"><i class="bi bi-film"></i> 纪录片</span>` :
        `<span class="badge bg-primary me-1"><i class="bi bi-broadcast"></i> 播客</span>`;

    // 如果转录失败，显示重新转录按钮
    const retryButton = podcast.status === 'failed' ?
        `<button class="btn btn-sm btn-warning" onclick="retryTranscription('${podcast.id}')">
            <i class="bi bi-arrow-clockwise"></i> 重新转录
        </button>` : '';

    return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="card-title">
                            ${contentTypeBadge}
                            ${categoryBadge}
                            ${podcast.title || '未命名'}
                            ${statusBadge}
                        </h6>
                        <p class="card-text text-muted small mb-2">
                            <strong>ID:</strong> ${podcast.id}<br>
                            <strong>创建时间:</strong> ${createdAt}
                            ${podcast.original_filename ? `<br><strong>文件名:</strong> ${podcast.original_filename}` : ''}
                        </p>
                        ${podcast.error_message ? `<p class="text-danger small mb-0">错误: ${podcast.error_message}</p>` : ''}
                    </div>
                    <div class="btn-group" role="group">
                        ${retryButton}
                        <button class="btn btn-sm btn-primary" onclick="viewDetail('${podcast.id}')">
                            查看详情
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletePodcast('${podcast.id}')">
                            删除
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 获取状态徽章
function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-secondary">等待中</span>',
        'downloading': '<span class="badge bg-info">下载中</span>',
        'transcribing': '<span class="badge bg-warning">转录中</span>',
        'completed': '<span class="badge bg-success">已完成</span>',
        'failed': '<span class="badge bg-danger">失败</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">未知</span>';
}

// 查看详情
async function viewDetail(podcastId) {
    const modalElement = document.getElementById('detailModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    const content = document.getElementById('detailContent');

    content.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';
    modal.show();

    try {
        const response = await fetch(`${API_BASE}/podcasts/${podcastId}`);
        const result = await response.json();

        if (result.success) {
            content.innerHTML = createDetailView(result.data);
        } else {
            content.innerHTML = `<div class="alert alert-danger">加载失败: ${result.error}</div>`;
        }
    } catch (error) {
        content.innerHTML = `<div class="alert alert-danger">请求失败: ${error.message}</div>`;
    }
}

// 创建详情视图
function createDetailView(data) {
    const { podcast, transcripts, notes } = data;
    const visibleNotes = (notes || []).filter(n => !isNoteHidden(podcast.id, n.id));

    let html = `
        <div class="mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6>基本信息</h6>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary" onclick="renamePodcast('${podcast.id}', '${podcast.title}')">
                        重命名
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="updateCategory('${podcast.id}', '${podcast.category || ''}')">
                        设置栏目
                    </button>
                </div>
            </div>
            <table class="table table-sm">
                <tr><td><strong>播客名称</strong></td><td>${podcast.title}</td></tr>
                <tr>
                    <td><strong>播客栏目</strong></td>
                    <td>
                        <span class="badge bg-info">${podcast.category || '未分类'}</span>
                    </td>
                </tr>
                <tr><td><strong>播客 ID</strong></td><td>${podcast.id}</td></tr>
                <tr><td><strong>URL</strong></td><td><a href="${podcast.url}" target="_blank">${podcast.url}</a></td></tr>
                <tr><td><strong>状态</strong></td><td>${getStatusBadge(podcast.status)}</td></tr>
                <tr><td><strong>创建时间</strong></td><td>${new Date(podcast.created_at).toLocaleString('zh-CN')}</td></tr>
                ${podcast.duration ? `<tr><td><strong>时长</strong></td><td>${formatDuration(podcast.duration)}</td></tr>` : ''}
                ${podcast.file_size ? `<tr><td><strong>文件大小</strong></td><td>${formatFileSize(podcast.file_size)}</td></tr>` : ''}
            </table>
        </div>
    `;

    // 转录记录
    if (transcripts && transcripts.length > 0) {
        html += `
            <div class="mb-4">
                <h6>转录记录</h6>
                <div class="list-group">
                    ${transcripts.map(t => `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>模型:</strong> ${t.model_version || '未知'}<br>
                                    <strong>字数:</strong> ${t.word_count || 0}<br>
                                    <strong>时间:</strong> ${new Date(t.created_at).toLocaleString('zh-CN')}
                                </div>
                                <div class="btn-group" role="group">
                                    <button class="btn btn-sm btn-outline-info" data-file-path="${t.file_path}" data-transcript-id="${t.id}" onclick="previewFile(this.getAttribute('data-file-path'), this.getAttribute('data-transcript-id'))">
                                        预览
                                    </button>
                                    <button class="btn btn-sm btn-outline-primary" data-file-path="${t.file_path}" onclick="downloadFile(this.getAttribute('data-file-path'))">
                                        下载
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // 笔记记录
    if (visibleNotes.length > 0) {
        html += `
            <div class="mb-4">
                <h6>笔记记录</h6>
                <div class="list-group">
                    ${visibleNotes.map(n => `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>类型:</strong> ${n.note_type === 'auto' ? '规则引擎' : 'AI 生成'}<br>
                                    ${n.model_name ? `<strong>模型:</strong> ${n.model_name}<br>` : ''}
                                    <strong>时间:</strong> ${new Date(n.created_at).toLocaleString('zh-CN')}
                                </div>
                                <div class="btn-group" role="group">
                                    <button class="btn btn-sm btn-outline-info" data-file-path="${n.file_path}" onclick="previewFile(this.getAttribute('data-file-path'))">
                                        预览
                                    </button>
                                    <button class="btn btn-sm btn-outline-primary" data-file-path="${n.file_path}" onclick="downloadFile(this.getAttribute('data-file-path'))">
                                        下载
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteNoteRecord('${n.id}', '${podcast.id}')">
                                        删除显示
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // 笔记生成按钮
    if (podcast.status === 'completed') {
        html += `
            <div class="mb-4">
                <h6>功能操作</h6>
                <div class="d-grid gap-2 mb-2">
                    <button class="btn btn-outline-primary" onclick="initAIChat('${podcast.id}')">
                        <i class="bi bi-chat-dots"></i> AI 对话（基于转录内容）
                    </button>
                </div>
                <div class="btn-group w-100" role="group">
                    <button class="btn btn-outline-success" onclick="generateNote('${podcast.id}', 'auto')">
                        规则引擎笔记
                    </button>
                    <button class="btn btn-outline-info" onclick="generateNote('${podcast.id}', 'ai', 'qwen')">
                        通义千问笔记
                    </button>
                    <button class="btn btn-outline-secondary" onclick="generateNote('${podcast.id}', 'ai', 'deepseek')">
                        DeepSeek 笔记
                    </button>
                </div>
                <div id="noteAlert" class="alert mt-3 d-none"></div>
            </div>
        `;
    }

    return html;
}

// 预览文件
async function previewFile(filePath, transcriptId = null) {
    const modalElement = document.getElementById('previewModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    const content = document.getElementById('previewContent');

    content.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';
    modal.show();

    try {
        // 使用POST请求避免URL编码问题
        const response = await fetch(`${API_BASE}/files/preview`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_path: filePath
            })
        });
        const result = await response.json();

        if (result.success) {
            // 检查是否是转录文件（JSON格式）
            if (filePath.includes('transcripts') && filePath.endsWith('.json')) {
                // 解析转录数据并渲染对话式布局
                const transcriptData = JSON.parse(result.data.content);
                content.innerHTML = renderTranscriptView(transcriptData, transcriptId);
            } else if (result.data.type === 'markdown') {
                content.innerHTML = result.data.html;
            } else {
                content.innerHTML = `<pre>${result.data.content}</pre>`;
            }
        } else {
            content.innerHTML = `<div class="alert alert-danger">预览失败: ${result.error}</div>`;
        }
    } catch (error) {
        content.innerHTML = `<div class="alert alert-danger">请求失败: ${error.message}</div>`;
    }
}

// 下载文件
async function downloadFile(filePath) {
    try {
        // 使用POST请求获取文件
        const response = await fetch(`${API_BASE}/files/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_path: filePath
            })
        });

        if (response.ok) {
            // 获取文件名
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'download';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename\*=UTF-8''(.+)|filename="?(.+)"?/);
                if (filenameMatch) {
                    filename = decodeURIComponent(filenameMatch[1] || filenameMatch[2]);
                }
            }

            // 创建Blob并触发下载
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('下载失败');
        }
    } catch (error) {
        alert(`下载失败: ${error.message}`);
    }
}

// 生成笔记
async function generateNote(podcastId, noteType, aiProvider = 'qwen') {
    const noteAlert = document.getElementById('noteAlert');

    showAlert(noteAlert, 'info', '正在生成笔记，请稍候...');

    try {
        const response = await fetch(`${API_BASE}/notes/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                podcast_id: podcastId,
                note_type: noteType,
                ai_provider: aiProvider
            })
        });

        const result = await response.json();

        if (result.success) {
            showAlert(noteAlert, 'success', `笔记生成成功！文件路径: ${result.data.file_path}`);
            // 刷新详情
            setTimeout(() => viewDetail(podcastId), 1000);
        } else {
            showAlert(noteAlert, 'danger', `生成失败: ${result.error}`);
        }
    } catch (error) {
        showAlert(noteAlert, 'danger', `请求失败: ${error.message}`);
    }
}

// 重新转录
async function retryTranscription(podcastId) {
    if (!confirm('确定要重新转录这个内容吗？这将使用已下载的文件重新进行转录。')) {
        return;
    }

    try {
        // 显示加载提示
        const card = event.target.closest('.card');
        const btnGroup = card.querySelector('.btn-group');
        const originalHtml = btnGroup.innerHTML;
        btnGroup.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 转录中...';

        const response = await fetch(`${API_BASE}/podcasts/${podcastId}/retry-transcription`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            alert('重新转录成功！');
            loadPodcasts(); // 刷新列表
        } else {
            alert(`重新转录失败: ${result.error}`);
            btnGroup.innerHTML = originalHtml;
        }
    } catch (error) {
        alert(`请求失败: ${error.message}`);
        loadPodcasts(); // 刷新列表以恢复状态
    }
}

// 删除播客
async function deletePodcast(podcastId) {
    if (!confirm('确定要删除这个播客吗？此操作将删除所有相关文件，无法恢复。')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/podcasts/${podcastId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            alert('删除成功！');
            loadPodcasts();
        } else {
            alert(`删除失败: ${result.error}`);
        }
    } catch (error) {
        alert(`请求失败: ${error.message}`);
    }
}

function getHiddenNotesState() {
    try {
        const raw = localStorage.getItem(HIDDEN_NOTES_STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch (error) {
        return {};
    }
}

function saveHiddenNotesState(state) {
    localStorage.setItem(HIDDEN_NOTES_STORAGE_KEY, JSON.stringify(state));
}

function isNoteHidden(podcastId, noteId) {
    const state = getHiddenNotesState();
    const hiddenList = state[String(podcastId)] || [];
    return hiddenList.includes(String(noteId));
}

// 删除笔记记录（仅删除前端显示，不删除文件和数据库记录）
async function deleteNoteRecord(noteId, podcastId) {
    if (!confirm('确定要删除这条笔记记录的前端显示吗？文件和数据库记录都会保留。')) {
        return;
    }

    try {
        const state = getHiddenNotesState();
        const key = String(podcastId);
        const hiddenSet = new Set((state[key] || []).map(String));
        hiddenSet.add(String(noteId));
        state[key] = Array.from(hiddenSet);
        saveHiddenNotesState(state);

        alert('已从前端隐藏该笔记记录。');
        viewDetail(podcastId);
    } catch (error) {
        alert(`操作失败: ${error.message}`);
    }
}

function clearHiddenNotesForPodcast(podcastId) {
    try {
        const state = getHiddenNotesState();
        const key = String(podcastId);
        if (state[key]) {
            delete state[key];
            saveHiddenNotesState(state);
        }
    } catch (error) {
        // 忽略清理异常
    }
}

// 清空所有播客
async function clearAllPodcasts() {
    if (!confirm('确定要清空所有播客吗？此操作将删除所有播客和相关文件，无法恢复。')) {
        return;
    }

    if (!confirm('再次确认：真的要清空所有播客吗？')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/podcasts/clear-all`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            alert(`清空成功！删除了 ${result.data.podcasts_deleted} 个播客。`);
            loadPodcasts();
        } else {
            alert(`清空失败: ${result.error}`);
        }
    } catch (error) {
        alert(`请求失败: ${error.message}`);
    }
}

// 重命名播客
async function renamePodcast(podcastId, currentTitle) {
    const newTitle = prompt('请输入新的播客名称:', currentTitle);

    if (!newTitle || newTitle === currentTitle) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/podcasts/${podcastId}/rename`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title: newTitle })
        });

        const result = await response.json();

        if (result.success) {
            alert('重命名成功！');
            viewDetail(podcastId);
            loadPodcasts();
        } else {
            alert(`重命名失败: ${result.error}`);
        }
    } catch (error) {
        alert(`请求失败: ${error.message}`);
    }
}

// 更新播客栏目
async function updateCategory(podcastId, currentCategory) {
    const newCategory = prompt('请输入播客栏目（用于分类）:', currentCategory);

    if (newCategory === null) {
        return;  // 用户点击取消
    }

    try {
        const response = await fetch(`${API_BASE}/podcasts/${podcastId}/category`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ category: newCategory })
        });

        const result = await response.json();

        if (result.success) {
            alert('栏目设置成功！');
            viewDetail(podcastId);
            loadPodcasts();
        } else {
            alert(`设置失败: ${result.error}`);
        }
    } catch (error) {
        alert(`请求失败: ${error.message}`);
    }
}

// 显示提示信息
function showAlert(element, type, message) {
    element.className = `alert alert-${type}`;
    element.textContent = message;
    element.classList.remove('d-none');
}

// 格式化时长
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    } else {
        return `${minutes}:${String(secs).padStart(2, '0')}`;
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB';
    return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB';
}

// 渲染转录视图（对话式布局）
function renderTranscriptView(data, transcriptId) {
    const segments = data.segments || [];
    const speakerNames = data.metadata?.speaker_names || {};

    const hasSpeakerId = (value) => value !== null && value !== undefined && String(value).trim() !== '';
    const normalizeSpeakerId = (value) => hasSpeakerId(value) ? String(value) : 'unknown';

    // 提取所有说话人
    const speakers = new Set();
    segments.forEach(seg => {
        if (hasSpeakerId(seg.speaker_id)) {
            speakers.add(String(seg.speaker_id));
        }
    });

    // 分配颜色
    const speakerColors = {};
    const colors = ['primary', 'success', 'info', 'warning', 'secondary'];
    let colorIndex = 0;
    speakers.forEach(speaker => {
        speakerColors[speaker] = colors[colorIndex % colors.length];
        colorIndex++;
    });

    let html = `
        <div class="transcript-viewer">
            <!-- 工具栏 -->
            <div class="transcript-toolbar mb-3 p-3 bg-light rounded">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <div class="input-group">
                            <span class="input-group-text"><i class="bi bi-search"></i></span>
                            <input type="text" class="form-control" id="searchInput"
                                   placeholder="搜索内容..." onkeyup="filterTranscript()">
                        </div>
                    </div>
                    <div class="col-md-6 text-end">
                        <div class="btn-group" role="group">
                            ${transcriptId ? `
                                <button class="btn btn-sm btn-outline-primary" onclick="manageSpeakers('${transcriptId}')">
                                    <i class="bi bi-people"></i> 管理说话人
                                </button>
                            ` : ''}
                            <button class="btn btn-sm btn-outline-success" onclick="exportTranscript('${transcriptId}', 'txt')">
                                <i class="bi bi-download"></i> 导出TXT
                            </button>
                            <button class="btn btn-sm btn-outline-info" onclick="exportTranscript('${transcriptId}', 'md')">
                                <i class="bi bi-download"></i> 导出MD
                            </button>
                            <button class="btn btn-sm btn-outline-warning" onclick="exportTranscript('${transcriptId}', 'srt')">
                                <i class="bi bi-download"></i> 导出SRT
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 说话人过滤 -->
                ${speakers.size > 0 ? `
                    <div class="mt-2">
                        <label class="form-label small mb-1">按说话人筛选：</label>
                        <div class="btn-group btn-group-sm" role="group">
                            <input type="checkbox" class="btn-check" id="filter-all" checked onchange="filterBySpeaker(null)">
                            <label class="btn btn-outline-secondary" for="filter-all">全部</label>
                            ${Array.from(speakers).map(speaker => {
                                const name = speakerNames[speaker] || speaker;
                                const color = speakerColors[speaker];
                                return `
                                    <input type="checkbox" class="btn-check speaker-filter" id="filter-${speaker}"
                                           data-speaker="${speaker}" checked onchange="filterBySpeaker('${speaker}')">
                                    <label class="btn btn-outline-${color}" for="filter-${speaker}">${name}</label>
                                `;
                            }).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>

            <!-- 转录内容 -->
            <div class="transcript-content" id="transcriptContent">
    `;

    // 渲染每个段落
    segments.forEach((seg, index) => {
        const speakerId = normalizeSpeakerId(seg.speaker_id);
        const speakerName = speakerNames[speakerId] || speakerId;
        const color = speakerColors[speakerId] || 'secondary';
        const startTime = formatTime(seg.start);
        const endTime = formatTime(seg.end);

        // 交替左右布局
        const alignment = index % 2 === 0 ? 'start' : 'end';

        html += `
            <div class="transcript-segment mb-3" data-speaker="${speakerId}" data-text="${seg.text.toLowerCase()}">
                <div class="d-flex justify-content-${alignment}">
                    <div class="segment-bubble segment-${alignment}" style="max-width: 75%;">
                        <div class="segment-header d-flex justify-content-between align-items-center mb-2">
                            <span class="badge bg-${color}">
                                <i class="bi bi-person-circle"></i> ${speakerName}
                            </span>
                            <small class="text-muted">${startTime} - ${endTime}</small>
                        </div>
                        <div class="segment-text bg-${color} bg-opacity-10 p-3 rounded">
                            ${seg.text}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += `
            </div>
        </div>
    `;

    return html;
}

// 格式化时间
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}

// 搜索过滤
function filterTranscript() {
    const searchText = document.getElementById('searchInput').value.toLowerCase();
    const segments = document.querySelectorAll('.transcript-segment');

    segments.forEach(segment => {
        const text = segment.getAttribute('data-text');
        if (text.includes(searchText)) {
            segment.style.display = '';
        } else {
            segment.style.display = 'none';
        }
    });
}

// 按说话人筛选
function filterBySpeaker(speaker) {
    const allCheckbox = document.getElementById('filter-all');
    const speakerCheckboxes = document.querySelectorAll('.speaker-filter');

    if (speaker === null) {
        // 全部选中/取消
        const checked = allCheckbox.checked;
        speakerCheckboxes.forEach(cb => {
            cb.checked = checked;
        });

        const segments = document.querySelectorAll('.transcript-segment');
        segments.forEach(seg => {
            seg.style.display = checked ? '' : 'none';
        });
    } else {
        // 单个说话人筛选
        const segments = document.querySelectorAll(`.transcript-segment[data-speaker="${speaker}"]`);
        const checkbox = document.getElementById(`filter-${speaker}`);

        segments.forEach(seg => {
            seg.style.display = checkbox.checked ? '' : 'none';
        });

        // 更新"全部"复选框状态
        const allChecked = Array.from(speakerCheckboxes).every(cb => cb.checked);
        allCheckbox.checked = allChecked;
    }
}

// 管理说话人
async function manageSpeakers(transcriptId) {
    try {
        // 获取说话人列表
        const response = await fetch(`${API_BASE}/transcripts/${transcriptId}/speakers`);
        const result = await response.json();

        if (!result.success) {
            alert(`获取说话人列表失败: ${result.error}`);
            return;
        }

        const speakers = result.data.speakers;

        if (speakers.length === 0) {
            alert('该转录没有说话人信息');
            return;
        }

        // 创建对话框
        let html = '<div class="list-group">';
        speakers.forEach(speaker => {
            html += `
                <div class="list-group-item">
                    <div class="row align-items-center">
                        <div class="col-md-4">
                            <strong>${speaker.id}</strong>
                        </div>
                        <div class="col-md-6">
                            <input type="text" class="form-control form-control-sm"
                                   id="speaker-name-${speaker.id}"
                                   value="${speaker.name}"
                                   placeholder="输入说话人名称">
                        </div>
                        <div class="col-md-2 text-end">
                            <small class="text-muted">${speaker.count} 次</small>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        // 显示对话框
        const confirmed = confirm('是否要重命名说话人？\n点击确定后，请在弹出的输入框中修改说话人名称。');

        if (confirmed) {
            // 创建临时模态框
            const modalHtml = `
                <div class="modal fade" id="speakerModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">管理说话人</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${html}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                                <button type="button" class="btn btn-primary" onclick="saveSpeakerNames('${transcriptId}')">保存</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // 添加到页面
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modal = new bootstrap.Modal(document.getElementById('speakerModal'));
            modal.show();

            // 模态框关闭后移除
            document.getElementById('speakerModal').addEventListener('hidden.bs.modal', function() {
                cleanupModalBackdrop();
                this.remove();
            });
        }
    } catch (error) {
        alert(`获取说话人列表失败: ${error.message}`);
    }
}

// 保存说话人名称
async function saveSpeakerNames(transcriptId) {
    try {
        // 收集所有说话人名称
        const mappings = {};
        const inputs = document.querySelectorAll('[id^="speaker-name-"]');

        inputs.forEach(input => {
            const speakerId = input.id.replace('speaker-name-', '');
            const name = input.value.trim();
            if (name) {
                mappings[speakerId] = name;
            }
        });

        // 发送请求
        const response = await fetch(`${API_BASE}/transcripts/${transcriptId}/speakers/rename`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mappings })
        });

        const result = await response.json();

        if (result.success) {
            alert('说话人名称已更新！');
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('speakerModal')).hide();
            // 刷新预览
            location.reload();
        } else {
            alert(`保存失败: ${result.error}`);
        }
    } catch (error) {
        alert(`保存失败: ${error.message}`);
    }
}

// 导出转录
async function exportTranscript(transcriptId, format) {
    try {
        const response = await fetch(`${API_BASE}/transcripts/${transcriptId}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format: format,
                include_speakers: true,
                include_timestamps: true
            })
        });

        if (response.ok) {
            // 获取文件名
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `transcript.${format}`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename\*=UTF-8''(.+)|filename="?(.+)"?/);
                if (filenameMatch) {
                    filename = decodeURIComponent(filenameMatch[1] || filenameMatch[2]);
                }
            }

            // 下载文件
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('导出失败');
        }
    } catch (error) {
        alert(`导出失败: ${error.message}`);
    }
}

// ==================== AI 对话功能 ====================

// 全局变量：当前对话会话
let currentChatSession = null;

// 初始化 AI 对话
async function initAIChat(podcastId) {
    // 显示 AI 提供商选择对话框
    const provider = await showProviderSelection();
    if (!provider) return;

    let loadingModal = null;
    try {
        // 显示加载提示
        loadingModal = showLoadingModal('正在初始化 AI 对话...');

        const response = await fetch(`${API_BASE}/podcasts/${podcastId}/chat/init`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ provider })
        });

        const result = await response.json();

        if (result.success) {
            currentChatSession = result.data.session_id;
            showChatInterface(podcastId, provider);
        } else {
            alert(`初始化失败: ${result.error}`);
        }
    } catch (error) {
        alert(`初始化失败: ${error.message}`);
    } finally {
        if (loadingModal) {
            try {
                loadingModal.hide();
            } catch (e) {
                // ignore
            }
        }
        cleanupModalBackdrop();
    }
}

// 显示 AI 提供商选择（AI 对话仅支持 DeepSeek）
function showProviderSelection() {
    return new Promise((resolve) => {
        const html = `
            <div class="modal fade" id="providerModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">AI 对话</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <i class="bi bi-info-circle"></i> AI 对话功能使用 DeepSeek 模型
                            </div>
                            <div class="d-grid gap-2">
                                <button class="btn btn-primary btn-lg" onclick="selectProvider('deepseek')">
                                    <i class="bi bi-cpu"></i> 开始对话
                                    <br><small class="text-muted">使用 DeepSeek 进行深度对话</small>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 移除旧的模态框
        const oldModal = document.getElementById('providerModal');
        if (oldModal) oldModal.remove();

        // 添加新的模态框
        document.body.insertAdjacentHTML('beforeend', html);

        const modal = new bootstrap.Modal(document.getElementById('providerModal'));
        modal.show();

        initModalGuards();

        // 设置选择回调
        window.selectProvider = (provider) => {
            modal.hide();
            resolve(provider);
        };

        // 取消时返回 null
        document.getElementById('providerModal').addEventListener('hidden.bs.modal', () => {
            if (!window.selectedProvider) {
                resolve(null);
            }
            window.selectedProvider = null;
            cleanupModalBackdrop();
        });
    });
}

// 显示聊天界面
function showChatInterface(podcastId, provider) {
    const html = `
        <div class="modal fade" id="chatModal" tabindex="-1">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-chat-dots"></i> AI 对话
                            <span class="badge bg-primary">${provider === 'qwen' ? '通义千问' : 'DeepSeek'}</span>
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="chatMessages" style="height: 400px; overflow-y: auto;">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> AI 已加载播客转录内容，你可以开始提问了。
                            <br><small>提示：你可以询问播客的主要观点、讨论细节、或者进行深度思考。</small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <div class="input-group">
                            <input type="text" class="form-control" id="chatInput"
                                   placeholder="输入你的问题..."
                                   onkeypress="if(event.key==='Enter') sendChatMessage()">
                            <button class="btn btn-primary" onclick="sendChatMessage()">
                                <i class="bi bi-send"></i> 发送
                            </button>
                            <button class="btn btn-outline-secondary" onclick="clearChatHistory()">
                                <i class="bi bi-trash"></i> 清空
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 移除旧的模态框
    const oldModal = document.getElementById('chatModal');
    if (oldModal) oldModal.remove();

    // 添加新的模态框
    document.body.insertAdjacentHTML('beforeend', html);

    const modal = new bootstrap.Modal(document.getElementById('chatModal'));
    modal.show();

    initModalGuards();

    // 聚焦输入框
    document.getElementById('chatInput').focus();
}

// 发送聊天消息
async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // 清空输入框
    input.value = '';

    // 显示用户消息
    appendChatMessage('user', message);

    // 显示加载提示
    const loadingId = appendChatMessage('assistant', '<div class="spinner-border spinner-border-sm"></div> 思考中...');

    try {
        const response = await fetch(`${API_BASE}/chat/${currentChatSession}/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });

        const result = await response.json();

        // 移除加载提示
        document.getElementById(loadingId).remove();

        if (result.success) {
            appendChatMessage('assistant', result.data.message);
        } else {
            appendChatMessage('assistant', `<span class="text-danger">错误: ${result.error}</span>`);
        }
    } catch (error) {
        document.getElementById(loadingId).remove();
        appendChatMessage('assistant', `<span class="text-danger">请求失败: ${error.message}</span>`);
    }

    // 聚焦输入框
    input.focus();
}

// 添加聊天消息到界面
function appendChatMessage(role, content) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageId = 'msg-' + Date.now();

    const isUser = role === 'user';
    const alignClass = isUser ? 'text-end' : 'text-start';
    const bgClass = isUser ? 'bg-primary text-white' : 'bg-light';

    const html = `
        <div class="mb-3 ${alignClass}" id="${messageId}">
            <div class="d-inline-block ${bgClass} rounded p-3" style="max-width: 80%;">
                ${content}
            </div>
        </div>
    `;

    messagesDiv.insertAdjacentHTML('beforeend', html);

    // 滚动到底部
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    return messageId;
}

// 清空聊天历史
async function clearChatHistory() {
    if (!confirm('确定要清空对话历史吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/chat/${currentChatSession}/clear`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            // 清空界面
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> 对话历史已清空，你可以重新开始提问。
                </div>
            `;
        } else {
            alert(`清空失败: ${result.error}`);
        }
    } catch (error) {
        alert(`清空失败: ${error.message}`);
    }
}

// 显示加载模态框
function showLoadingModal(message) {
    const html = `
        <div class="modal fade" id="loadingModal" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-sm modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-body text-center py-4">
                        <div class="spinner-border text-primary mb-3"></div>
                        <p class="mb-0">${message}</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    const oldModal = document.getElementById('loadingModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', html);

    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();

    initModalGuards();

    return modal;
}
