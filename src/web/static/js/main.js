// API 基础 URL
const API_BASE = '/api';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadPodcasts();
    initSubmitForm();
});

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

// 加载播客列表
async function loadPodcasts() {
    const listContainer = document.getElementById('podcastList');

    try {
        const response = await fetch(`${API_BASE}/podcasts`);
        const result = await response.json();

        if (result.success && result.data.length > 0) {
            listContainer.innerHTML = result.data.map(podcast => createPodcastCard(podcast)).join('');
        } else {
            listContainer.innerHTML = '<p class="text-muted text-center">暂无播客记录</p>';
        }
    } catch (error) {
        listContainer.innerHTML = `<div class="alert alert-danger">加载失败: ${error.message}</div>`;
    }
}

// 创建播客卡片
function createPodcastCard(podcast) {
    const statusBadge = getStatusBadge(podcast.status);
    const createdAt = new Date(podcast.created_at).toLocaleString('zh-CN');

    return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="card-title">
                            ${podcast.title || '未命名播客'}
                            ${statusBadge}
                        </h6>
                        <p class="card-text text-muted small mb-2">
                            <strong>ID:</strong> ${podcast.id}<br>
                            <strong>创建时间:</strong> ${createdAt}
                        </p>
                        ${podcast.error_message ? `<p class="text-danger small mb-0">错误: ${podcast.error_message}</p>` : ''}
                    </div>
                    <div class="btn-group" role="group">
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
    const modal = new bootstrap.Modal(document.getElementById('detailModal'));
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

    let html = `
        <div class="mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6>基本信息</h6>
                <button class="btn btn-sm btn-outline-primary" onclick="renamePodcast('${podcast.id}', '${podcast.title}')">
                    重命名
                </button>
            </div>
            <table class="table table-sm">
                <tr><td><strong>播客名称</strong></td><td>${podcast.title}</td></tr>
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
                                    <button class="btn btn-sm btn-outline-info" data-file-path="${t.file_path}" onclick="previewFile(this.getAttribute('data-file-path'))">
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
    if (notes && notes.length > 0) {
        html += `
            <div class="mb-4">
                <h6>笔记记录</h6>
                <div class="list-group">
                    ${notes.map(n => `
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
                <h6>生成笔记</h6>
                <div class="btn-group" role="group">
                    <button class="btn btn-outline-primary" onclick="generateNote('${podcast.id}', 'auto')">
                        规则引擎笔记
                    </button>
                    <button class="btn btn-outline-success" onclick="generateNote('${podcast.id}', 'ai', 'qwen')">
                        通义千问笔记
                    </button>
                    <button class="btn btn-outline-info" onclick="generateNote('${podcast.id}', 'ai', 'deepseek')">
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
async function previewFile(filePath) {
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
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
            if (result.data.type === 'markdown') {
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
