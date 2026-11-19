// =========================================================================
// Copyright (c) 2026 NDKBVH. All rights reserved.
// HỆ THỐNG TRA CỨU HÓA ĐƠN ĐIỆN TỬ, NGƯỜI NỘP THUẾ & ĐỌC HÓA ĐƠN XML RPA
// =========================================================================

// State variables - Tab 1: Hóa đơn điện tử
let invoiceQueue = [];
let isBatchRunning = false;
let isPaused = false;

// State variables - Tab 2: Người nộp thuế
let nntQueue = [];
let isNntBatchRunning = false;
let isNntPaused = false;

// State variables - Tab 3: Đọc hóa đơn XML
let xmlQueue = [];
let isXmlBatchRunning = false;
let isXmlPaused = false;
let activeXmlPreviewMode = 'crop'; // 'crop' (bản chụp xác nhận) | 'full' (ảnh toàn cảnh)
let currentActiveXmlId = null;

// =========================================================================
// INITIALIZATION & TAB SWITCHING
// =========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Setup tab click listeners directly
    const tabBtnInvoice = document.getElementById('tabBtnInvoice');
    const tabBtnTaxpayer = document.getElementById('tabBtnTaxpayer');
    const tabBtnXml = document.getElementById('tabBtnXml');

    if (tabBtnInvoice) tabBtnInvoice.addEventListener('click', () => switchTab('invoice'));
    if (tabBtnTaxpayer) tabBtnTaxpayer.addEventListener('click', () => switchTab('taxpayer'));
    if (tabBtnXml) tabBtnXml.addEventListener('click', () => switchTab('xml'));

    // Initialize all tabs
    setupDropZone();
    setupControls();
    setupNntControls();
    setupXmlControls();

    // Load histories
    loadHistory();
    loadNntHistory();
    loadXmlHistory();
});

function switchTab(tabName) {
    const tabBtnInvoice = document.getElementById('tabBtnInvoice');
    const tabBtnTaxpayer = document.getElementById('tabBtnTaxpayer');
    const tabBtnXml = document.getElementById('tabBtnXml');
    const tabContentInvoice = document.getElementById('tabContentInvoice');
    const tabContentTaxpayer = document.getElementById('tabContentTaxpayer');
    const tabContentXml = document.getElementById('tabContentXml');

    if (tabName === 'invoice') {
        if (tabBtnInvoice) tabBtnInvoice.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition bg-red-600 text-white shadow-sm';
        if (tabBtnTaxpayer) tabBtnTaxpayer.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition text-slate-600 hover:text-red-600 hover:bg-slate-100';
        if (tabBtnXml) tabBtnXml.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition text-slate-600 hover:text-emerald-700 hover:bg-emerald-50';
        if (tabContentInvoice) tabContentInvoice.classList.remove('hidden');
        if (tabContentTaxpayer) tabContentTaxpayer.classList.add('hidden');
        if (tabContentXml) tabContentXml.classList.add('hidden');
    } else if (tabName === 'taxpayer') {
        if (tabBtnInvoice) tabBtnInvoice.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition text-slate-600 hover:text-red-600 hover:bg-slate-100';
        if (tabBtnTaxpayer) tabBtnTaxpayer.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition bg-blue-600 text-white shadow-sm';
        if (tabBtnXml) tabBtnXml.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition text-slate-600 hover:text-emerald-700 hover:bg-emerald-50';
        if (tabContentInvoice) tabContentInvoice.classList.add('hidden');
        if (tabContentTaxpayer) tabContentTaxpayer.classList.remove('hidden');
        if (tabContentXml) tabContentXml.classList.add('hidden');
    } else if (tabName === 'xml') {
        if (tabBtnInvoice) tabBtnInvoice.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition text-slate-600 hover:text-red-600 hover:bg-slate-100';
        if (tabBtnTaxpayer) tabBtnTaxpayer.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition text-slate-600 hover:text-blue-600 hover:bg-slate-100';
        if (tabBtnXml) tabBtnXml.className = 'tab-btn px-3.5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition bg-emerald-600 text-white shadow-sm';
        if (tabContentInvoice) tabContentInvoice.classList.add('hidden');
        if (tabContentTaxpayer) tabContentTaxpayer.classList.add('hidden');
        if (tabContentXml) tabContentXml.classList.remove('hidden');
    }
}
window.switchTab = switchTab;

function quickCheckNnt(mst) {
    if (!mst) return;
    const cleanMst = mst.trim();
    switchTab('taxpayer');
    const nntInput = document.getElementById('nntSingleMstInput');
    if (nntInput) {
        nntInput.value = cleanMst;
        handleNntSingleSearch();
    }
}
window.quickCheckNnt = quickCheckNnt;

// =========================================================================
// TAB 1: LOGIC TRA CỨU HÓA ĐƠN ĐIỆN TỬ
// =========================================================================
function setupDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    if (dropZone && fileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                handleFilesUpload(files);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleFilesUpload(fileInput.files);
            }
        });
    }

    bindHeadlessToggle('headlessCheckbox', 'headlessLabel');
}

function bindHeadlessToggle(checkboxId, labelId) {
    const checkbox = document.getElementById(checkboxId);
    const label = document.getElementById(labelId);
    if (!checkbox || !label) return;
    const syncLabel = () => {
        label.textContent = checkbox.checked
            ? 'Chạy ngầm (Nhanh - Chỉ chụp web)'
            : 'Mở trình duyệt (Chụp toàn màn hình)';
    };
    syncLabel();
    checkbox.addEventListener('change', syncLabel);
}

async function handleFilesUpload(files) {
    const uploadLoader = document.getElementById('uploadLoader');
    const fileInput = document.getElementById('fileInput');
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    if (uploadLoader) uploadLoader.classList.remove('hidden');
    addLog(`Đang tải lên và phân tích ${files.length} tệp hóa đơn...`, 'info');

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const res = await response.json();
        if (!response.ok || !res.success) {
            throw new Error(res.detail || 'Lỗi khi tải tệp.');
        }

        const newInvoices = res.invoices || [res.data];
        newInvoices.forEach(inv => {
            invoiceQueue.push(inv);
        });

        addLog(`Bóc tách thành công ${newInvoices.length} hóa đơn. Tổng trong danh sách: ${invoiceQueue.length}.`, 'success');
        renderQueueTable();
        updateStats();

    } catch (err) {
        addLog(`Lỗi tải tệp: ${err.message}`, 'error');
        alert(`Lỗi: ${err.message}`);
    } finally {
        if (uploadLoader) uploadLoader.classList.add('hidden');
        if (fileInput) fileInput.value = '';
    }
}

function renderQueueTable() {
    const queueTableBody = document.getElementById('queueTableBody');
    const queueCountBadge = document.getElementById('queueCountBadge');
    const progressContainer = document.getElementById('progressContainer');
    if (!queueTableBody) return;

    queueTableBody.innerHTML = '';
    if (queueCountBadge) queueCountBadge.textContent = `${invoiceQueue.length} hóa đơn`;

    if (invoiceQueue.length === 0) {
        queueTableBody.innerHTML = `
            <tr id="emptyQueueRow">
                <td colspan="10" class="py-10 text-center text-slate-400">
                    <i class="fa-solid fa-folder-open text-3xl mb-2 block opacity-40"></i>
                    Chưa có hóa đơn nào trong danh sách. Hãy kéo thả hoặc chọn tệp hóa đơn ở trên để bắt đầu.
                </td>
            </tr>
        `;
        if (progressContainer) progressContainer.classList.add('hidden');
        return;
    }

    if (progressContainer) progressContainer.classList.remove('hidden');

    invoiceQueue.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.id = `row_${item.id}`;
        tr.className = `transition border-b border-slate-100 hover:bg-slate-50/80 ${getRowStateClass(item.status, item.status_code)}`;

        const statusBadge = getStatusBadgeHtml(item.status, item.status_code, item.message);

        const screenshotBtn = item.screenshot_url 
            ? `<button type="button" onclick="viewActiveScreenshot('${item.id}')" class="text-red-600 hover:text-red-700 font-semibold flex items-center gap-1 mx-auto text-xs bg-red-50 hover:bg-red-100 px-2 py-1 rounded-md transition">
                 <i class="fa-solid fa-camera"></i> Xem ảnh
               </button>`
            : `<span class="text-slate-300">-</span>`;

        tr.innerHTML = `
            <td class="py-2.5 px-3 text-center font-mono font-semibold text-slate-500">${index + 1}</td>
            <td class="py-2.5 px-3">
                <div class="font-medium text-slate-800 truncate max-w-[200px]" title="${escapeHtml(item.file_name || '')}">
                    <i class="fa-solid ${getFileIcon(item.file_name)} mr-1 text-slate-400"></i>
                    ${escapeHtml(item.file_name || 'Hóa đơn')}
                </div>
                ${item.note ? `<div class="text-[10px] text-amber-600 truncate max-w-[200px]" title="${escapeHtml(item.note)}"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(item.note)}</div>` : ''}
            </td>
            <td class="py-2 px-2">
                <div class="flex items-center gap-1">
                    <input type="text" value="${item.mst_nguoi_ban || ''}" onchange="updateQueueField('${item.id}', 'mst_nguoi_ban', this.value)" 
                           class="w-full px-2 py-1 bg-white border border-slate-300 rounded font-mono text-xs focus:ring-1 focus:ring-red-500">
                    ${item.mst_nguoi_ban ? `<button type="button" onclick="quickCheckNnt('${item.mst_nguoi_ban}')" title="Tra cứu MST tại Cục Thuế (Tab 2)" class="p-1 rounded bg-blue-50 hover:bg-blue-100 text-blue-600 text-xs shrink-0 transition"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>` : ''}
                </div>
            </td>
            <td class="py-2 px-2">
                <input type="text" value="${item.ky_hieu || ''}" onchange="updateQueueField('${item.id}', 'ky_hieu', this.value.toUpperCase())" 
                       class="w-full px-2 py-1 bg-white border border-slate-300 rounded font-mono text-xs uppercase focus:ring-1 focus:ring-red-500">
            </td>
            <td class="py-2 px-2">
                <input type="text" value="${item.so_hd || ''}" onchange="updateQueueField('${item.id}', 'so_hd', this.value)" 
                       class="w-full px-2 py-1 bg-white border border-slate-300 rounded font-mono text-xs focus:ring-1 focus:ring-red-500">
            </td>
            <td class="py-2 px-2 text-right">
                <input type="text" value="${formatCurrency(item.tong_tien_thue) || ''}" onchange="updateQueueField('${item.id}', 'tong_tien_thue', this.value)" 
                       class="w-full px-2 py-1 bg-white border border-slate-300 rounded font-mono text-xs text-right focus:ring-1 focus:ring-red-500">
            </td>
            <td class="py-2 px-2 text-right">
                <input type="text" value="${formatCurrency(item.tong_tien) || ''}" onchange="updateQueueField('${item.id}', 'tong_tien', this.value)" 
                       class="w-full px-2 py-1 bg-white border border-slate-300 rounded font-mono text-xs text-right font-bold text-red-700 focus:ring-1 focus:ring-red-500">
            </td>
            <td class="py-2.5 px-3 text-center" id="status_col_${item.id}">
                ${statusBadge}
            </td>
            <td class="py-2.5 px-3 text-center" id="screenshot_col_${item.id}">
                ${screenshotBtn}
            </td>
            <td class="py-2.5 px-3 text-center">
                <div class="flex items-center justify-center gap-1.5">
                    <button type="button" onclick="runSingleInvoice('${item.id}')" title="Tra cứu dòng này" class="p-1.5 rounded hover:bg-slate-200 text-slate-600 hover:text-red-600 transition">
                        <i class="fa-solid fa-play text-xs"></i>
                    </button>
                    <button type="button" onclick="removeQueueItem('${item.id}')" title="Xóa khỏi danh sách" class="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600 transition">
                        <i class="fa-solid fa-trash text-xs"></i>
                    </button>
                </div>
            </td>
        `;
        queueTableBody.appendChild(tr);
    });
}
window.renderQueueTable = renderQueueTable;

function getFileIcon(filename) {
    if (!filename) return 'fa-file';
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'pdf') return 'fa-file-pdf text-red-500';
    if (ext === 'xml') return 'fa-file-code text-blue-500';
    if (ext === 'zip') return 'fa-file-zipper text-amber-500';
    return 'fa-file-lines text-slate-400';
}

function getRowStateClass(status, statusCode) {
    if (status === 'running') return 'row-running';
    if (statusCode === 'FOUND') return 'row-success';
    if (statusCode === 'NOT_FOUND' || status === 'error') return 'row-error';
    return '';
}

function getStatusBadgeHtml(status, statusCode, message) {
    if (status === 'running') {
        return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 animate-pulse">
                    <i class="fa-solid fa-spinner fa-spin"></i> Đang tra cứu...
                </span>`;
    }
    if (statusCode === 'FOUND') {
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800" title="${escapeHtml(message || 'Hợp lệ')}">
                    <i class="fa-solid fa-check"></i> Hợp lệ
                </span>`;
    }
    if (statusCode === 'NOT_FOUND') {
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800" title="${escapeHtml(message || 'Không tìm thấy')}">
                    <i class="fa-solid fa-xmark"></i> Không tìm thấy
                </span>`;
    }
    if (status === 'error') {
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800" title="${escapeHtml(message || 'Lỗi xử lý')}">
                    <i class="fa-solid fa-triangle-exclamation"></i> Lỗi
                </span>`;
    }
    return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                <i class="fa-regular fa-clock"></i> Chờ xử lý
            </span>`;
}

function updateQueueField(id, field, value) {
    const item = invoiceQueue.find(x => x.id === id);
    if (item) {
        item[field] = value;
    }
}
window.updateQueueField = updateQueueField;

function removeQueueItem(id) {
    invoiceQueue = invoiceQueue.filter(x => x.id !== id);
    renderQueueTable();
    updateStats();
}
window.removeQueueItem = removeQueueItem;

function updateStats() {
    const statTotal = document.getElementById('statTotal');
    const statPending = document.getElementById('statPending');
    const statFound = document.getElementById('statFound');
    const statNotFound = document.getElementById('statNotFound');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressText = document.getElementById('progressText');

    const total = invoiceQueue.length;
    const pending = invoiceQueue.filter(x => !x.status_code && x.status !== 'error').length;
    const found = invoiceQueue.filter(x => x.status_code === 'FOUND').length;
    const notFound = invoiceQueue.filter(x => x.status_code === 'NOT_FOUND' || x.status === 'error').length;
    const completed = total - pending;

    if (statTotal) statTotal.textContent = `Tổng: ${total}`;
    if (statPending) statPending.textContent = `Chờ: ${pending}`;
    if (statFound) statFound.textContent = `Hợp lệ: ${found}`;
    if (statNotFound) statNotFound.textContent = `Không thấy/Lỗi: ${notFound}`;

    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    if (progressBarFill) progressBarFill.style.width = `${pct}%`;
    if (progressText) {
        progressText.innerHTML = isBatchRunning
            ? `<i class="fa-solid fa-spinner fa-spin text-red-600"></i> Đang xử lý: ${completed}/${total} hóa đơn (${pct}%)`
            : `<i class="fa-solid fa-check-double text-emerald-600"></i> Tiến độ: ${completed}/${total} hóa đơn (${pct}%)`;
    }
}

function setupControls() {
    const btnStartBatch = document.getElementById('btnStartBatch');
    const btnPauseBatch = document.getElementById('btnPauseBatch');
    const btnClearQueue = document.getElementById('btnClearQueue');
    const btnExportExcel = document.getElementById('btnExportExcel');
    const btnDownloadZip = document.getElementById('btnDownloadZip');
    const btnTransferMstToNnt = document.getElementById('btnTransferMstToNnt');
    const btnClearHistory = document.getElementById('btnClearHistory');
    const btnExportHistoryExcel = document.getElementById('btnExportHistoryExcel');

    if (btnStartBatch) {
        btnStartBatch.addEventListener('click', () => {
            if (invoiceQueue.length === 0) {
                alert('Vui lòng tải ít nhất một hóa đơn vào danh sách.');
                return;
            }
            startBatchProcess();
        });
    }

    if (btnPauseBatch) {
        btnPauseBatch.addEventListener('click', () => {
            isPaused = true;
            btnPauseBatch.classList.add('hidden');
            if (btnStartBatch) {
                btnStartBatch.classList.remove('hidden');
                btnStartBatch.innerHTML = `<i class="fa-solid fa-play"></i> Tiếp Tục Tra Cứu`;
            }
            addLog('Người dùng đã yêu cầu tạm dừng tiến trình tra cứu.', 'warning');
        });
    }

    if (btnClearQueue) {
        btnClearQueue.addEventListener('click', () => {
            if (isBatchRunning) {
                alert('Vui lòng tạm dừng tiến trình trước khi xóa danh sách.');
                return;
            }
            if (confirm('Bạn có chắc chắn muốn xóa toàn bộ danh sách hóa đơn đang chờ?')) {
                invoiceQueue = [];
                renderQueueTable();
                updateStats();
                addLog('Đã dọn sạch hàng đợi hóa đơn.', 'info');
            }
        });
    }

    if (btnExportExcel) {
        btnExportExcel.addEventListener('click', () => {
            exportExcel(invoiceQueue);
        });
    }

    if (btnDownloadZip) {
        btnDownloadZip.addEventListener('click', () => {
            downloadScreenshotsZip(invoiceQueue);
        });
    }

    if (btnTransferMstToNnt) {
        btnTransferMstToNnt.addEventListener('click', () => {
            const validMsts = invoiceQueue.map(x => ({
                mst: (x.mst_nguoi_ban || '').trim(),
                file_name: x.file_name || ''
            })).filter(x => x.mst);

            if (validMsts.length === 0) {
                alert('Chưa có hóa đơn nào có Mã Số Thuế để chuyển sang tra cứu NNT.');
                return;
            }

            let addedCount = 0;
            validMsts.forEach(item => {
                const cleanMst = item.mst.replace(/\s+/g, '');
                let existing = nntQueue.find(x => x.mst === cleanMst);
                if (!existing) {
                    nntQueue.push({
                        id: 'nnt_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
                        mst: cleanMst,
                        ten_nnt: '',
                        dia_chi: '',
                        co_quan_thue: '',
                        trang_thai_mst: '',
                        file_sources: item.file_name ? [item.file_name] : [],
                        status: 'pending',
                        status_code: '',
                        message: '',
                        screenshot_url: '',
                        screenshot_filename: '',
                        timestamp: ''
                    });
                    addedCount++;
                } else {
                    if (item.file_name && !existing.file_sources.includes(item.file_name)) {
                        existing.file_sources.push(item.file_name);
                    }
                }
            });

            switchTab('taxpayer');
            renderNntQueueTable();
            updateNntStats();
            addNntLog(`Đã chuyển ${addedCount} Mã Số Thuế từ hóa đơn Tab 1 sang danh sách tra cứu NNT.`, 'success');

            const nntAutoRun = document.getElementById('nntAutoRunCheckbox');
            if (nntAutoRun && nntAutoRun.checked) {
                startNntBatch();
            }
        });
    }

    if (btnClearHistory) {
        btnClearHistory.addEventListener('click', async () => {
            if (confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử tra cứu hóa đơn không?')) {
                try {
                    await fetch('/api/history', { method: 'DELETE' });
                    loadHistory();
                    addLog('Đã xóa toàn bộ lịch sử tra cứu hóa đơn.', 'info');
                } catch (e) {
                    alert('Không thể xóa lịch sử.');
                }
            }
        });
    }

    if (btnExportHistoryExcel) {
        btnExportHistoryExcel.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/history');
                const data = await res.json();
                exportExcel(data.history || []);
            } catch (e) {
                alert('Lỗi xuất Excel lịch sử.');
            }
        });
    }
}

async function startBatchProcess() {
    const btnStartBatch = document.getElementById('btnStartBatch');
    const btnPauseBatch = document.getElementById('btnPauseBatch');
    const rpaStatusIndicator = document.getElementById('rpaStatusIndicator');

    isBatchRunning = true;
    isPaused = false;
    if (btnStartBatch) btnStartBatch.classList.add('hidden');
    if (btnPauseBatch) btnPauseBatch.classList.remove('hidden');
    if (rpaStatusIndicator) rpaStatusIndicator.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Đang chạy RPA`;

    addLog(`=== BẮT ĐẦU TRA CỨU HÀNG LOẠT (${invoiceQueue.length} HÓA ĐƠN) ===`, 'info');

    for (let i = 0; i < invoiceQueue.length; i++) {
        if (isPaused) {
            addLog('Tiến trình đã tạm dừng. Nhấn Tiếp Tục để chạy tiếp.', 'warning');
            break;
        }

        const item = invoiceQueue[i];
        if (item.status_code === 'FOUND') {
            continue;
        }

        await processInvoiceItem(item, i + 1, invoiceQueue.length);
        updateStats();

        if (i < invoiceQueue.length - 1 && !isPaused) {
            await new Promise(r => setTimeout(r, 1000));
        }
    }

    isBatchRunning = false;
    if (btnPauseBatch) btnPauseBatch.classList.add('hidden');
    if (btnStartBatch) {
        btnStartBatch.classList.remove('hidden');
        btnStartBatch.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Tra Cứu Lại Toàn Bộ`;
    }
    if (rpaStatusIndicator) rpaStatusIndicator.innerHTML = `<span class="w-2 h-2 rounded-full bg-slate-500"></span> Chờ lệnh`;

    addLog('=== HOÀN TẤT ĐỢT TRA CỨU HÀNG LOẠT ===', 'success');
    loadHistory();
}

async function runSingleInvoice(itemId) {
    const item = invoiceQueue.find(x => x.id === itemId);
    if (!item) return;
    const index = invoiceQueue.indexOf(item) + 1;
    await processInvoiceItem(item, index, invoiceQueue.length);
    updateStats();
    loadHistory();
}
window.runSingleInvoice = runSingleInvoice;

async function processInvoiceItem(item, currentIdx, totalCount) {
    const headlessCheckbox = document.getElementById('headlessCheckbox');
    item.status = 'running';
    renderQueueTable();

    addLog(`[${currentIdx}/${totalCount}] Đang xử lý: ${item.file_name} | MST: ${item.mst_nguoi_ban} | Số HĐ: ${item.so_hd}...`, 'info');

    const payload = {
        mst_nguoi_ban: item.mst_nguoi_ban || '',
        loai_hd: item.loai_hd || 'Hóa đơn điện tử giá trị gia tăng',
        ky_hieu: (item.ky_hieu || '').toUpperCase(),
        so_hd: item.so_hd || '',
        tong_tien_thue: item.tong_tien_thue || '',
        tong_tien: item.tong_tien || '',
        headless: headlessCheckbox ? headlessCheckbox.checked : false
    };

    try {
        const response = await fetch('/api/lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();

        if (res.logs && res.logs.length > 0) {
            res.logs.forEach(msg => addLog(`  ↳ ${msg}`, 'console'));
        }

        item.status = res.success ? 'success' : (res.status_code === 'NOT_FOUND' ? 'not_found' : 'error');
        item.status_code = res.status_code || '';
        item.message = res.message || '';
        item.details = res.details || [];
        item.screenshot_url = res.screenshot_url || '';
        item.screenshot_filename = res.screenshot_filename || '';

        if (res.status_code === 'FOUND') {
            addLog(`[${currentIdx}/${totalCount}] ✅ KẾT QUẢ: TỒN TẠI HÓA ĐƠN HỢP LỆ! (${item.file_name})`, 'success');
        } else if (res.status_code === 'NOT_FOUND') {
            addLog(`[${currentIdx}/${totalCount}] ❌ KẾT QUẢ: KHÔNG TỒN TẠI HÓA ĐƠN! (${item.file_name})`, 'error');
        } else {
            addLog(`[${currentIdx}/${totalCount}] ⚠️ KẾT QUẢ: ${res.message || 'Lỗi tra cứu'}`, 'warning');
        }

        viewActiveScreenshot(item.id);

    } catch (err) {
        item.status = 'error';
        item.message = err.message;
        addLog(`[${currentIdx}/${totalCount}] Lỗi mạng khi tra cứu: ${err.message}`, 'error');
    }

    renderQueueTable();
}

function viewActiveScreenshot(itemId) {
    const item = invoiceQueue.find(x => x.id === itemId);
    if (!item || !item.screenshot_url) return;

    const placeholder = document.getElementById('activeScreenshotPlaceholder');
    const img = document.getElementById('activeScreenshotImg');
    const overlay = document.getElementById('activeScreenshotOverlay');
    const btnDownload = document.getElementById('btnDownloadActiveScreenshot');
    const badge = document.getElementById('activeResultBadge');
    const details = document.getElementById('activeResultDetails');
    const title = document.getElementById('activeResultTitle');
    const sub = document.getElementById('activeResultSub');

    if (placeholder) placeholder.classList.add('hidden');
    if (img) {
        img.src = item.screenshot_url;
        img.classList.remove('hidden');
    }
    if (overlay) overlay.classList.remove('hidden');
    if (btnDownload) btnDownload.href = item.screenshot_url;

    if (badge) {
        badge.classList.remove('hidden');
        if (item.status_code === 'FOUND') {
            badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800';
            badge.textContent = 'HỢP LỆ (TỒN TẠI)';
        } else {
            badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800';
            badge.textContent = 'KHÔNG TỒN TẠI / LỖI';
        }
    }

    if (details) details.classList.remove('hidden');
    if (title) title.textContent = `${item.file_name || 'Hóa đơn'} - Số: ${item.so_hd} (Ký hiệu: ${item.ky_hieu})`;
    if (sub) sub.textContent = item.message || (item.details ? item.details.join(' | ') : '');
}
window.viewActiveScreenshot = viewActiveScreenshot;

async function exportExcel(invoices) {
    if (!invoices || invoices.length === 0) {
        alert('Không có dữ liệu để xuất Excel.');
        return;
    }

    addLog('Đang khởi tạo tệp Excel báo cáo đối soát...', 'info');
    try {
        const response = await fetch('/api/export-excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ invoices: invoices })
        });

        if (!response.ok) throw new Error('Lỗi xuất tệp Excel.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BangKe_DoiSoat_HoaDon_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        addLog('Đã tải về tệp Báo cáo đối soát Excel thành công!', 'success');
    } catch (e) {
        addLog(`Lỗi xuất Excel: ${e.message}`, 'error');
        alert(`Lỗi xuất Excel: ${e.message}`);
    }
}

async function downloadScreenshotsZip(invoices) {
    const urls = invoices.map(x => x.screenshot_url).filter(Boolean);
    if (urls.length === 0) {
        alert('Chưa có ảnh chụp xác nhận nào để tải về.');
        return;
    }

    addLog(`Đang đóng gói ${urls.length} ảnh bằng chứng vào tệp .zip...`, 'info');
    try {
        const response = await fetch('/api/download-batch-screenshots', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ screenshots: urls })
        });

        if (!response.ok) throw new Error('Lỗi đóng gói tệp ZIP.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Anh_XacNhan_HoaDon_${new Date().toISOString().slice(0, 10)}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        addLog('Đã tải về gói ảnh xác nhận (.zip) thành công!', 'success');
    } catch (e) {
        addLog(`Lỗi tải ZIP: ${e.message}`, 'error');
        alert(`Lỗi tải ZIP: ${e.message}`);
    }
}

async function loadHistory() {
    const historyTableBody = document.getElementById('historyTableBody');
    if (!historyTableBody) return;

    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        const history = data.history || [];

        if (history.length === 0) {
            historyTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="py-6 text-center text-slate-400">Chưa có lịch sử tra cứu nào được lưu.</td>
                </tr>
            `;
            return;
        }

        historyTableBody.innerHTML = '';
        history.forEach(item => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition';

            const statusBadge = item.status_code === 'FOUND'
                ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                     <i class="fa-solid fa-check"></i> Hợp lệ
                   </span>`
                : `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                     <i class="fa-solid fa-xmark"></i> Không tồn tại
                   </span>`;

            const screenshotLink = item.screenshot_url
                ? `<button onclick="openLightbox('${item.screenshot_url}')" class="text-red-600 hover:text-red-700 font-semibold flex items-center gap-1 ml-auto">
                     <i class="fa-solid fa-image"></i> Xem
                   </button>`
                : `<span class="text-slate-300">-</span>`;

            tr.innerHTML = `
                <td class="py-2 px-3 font-mono text-slate-500">${item.timestamp}</td>
                <td class="py-2 px-3 font-mono font-medium text-slate-800">${item.mst_nguoi_ban}</td>
                <td class="py-2 px-3 font-mono text-slate-700">${item.ky_hieu}</td>
                <td class="py-2 px-3 font-mono font-semibold text-slate-800">${item.so_hd}</td>
                <td class="py-2 px-3 font-mono text-slate-700 font-bold">${formatCurrency(item.tong_tien)} đ</td>
                <td class="py-2 px-3">${statusBadge}</td>
                <td class="py-2 px-3 text-right">${screenshotLink}</td>
            `;
            historyTableBody.appendChild(tr);
        });
    } catch (e) {
        console.error('Lỗi nạp lịch sử hóa đơn:', e);
    }
}

// =========================================================================
// TAB 2: LOGIC TRA CỨU NGƯỜI NỘP THUẾ (TRACUUNNT.GDT.GOV.VN)
// =========================================================================
function setupNntControls() {
    const nntDropZone = document.getElementById('nntDropZone');
    const nntFileInput = document.getElementById('nntFileInput');
    const btnNntSingleSearch = document.getElementById('btnNntSingleSearch');
    const nntSingleMstInput = document.getElementById('nntSingleMstInput');
    const btnNntAddBatch = document.getElementById('btnNntAddBatch');
    const btnNntStartBatch = document.getElementById('btnNntStartBatch');
    const btnNntPauseBatch = document.getElementById('btnNntPauseBatch');
    const btnNntClearQueue = document.getElementById('btnNntClearQueue');
    const btnNntExportExcel = document.getElementById('btnNntExportExcel');
    const btnNntDownloadZip = document.getElementById('btnNntDownloadZip');
    const btnExportNntHistoryExcel = document.getElementById('btnExportNntHistoryExcel');
    const btnClearNntHistory = document.getElementById('btnClearNntHistory');

    bindHeadlessToggle('nntHeadlessCheckbox', 'nntHeadlessLabel');

    if (nntDropZone && nntFileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            nntDropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                nntDropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            nntDropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                nntDropZone.classList.remove('dragover');
            });
        });

        nntDropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                handleNntFilesUpload(files);
            }
        });

        nntFileInput.addEventListener('change', () => {
            if (nntFileInput.files.length > 0) {
                handleNntFilesUpload(nntFileInput.files);
            }
        });
    }

    if (btnNntSingleSearch) btnNntSingleSearch.addEventListener('click', handleNntSingleSearch);
    if (nntSingleMstInput) {
        nntSingleMstInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleNntSingleSearch();
        });
    }

    if (btnNntAddBatch) btnNntAddBatch.addEventListener('click', handleNntAddBatch);

    if (btnNntStartBatch) {
        btnNntStartBatch.addEventListener('click', () => {
            if (nntQueue.length === 0) {
                alert('Vui lòng thêm ít nhất một Mã Số Thuế vào danh sách.');
                return;
            }
            startNntBatch();
        });
    }

    if (btnNntPauseBatch) {
        btnNntPauseBatch.addEventListener('click', () => {
            isNntPaused = true;
            btnNntPauseBatch.classList.add('hidden');
            if (btnNntStartBatch) {
                btnNntStartBatch.classList.remove('hidden');
                btnNntStartBatch.innerHTML = `<i class="fa-solid fa-play"></i> Tiếp Tục Tra Cứu`;
            }
            addNntLog('Người dùng đã yêu cầu tạm dừng tiến trình tra cứu NNT.', 'warning');
        });
    }

    if (btnNntClearQueue) {
        btnNntClearQueue.addEventListener('click', () => {
            if (isNntBatchRunning) {
                alert('Vui lòng tạm dừng tiến trình trước khi xóa danh sách.');
                return;
            }
            if (confirm('Bạn có chắc chắn muốn xóa toàn bộ danh sách Mã Số Thuế?')) {
                nntQueue = [];
                renderNntQueueTable();
                updateNntStats();
                addNntLog('Đã dọn sạch hàng đợi Người Nộp Thuế.', 'info');
            }
        });
    }

    if (btnNntExportExcel) {
        btnNntExportExcel.addEventListener('click', () => {
            exportNntExcel(nntQueue);
        });
    }

    if (btnNntDownloadZip) {
        btnNntDownloadZip.addEventListener('click', () => {
            downloadNntScreenshotsZip(nntQueue);
        });
    }

    if (btnExportNntHistoryExcel) {
        btnExportNntHistoryExcel.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/nnt/history');
                const data = await res.json();
                exportNntExcel(data.history || []);
            } catch (e) {
                alert('Lỗi xuất Excel lịch sử NNT.');
            }
        });
    }

    if (btnClearNntHistory) {
        btnClearNntHistory.addEventListener('click', async () => {
            if (confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử tra cứu Người Nộp Thuế?')) {
                try {
                    await fetch('/api/nnt/history', { method: 'DELETE' });
                    loadNntHistory();
                    addNntLog('Đã xóa toàn bộ lịch sử tra cứu NNT.', 'info');
                } catch (e) {
                    alert('Không thể xóa lịch sử NNT.');
                }
            }
        });
    }
}

async function handleNntFilesUpload(files) {
    const nntUploadLoader = document.getElementById('nntUploadLoader');
    const nntFileInput = document.getElementById('nntFileInput');
    const nntAutoRunCheckbox = document.getElementById('nntAutoRunCheckbox');
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    if (nntUploadLoader) nntUploadLoader.classList.remove('hidden');
    addNntLog(`Đang tải lên và bóc tách MST từ ${files.length} tệp hóa đơn...`, 'info');

    try {
        const response = await fetch('/api/nnt/upload', {
            method: 'POST',
            body: formData
        });

        const res = await response.json();
        if (!response.ok || !res.success) {
            throw new Error(res.detail || 'Lỗi khi bóc tách hóa đơn.');
        }

        const items = res.items || [];
        let addedCount = 0;

        items.forEach(newItem => {
            const existing = nntQueue.find(x => x.mst === newItem.mst);
            if (!existing) {
                nntQueue.push(newItem);
                addedCount++;
            } else {
                if (newItem.file_sources) {
                    newItem.file_sources.forEach(src => {
                        if (!existing.file_sources.includes(src)) {
                            existing.file_sources.push(src);
                        }
                    });
                }
                if (!existing.ten_nnt && newItem.ten_nnt) {
                    existing.ten_nnt = newItem.ten_nnt;
                }
            }
        });

        addNntLog(`Bóc tách thành công ${items.length} MST (${addedCount} MST mới). Tổng trong danh sách: ${nntQueue.length}.`, 'success');
        renderNntQueueTable();
        updateNntStats();

        if (nntAutoRunCheckbox && nntAutoRunCheckbox.checked && !isNntBatchRunning) {
            addNntLog('Tùy chọn "Tự động tra cứu" đang bật: Khởi chạy RPA ngay lập tức...', 'info');
            startNntBatch();
        }

    } catch (err) {
        addNntLog(`Lỗi bóc tách hóa đơn: ${err.message}`, 'error');
        alert(`Lỗi: ${err.message}`);
    } finally {
        if (nntUploadLoader) nntUploadLoader.classList.add('hidden');
        if (nntFileInput) nntFileInput.value = '';
    }
}

async function handleNntSingleSearch() {
    const nntSingleMstInput = document.getElementById('nntSingleMstInput');
    if (!nntSingleMstInput) return;
    const rawMst = nntSingleMstInput.value.trim();
    if (!rawMst) {
        alert('Vui lòng nhập Mã Số Thuế (MST).');
        nntSingleMstInput.focus();
        return;
    }

    const cleanMst = rawMst.replace(/\s+/g, '');
    let item = nntQueue.find(x => x.mst === cleanMst);
    if (!item) {
        item = {
            id: 'nnt_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
            mst: cleanMst,
            ten_nnt: '',
            dia_chi: '',
            co_quan_thue: '',
            trang_thai_mst: '',
            file_sources: ['Nhập tay'],
            status: 'pending',
            status_code: '',
            message: '',
            screenshot_url: '',
            screenshot_filename: '',
            timestamp: ''
        };
        nntQueue.unshift(item);
    }

    renderNntQueueTable();
    updateNntStats();

    const idx = nntQueue.indexOf(item) + 1;
    await processNntItem(item, idx, nntQueue.length);
    updateNntStats();
    loadNntHistory();
}
window.handleNntSingleSearch = handleNntSingleSearch;

function handleNntAddBatch() {
    const nntBatchTextarea = document.getElementById('nntBatchTextarea');
    const nntAutoRunCheckbox = document.getElementById('nntAutoRunCheckbox');
    if (!nntBatchTextarea) return;

    const text = nntBatchTextarea.value.trim();
    if (!text) {
        alert('Vui lòng dán danh sách Mã Số Thuế vào ô bên cạnh (mỗi MST 1 dòng).');
        return;
    }

    const lines = text.split(/[\r\n,;]+/).map(x => x.trim()).filter(Boolean);
    let addedCount = 0;

    lines.forEach(mst => {
        const cleanMst = mst.replace(/\s+/g, '');
        if (!cleanMst) return;
        if (!nntQueue.some(x => x.mst === cleanMst)) {
            nntQueue.push({
                id: 'nnt_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
                mst: cleanMst,
                ten_nnt: '',
                dia_chi: '',
                co_quan_thue: '',
                trang_thai_mst: '',
                file_sources: ['Nhập tay'],
                status: 'pending',
                status_code: '',
                message: '',
                screenshot_url: '',
                screenshot_filename: '',
                timestamp: ''
            });
            addedCount++;
        }
    });

    nntBatchTextarea.value = '';
    renderNntQueueTable();
    updateNntStats();
    addNntLog(`Đã nạp ${addedCount} Mã Số Thuế vào danh sách chờ tra cứu.`, 'success');

    if (nntAutoRunCheckbox && nntAutoRunCheckbox.checked && !isNntBatchRunning) {
        startNntBatch();
    }
}
window.handleNntAddBatch = handleNntAddBatch;

async function startNntBatch() {
    const btnNntStartBatch = document.getElementById('btnNntStartBatch');
    const btnNntPauseBatch = document.getElementById('btnNntPauseBatch');
    const nntRpaStatusIndicator = document.getElementById('nntRpaStatusIndicator');

    isNntBatchRunning = true;
    isNntPaused = false;
    if (btnNntStartBatch) btnNntStartBatch.classList.add('hidden');
    if (btnNntPauseBatch) btnNntPauseBatch.classList.remove('hidden');
    if (nntRpaStatusIndicator) nntRpaStatusIndicator.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Đang chạy RPA NNT`;

    addNntLog(`=== BẮT ĐẦU TRA CỨU NNT HÀNG LOẠT (${nntQueue.length} MST) ===`, 'info');

    for (let i = 0; i < nntQueue.length; i++) {
        if (isNntPaused) {
            addNntLog('Tiến trình NNT đã tạm dừng. Nhấn Tiếp Tục để chạy tiếp.', 'warning');
            break;
        }

        const item = nntQueue[i];
        if (item.status_code === 'FOUND') {
            continue;
        }

        await processNntItem(item, i + 1, nntQueue.length);
        updateNntStats();

        if (i < nntQueue.length - 1 && !isNntPaused) {
            await new Promise(r => setTimeout(r, 1000));
        }
    }

    isNntBatchRunning = false;
    if (btnNntPauseBatch) btnNntPauseBatch.classList.add('hidden');
    if (btnNntStartBatch) {
        btnNntStartBatch.classList.remove('hidden');
        btnNntStartBatch.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Tra Cứu Lại NNT`;
    }
    if (nntRpaStatusIndicator) nntRpaStatusIndicator.innerHTML = `<span class="w-2 h-2 rounded-full bg-slate-500"></span> Chờ lệnh`;

    addNntLog('=== HOÀN TẤT ĐỢT TRA CỨU NGƯỜI NỘP THUẾ HÀNG LOẠT ===', 'success');
    loadNntHistory();
}

async function processNntItem(item, currentIdx, totalCount) {
    const nntHeadlessCheckbox = document.getElementById('nntHeadlessCheckbox');
    item.status = 'running';
    renderNntQueueTable();

    addNntLog(`[${currentIdx}/${totalCount}] Đang tra cứu Cục Thuế cho MST: ${item.mst}...`, 'info');

    const payload = {
        mst: item.mst,
        headless: nntHeadlessCheckbox ? nntHeadlessCheckbox.checked : false
    };

    try {
        const response = await fetch('/api/nnt/lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();

        if (res.logs && res.logs.length > 0) {
            res.logs.forEach(msg => addNntLog(`  ↳ ${msg}`, 'console'));
        }

        item.status = res.success ? 'success' : (res.status_code === 'NOT_FOUND' ? 'not_found' : 'error');
        item.status_code = res.status_code || '';
        item.message = res.message || '';
        item.ten_nnt = res.data ? res.data.ten_nnt : (item.ten_nnt || '');
        item.dia_chi = res.data ? res.data.dia_chi : '';
        item.co_quan_thue = res.data ? res.data.co_quan_thue : '';
        item.trang_thai_mst = res.data ? res.data.trang_thai_mst : '';
        item.screenshot_url = res.screenshot_url || '';
        item.screenshot_filename = res.screenshot_filename || '';
        item.timestamp = res.timestamp || '';

        if (res.status_code === 'FOUND') {
            addNntLog(`[${currentIdx}/${totalCount}] ✅ KẾT QUẢ: TÌM THẤY NNT! (${item.mst} - ${item.ten_nnt}) | ${item.trang_thai_mst}`, 'success');
        } else if (res.status_code === 'NOT_FOUND') {
            addNntLog(`[${currentIdx}/${totalCount}] ❌ KẾT QUẢ: KHÔNG TÌM THẤY NNT VỚI MST ${item.mst}!`, 'error');
        } else {
            addNntLog(`[${currentIdx}/${totalCount}] ⚠️ KẾT QUẢ: ${res.message || 'Lỗi tra cứu NNT'}`, 'warning');
        }

        viewNntActiveScreenshot(item.id);

    } catch (err) {
        item.status = 'error';
        item.message = err.message;
        addNntLog(`[${currentIdx}/${totalCount}] Lỗi mạng khi tra cứu NNT: ${err.message}`, 'error');
    }

    renderNntQueueTable();
}

async function runSingleNntItem(itemId) {
    const item = nntQueue.find(x => x.id === itemId);
    if (!item) return;
    const idx = nntQueue.indexOf(item) + 1;
    await processNntItem(item, idx, nntQueue.length);
    updateNntStats();
    loadNntHistory();
}
window.runSingleNntItem = runSingleNntItem;

function removeNntQueueItem(itemId) {
    nntQueue = nntQueue.filter(x => x.id !== itemId);
    renderNntQueueTable();
    updateNntStats();
}
window.removeNntQueueItem = removeNntQueueItem;

function updateNntQueueField(id, field, value) {
    const item = nntQueue.find(x => x.id === id);
    if (item) {
        item[field] = value;
    }
}
window.updateNntQueueField = updateNntQueueField;

function renderNntQueueTable() {
    const nntQueueTableBody = document.getElementById('nntQueueTableBody');
    const nntQueueCountBadge = document.getElementById('nntQueueCountBadge');
    const nntProgressContainer = document.getElementById('nntProgressContainer');
    if (!nntQueueTableBody) return;

    nntQueueTableBody.innerHTML = '';
    if (nntQueueCountBadge) nntQueueCountBadge.textContent = `${nntQueue.length} MST`;

    if (nntQueue.length === 0) {
        nntQueueTableBody.innerHTML = `
            <tr id="nntEmptyQueueRow">
                <td colspan="9" class="py-10 text-center text-slate-400">
                    <i class="fa-solid fa-building-circle-check text-3xl mb-2 block opacity-40"></i>
                    Chưa có mã số thuế nào được nạp. Hãy tải tệp hóa đơn lên ở trên hoặc nhập MST để bắt đầu tra cứu.
                </td>
            </tr>
        `;
        if (nntProgressContainer) nntProgressContainer.classList.add('hidden');
        return;
    }

    if (nntProgressContainer) nntProgressContainer.classList.remove('hidden');

    nntQueue.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.id = `nnt_row_${item.id}`;
        tr.className = `transition border-b border-slate-100 hover:bg-slate-50/80 ${getNntRowStateClass(item.status, item.status_code, item.trang_thai_mst)}`;

        const statusBadge = getNntStatusBadgeHtml(item.status, item.status_code, item.trang_thai_mst, item.message);

        const screenshotBtn = item.screenshot_url 
            ? `<button type="button" onclick="viewNntActiveScreenshot('${item.id}')" class="text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1 mx-auto text-xs bg-blue-50 hover:bg-blue-100 px-2 py-1 rounded-md transition">
                 <i class="fa-solid fa-camera"></i> Xem ảnh
               </button>`
            : `<span class="text-slate-300">-</span>`;

        let sourceHtml = '<span class="text-slate-400 italic text-[11px]">Nhập tay</span>';
        if (item.file_sources && item.file_sources.length > 0 && item.file_sources[0] !== 'Nhập tay') {
            sourceHtml = item.file_sources.map(src => 
                `<span class="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-mono font-medium truncate max-w-[130px]" title="${escapeHtml(src)}">
                    <i class="fa-regular fa-file-lines mr-0.5"></i>${escapeHtml(src)}
                 </span>`
            ).join(' ');
        }

        tr.innerHTML = `
            <td class="py-2.5 px-3 text-center font-mono font-semibold text-slate-500">${index + 1}</td>
            <td class="py-2 px-2">
                <input type="text" value="${item.mst || ''}" onchange="updateNntQueueField('${item.id}', 'mst', this.value.trim())" 
                       class="w-full px-2 py-1 bg-white border border-slate-300 rounded font-mono font-bold text-slate-800 text-xs focus:ring-1 focus:ring-blue-500">
            </td>
            <td class="py-2.5 px-3 max-w-[150px]">
                <div class="flex flex-wrap gap-1">${sourceHtml}</div>
            </td>
            <td class="py-2.5 px-3 font-semibold text-slate-800">
                ${item.ten_nnt ? escapeHtml(item.ten_nnt) : `<span class="text-slate-400 italic">Chưa tra cứu</span>`}
            </td>
            <td class="py-2.5 px-3 text-slate-600 max-w-[220px] truncate" title="${item.dia_chi || ''}">
                ${item.dia_chi ? escapeHtml(item.dia_chi) : `<span class="text-slate-400">-</span>`}
            </td>
            <td class="py-2.5 px-3 text-slate-600 max-w-[150px] truncate" title="${item.co_quan_thue || ''}">
                ${item.co_quan_thue ? escapeHtml(item.co_quan_thue) : `<span class="text-slate-400">-</span>`}
            </td>
            <td class="py-2.5 px-3 text-center">
                ${statusBadge}
            </td>
            <td class="py-2.5 px-3 text-center">
                ${screenshotBtn}
            </td>
            <td class="py-2.5 px-3 text-center">
                <div class="flex items-center justify-center gap-1.5">
                    <button type="button" onclick="runSingleNntItem('${item.id}')" title="Tra cứu MST này" class="p-1.5 rounded hover:bg-slate-200 text-slate-600 hover:text-blue-600 transition">
                        <i class="fa-solid fa-play text-xs"></i>
                    </button>
                    <button type="button" onclick="removeNntQueueItem('${item.id}')" title="Xóa khỏi danh sách" class="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600 transition">
                        <i class="fa-solid fa-trash text-xs"></i>
                    </button>
                </div>
            </td>
        `;
        nntQueueTableBody.appendChild(tr);
    });
}

function getNntRowStateClass(status, statusCode, trangThaiMst) {
    if (status === 'running') return 'row-running';
    if (statusCode === 'FOUND') {
        if (trangThaiMst && (trangThaiMst.includes('ngừng') || trangThaiMst.includes('đóng') || trangThaiMst.includes('khóa'))) {
            return 'row-error';
        }
        return 'row-success';
    }
    if (statusCode === 'NOT_FOUND' || status === 'error') return 'row-error';
    return '';
}

function getNntStatusBadgeHtml(status, statusCode, trangThaiMst, message) {
    if (status === 'running') {
        return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 animate-pulse">
                    <i class="fa-solid fa-spinner fa-spin"></i> Đang tra cứu...
                </span>`;
    }
    if (statusCode === 'FOUND') {
        const isClosed = trangThaiMst && (trangThaiMst.includes('ngừng') || trangThaiMst.includes('đóng') || trangThaiMst.includes('khóa'));
        if (isClosed) {
            return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900" title="${escapeHtml(trangThaiMst)}">
                        <i class="fa-solid fa-ban"></i> Ngừng HĐ
                    </span>`;
        }
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800" title="${escapeHtml(trangThaiMst || 'Đang hoạt động')}">
                    <i class="fa-solid fa-check"></i> Đang hoạt động
                </span>`;
    }
    if (statusCode === 'NOT_FOUND') {
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800" title="${message || 'Không tìm thấy MST'}">
                    <i class="fa-solid fa-xmark"></i> Không tìm thấy
                </span>`;
    }
    if (status === 'error') {
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800" title="${message || 'Lỗi xử lý'}">
                    <i class="fa-solid fa-triangle-exclamation"></i> Lỗi
                </span>`;
    }
    return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                <i class="fa-regular fa-clock"></i> Chờ xử lý
            </span>`;
}

function updateNntStats() {
    const nntStatTotal = document.getElementById('nntStatTotal');
    const nntStatPending = document.getElementById('nntStatPending');
    const nntStatActive = document.getElementById('nntStatActive');
    const nntStatInactive = document.getElementById('nntStatInactive');
    const nntProgressBarFill = document.getElementById('nntProgressBarFill');
    const nntProgressText = document.getElementById('nntProgressText');

    const total = nntQueue.length;
    const pending = nntQueue.filter(x => !x.status_code && x.status !== 'error').length;
    const active = nntQueue.filter(x => {
        if (x.status_code !== 'FOUND') return false;
        const tt = (x.trang_thai_mst || '').toLowerCase();
        return !tt.includes('ngừng') && !tt.includes('đóng') && !tt.includes('khóa');
    }).length;
    const inactive = nntQueue.filter(x => {
        if (x.status === 'error' || x.status_code === 'NOT_FOUND') return true;
        if (x.status_code === 'FOUND') {
            const tt = (x.trang_thai_mst || '').toLowerCase();
            return tt.includes('ngừng') || tt.includes('đóng') || tt.includes('khóa');
        }
        return false;
    }).length;
    const completed = total - pending;

    if (nntStatTotal) nntStatTotal.textContent = `Tổng: ${total}`;
    if (nntStatPending) nntStatPending.textContent = `Chờ: ${pending}`;
    if (nntStatActive) nntStatActive.textContent = `Đang HĐ: ${active}`;
    if (nntStatInactive) nntStatInactive.textContent = `Ngừng HĐ/Lỗi: ${inactive}`;

    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    if (nntProgressBarFill) nntProgressBarFill.style.width = `${pct}%`;
    if (nntProgressText) {
        nntProgressText.innerHTML = isNntBatchRunning
            ? `<i class="fa-solid fa-spinner fa-spin text-blue-600"></i> Đang xử lý: ${completed}/${total} MST (${pct}%)`
            : `<i class="fa-solid fa-check-double text-blue-600"></i> Tiến độ: ${completed}/${total} MST (${pct}%)`;
    }
}

function viewNntActiveScreenshot(itemId) {
    const item = nntQueue.find(x => x.id === itemId);
    if (!item || !item.screenshot_url) return;

    const placeholder = document.getElementById('nntActiveScreenshotPlaceholder');
    const img = document.getElementById('nntActiveScreenshotImg');
    const overlay = document.getElementById('nntActiveScreenshotOverlay');
    const btnDownload = document.getElementById('btnDownloadNntActiveScreenshot');
    const badge = document.getElementById('nntActiveResultBadge');
    const details = document.getElementById('nntActiveResultDetails');
    const title = document.getElementById('nntActiveResultTitle');
    const sub = document.getElementById('nntActiveResultSub');

    if (placeholder) placeholder.classList.add('hidden');
    if (img) {
        img.src = item.screenshot_url;
        img.classList.remove('hidden');
    }
    if (overlay) overlay.classList.remove('hidden');
    if (btnDownload) btnDownload.href = item.screenshot_url;

    if (badge) {
        badge.classList.remove('hidden');
        if (item.status_code === 'FOUND') {
            const isClosed = item.trang_thai_mst && (item.trang_thai_mst.includes('ngừng') || item.trang_thai_mst.includes('đóng') || item.trang_thai_mst.includes('khóa'));
            if (isClosed) {
                badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-900';
                badge.textContent = 'NGỪNG HOẠT ĐỘNG';
            } else {
                badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800';
                badge.textContent = 'ĐANG HOẠT ĐỘNG';
            }
        } else {
            badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800';
            badge.textContent = 'KHÔNG TÌM THẤY / LỖI';
        }
    }

    if (details) details.classList.remove('hidden');
    if (title) title.textContent = `${item.ten_nnt || 'Người nộp thuế'} - MST: ${item.mst}`;
    if (sub) sub.textContent = `${item.trang_thai_mst || item.message || ''} | ${item.co_quan_thue || ''}`;
}
window.viewNntActiveScreenshot = viewNntActiveScreenshot;

async function exportNntExcel(nntList) {
    if (!nntList || nntList.length === 0) {
        alert('Không có dữ liệu Người Nộp Thuế để xuất Excel.');
        return;
    }

    addNntLog('Đang khởi tạo tệp Excel báo cáo Người Nộp Thuế...', 'info');
    try {
        const response = await fetch('/api/nnt/export-excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nnt_list: nntList })
        });

        if (!response.ok) throw new Error('Lỗi xuất tệp Excel NNT.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BaoCao_TraCuu_NNT_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        addNntLog('Đã tải về tệp Báo cáo Excel Người Nộp Thuế thành công!', 'success');
    } catch (e) {
        addNntLog(`Lỗi xuất Excel NNT: ${e.message}`, 'error');
        alert(`Lỗi xuất Excel NNT: ${e.message}`);
    }
}

async function downloadNntScreenshotsZip(nntList) {
    const urls = nntList.map(x => x.screenshot_url).filter(Boolean);
    if (urls.length === 0) {
        alert('Chưa có ảnh chụp xác nhận NNT nào để tải về.');
        return;
    }

    addNntLog(`Đang đóng gói ${urls.length} ảnh bằng chứng NNT vào tệp .zip...`, 'info');
    try {
        const response = await fetch('/api/download-batch-screenshots', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ screenshots: urls })
        });

        if (!response.ok) throw new Error('Lỗi đóng gói tệp ZIP.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Anh_XacNhan_NNT_${new Date().toISOString().slice(0, 10)}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        addNntLog('Đã tải về gói ảnh xác nhận NNT (.zip) thành công!', 'success');
    } catch (e) {
        addNntLog(`Lỗi tải ZIP NNT: ${e.message}`, 'error');
        alert(`Lỗi tải ZIP NNT: ${e.message}`);
    }
}

async function loadNntHistory() {
    const nntHistoryTableBody = document.getElementById('nntHistoryTableBody');
    if (!nntHistoryTableBody) return;

    try {
        const res = await fetch('/api/nnt/history');
        const data = await res.json();
        const history = data.history || [];

        if (history.length === 0) {
            nntHistoryTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="py-6 text-center text-slate-400">Chưa có lịch sử tra cứu NNT nào được lưu.</td>
                </tr>
            `;
            return;
        }

        nntHistoryTableBody.innerHTML = '';
        history.forEach(item => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition';

            let statusBadge;
            if (item.status_code === 'FOUND') {
                const tt = (item.trang_thai_mst || '').toLowerCase();
                const isClosed = tt.includes('ngừng') || tt.includes('đóng') || tt.includes('khóa');
                if (isClosed) {
                    statusBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-900" title="${escapeHtml(item.trang_thai_mst)}">
                                     <i class="fa-solid fa-ban"></i> Ngừng HĐ
                                   </span>`;
                } else {
                    statusBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800" title="${escapeHtml(item.trang_thai_mst || 'Đang hoạt động')}">
                                     <i class="fa-solid fa-check"></i> Đang HĐ
                                   </span>`;
                }
            } else {
                statusBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                                 <i class="fa-solid fa-xmark"></i> Không tìm thấy
                               </span>`;
            }

            const screenshotLink = item.screenshot_url
                ? `<button onclick="openLightbox('${item.screenshot_url}')" class="text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1 ml-auto">
                     <i class="fa-solid fa-image"></i> Xem
                   </button>`
                : `<span class="text-slate-300">-</span>`;

            tr.innerHTML = `
                <td class="py-2 px-3 font-mono text-slate-500">${item.timestamp || '-'}</td>
                <td class="py-2 px-3 font-mono font-medium text-slate-800">${item.mst}</td>
                <td class="py-2 px-3 font-semibold text-slate-800 max-w-[200px] truncate" title="${item.ten_nnt || ''}">${escapeHtml(item.ten_nnt || '-')}</td>
                <td class="py-2 px-3 text-slate-600 max-w-[180px] truncate" title="${item.co_quan_thue || ''}">${escapeHtml(item.co_quan_thue || '-')}</td>
                <td class="py-2 px-3">${statusBadge}</td>
                <td class="py-2 px-3 text-right">${screenshotLink}</td>
            `;
            nntHistoryTableBody.appendChild(tr);
        });
    } catch (e) {
        console.error('Lỗi nạp lịch sử NNT:', e);
    }
}

// =========================================================================
// TAB 3: LOGIC ĐỌC HÓA ĐƠN XML & NHẬN BẢN CHỤP PHẦN XÁC NHẬN
// =========================================================================
function setupXmlControls() {
    const xmlDropZone = document.getElementById('xmlDropZone');
    const xmlFileInput = document.getElementById('xmlFileInput');
    const btnXmlStartBatch = document.getElementById('btnXmlStartBatch');
    const btnXmlPauseBatch = document.getElementById('btnXmlPauseBatch');
    const btnXmlClearQueue = document.getElementById('btnXmlClearQueue');
    const btnXmlExportExcel = document.getElementById('btnXmlExportExcel');
    const btnXmlDownloadZip = document.getElementById('btnXmlDownloadZip');
    const btnExportXmlHistoryExcel = document.getElementById('btnExportXmlHistoryExcel');
    const btnClearXmlHistory = document.getElementById('btnClearXmlHistory');

    bindHeadlessToggle('xmlHeadlessCheckbox', 'xmlHeadlessLabel');

    if (xmlDropZone && xmlFileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            xmlDropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                xmlDropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            xmlDropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                xmlDropZone.classList.remove('dragover');
            });
        });

        xmlDropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                handleXmlFilesUpload(files);
            }
        });

        xmlFileInput.addEventListener('change', () => {
            if (xmlFileInput.files.length > 0) {
                handleXmlFilesUpload(xmlFileInput.files);
            }
        });
    }

    if (btnXmlStartBatch) {
        btnXmlStartBatch.addEventListener('click', () => {
            if (xmlQueue.length === 0) {
                alert('Vui lòng tải ít nhất một tệp XML vào danh sách.');
                return;
            }
            startXmlBatchProcess();
        });
    }

    if (btnXmlPauseBatch) {
        btnXmlPauseBatch.addEventListener('click', () => {
            isXmlPaused = true;
            btnXmlPauseBatch.classList.add('hidden');
            if (btnXmlStartBatch) {
                btnXmlStartBatch.classList.remove('hidden');
                btnXmlStartBatch.innerHTML = `<i class="fa-solid fa-play"></i> Tiếp Tục Xác Thực XML`;
            }
            addXmlLog('Người dùng đã yêu cầu tạm dừng tiến trình tra cứu XML.', 'warning');
        });
    }

    if (btnXmlClearQueue) {
        btnXmlClearQueue.addEventListener('click', () => {
            if (isXmlBatchRunning) {
                alert('Vui lòng tạm dừng tiến trình trước khi xóa danh sách.');
                return;
            }
            if (confirm('Bạn có chắc chắn muốn xóa toàn bộ danh sách hóa đơn XML đang chờ?')) {
                xmlQueue = [];
                renderXmlQueueTable();
                updateXmlStats();
                addXmlLog('Đã dọn sạch hàng đợi hóa đơn XML.', 'info');
            }
        });
    }

    if (btnXmlExportExcel) {
        btnXmlExportExcel.addEventListener('click', () => {
            exportXmlExcel(xmlQueue);
        });
    }

    if (btnXmlDownloadZip) {
        btnXmlDownloadZip.addEventListener('click', () => {
            downloadXmlCertificatesZip(xmlQueue);
        });
    }

    if (btnExportXmlHistoryExcel) {
        btnExportXmlHistoryExcel.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/xml/history');
                const data = await res.json();
                exportXmlExcel(data.history || []);
            } catch (e) {
                alert('Lỗi xuất Excel lịch sử XML.');
            }
        });
    }

    if (btnClearXmlHistory) {
        btnClearXmlHistory.addEventListener('click', async () => {
            if (confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử xác thực XML không?')) {
                try {
                    await fetch('/api/xml/history', { method: 'DELETE' });
                    loadXmlHistory();
                    addXmlLog('Đã xóa toàn bộ lịch sử xác thực XML.', 'info');
                } catch (e) {
                    alert('Không thể xóa lịch sử XML.');
                }
            }
        });
    }
}

async function handleXmlFilesUpload(files) {
    const xmlUploadLoader = document.getElementById('xmlUploadLoader');
    const xmlFileInput = document.getElementById('xmlFileInput');
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    if (xmlUploadLoader) xmlUploadLoader.classList.remove('hidden');
    addXmlLog(`Đang tải lên và phân tích ${files.length} tệp hóa đơn XML...`, 'info');

    try {
        const response = await fetch('/api/xml/upload', {
            method: 'POST',
            body: formData
        });

        const res = await response.json();
        if (!response.ok || !res.success) {
            throw new Error(res.detail || 'Lỗi khi tải tệp XML.');
        }

        const newInvoices = res.invoices || [];
        newInvoices.forEach(inv => {
            xmlQueue.push(inv);
        });

        addXmlLog(`Bóc tách thành công ${newInvoices.length} hóa đơn XML. Tổng trong danh sách: ${xmlQueue.length}.`, 'success');
        renderXmlQueueTable();
        updateXmlStats();

    } catch (err) {
        addXmlLog(`Lỗi tải tệp XML: ${err.message}`, 'error');
        alert(`Lỗi: ${err.message}`);
    } finally {
        if (xmlUploadLoader) xmlUploadLoader.classList.add('hidden');
        if (xmlFileInput) xmlFileInput.value = '';
    }
}

function renderXmlQueueTable() {
    const xmlQueueTableBody = document.getElementById('xmlQueueTableBody');
    const xmlQueueCountBadge = document.getElementById('xmlQueueCountBadge');
    const xmlProgressContainer = document.getElementById('xmlProgressContainer');
    if (!xmlQueueTableBody) return;

    xmlQueueTableBody.innerHTML = '';
    if (xmlQueueCountBadge) xmlQueueCountBadge.textContent = `${xmlQueue.length} hóa đơn`;

    if (xmlQueue.length === 0) {
        xmlQueueTableBody.innerHTML = `
            <tr id="xmlEmptyQueueRow">
                <td colspan="11" class="py-10 text-center text-slate-400">
                    <i class="fa-solid fa-file-code text-3xl mb-2 block opacity-40"></i>
                    Chưa có hóa đơn XML nào trong danh sách. Hãy kéo thả hoặc chọn tệp .XML ở trên để bắt đầu tra cứu.
                </td>
            </tr>
        `;
        if (xmlProgressContainer) xmlProgressContainer.classList.add('hidden');
        return;
    }

    if (xmlProgressContainer) xmlProgressContainer.classList.remove('hidden');

    xmlQueue.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.id = `xml_row_${item.id}`;
        tr.className = `transition border-b border-slate-100 hover:bg-slate-50/80 ${getXmlRowStateClass(item.status, item.status_code)}`;

        const statusBadge = getXmlStatusBadgeHtml(item.status, item.status_code, item.message);

        const certUrl = item.confirmation_crop_url || item.screenshot_url;
        const screenshotBtn = certUrl
            ? `<button type="button" onclick="viewXmlActiveScreenshot('${item.id}')" class="text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1 mx-auto text-xs bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded-md transition border border-emerald-200">
                 <i class="fa-solid fa-certificate"></i> Bản chụp
               </button>`
            : `<span class="text-slate-300">-</span>`;

        tr.innerHTML = `
            <td class="py-2.5 px-3 text-center font-mono font-semibold text-slate-500">${index + 1}</td>
            <td class="py-2.5 px-3">
                <div class="font-medium text-slate-800 truncate max-w-[180px]" title="${escapeHtml(item.file_name || '')}">
                    <i class="fa-solid fa-file-code mr-1 text-emerald-600"></i>
                    ${escapeHtml(item.file_name || 'Hóa đơn XML')}
                </div>
            </td>
            <td class="py-2.5 px-3 font-mono font-bold text-slate-800">
                ${escapeHtml(item.mst_nguoi_ban || '-')}
            </td>
            <td class="py-2.5 px-3 font-medium text-slate-800 max-w-[170px] truncate" title="${escapeHtml(item.ten_nguoi_ban || '')}">
                ${escapeHtml(item.ten_nguoi_ban || '-')}
            </td>
            <td class="py-2.5 px-3 font-mono text-slate-700">
                ${escapeHtml(item.ky_hieu || '-')}
            </td>
            <td class="py-2.5 px-3 font-mono font-semibold text-slate-800">
                ${escapeHtml(item.so_hd || '-')}
            </td>
            <td class="py-2.5 px-3 text-right font-mono font-bold text-emerald-800">
                ${item.tong_tien ? formatCurrency(item.tong_tien) + ' đ' : '-'}
            </td>
            <td class="py-2.5 px-3 text-center font-mono text-slate-600">
                ${escapeHtml(item.ngay_lap || '-')}
            </td>
            <td class="py-2.5 px-3 text-center" id="xml_status_col_${item.id}">
                ${statusBadge}
            </td>
            <td class="py-2.5 px-3 text-center" id="xml_cert_col_${item.id}">
                ${screenshotBtn}
            </td>
            <td class="py-2.5 px-3 text-center">
                <div class="flex items-center justify-center gap-1.5">
                    <button type="button" onclick="runSingleXmlItem('${item.id}')" title="Tra cứu tệp XML này" class="p-1.5 rounded hover:bg-slate-200 text-slate-600 hover:text-emerald-700 transition">
                        <i class="fa-solid fa-play text-xs"></i>
                    </button>
                    <button type="button" onclick="removeXmlQueueItem('${item.id}')" title="Xóa khỏi danh sách" class="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600 transition">
                        <i class="fa-solid fa-trash text-xs"></i>
                    </button>
                </div>
            </td>
        `;
        xmlQueueTableBody.appendChild(tr);
    });
}
window.renderXmlQueueTable = renderXmlQueueTable;

function getXmlRowStateClass(status, statusCode) {
    if (status === 'running') return 'row-running';
    if (statusCode === 'VERIFIED' || statusCode === 'FOUND') return 'row-success';
    if (status === 'error' || statusCode === 'ERROR' || statusCode === 'NOT_FOUND') return 'row-error';
    return '';
}

function getXmlStatusBadgeHtml(status, statusCode, message) {
    if (status === 'running') {
        return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 animate-pulse">
                    <i class="fa-solid fa-spinner fa-spin"></i> Đang xác thực...
                </span>`;
    }
    if (statusCode === 'VERIFIED' || statusCode === 'FOUND') {
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800" title="${escapeHtml(message || 'Đã xác thực & Chữ ký số hợp lệ')}">
                    <i class="fa-solid fa-circle-check"></i> Hợp lệ (Ký đúng)
                </span>`;
    }
    if (status === 'error' || statusCode === 'ERROR') {
        return `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800" title="${escapeHtml(message || 'Lỗi tra cứu XML')}">
                    <i class="fa-solid fa-circle-xmark"></i> Lỗi
                </span>`;
    }
    return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                <i class="fa-regular fa-clock"></i> Chờ xử lý
            </span>`;
}

function updateXmlStats() {
    const xmlStatTotal = document.getElementById('xmlStatTotal');
    const xmlStatPending = document.getElementById('xmlStatPending');
    const xmlStatVerified = document.getElementById('xmlStatVerified');
    const xmlStatError = document.getElementById('xmlStatError');
    const xmlProgressBarFill = document.getElementById('xmlProgressBarFill');
    const xmlProgressText = document.getElementById('xmlProgressText');

    const total = xmlQueue.length;
    const pending = xmlQueue.filter(x => !x.status_code && x.status !== 'error').length;
    const verified = xmlQueue.filter(x => x.status_code === 'VERIFIED' || x.status_code === 'FOUND').length;
    const error = xmlQueue.filter(x => x.status === 'error' || x.status_code === 'ERROR').length;
    const completed = total - pending;

    if (xmlStatTotal) xmlStatTotal.textContent = `Tổng: ${total}`;
    if (xmlStatPending) xmlStatPending.textContent = `Chờ: ${pending}`;
    if (xmlStatVerified) xmlStatVerified.textContent = `Hợp lệ: ${verified}`;
    if (xmlStatError) xmlStatError.textContent = `Lỗi: ${error}`;

    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    if (xmlProgressBarFill) xmlProgressBarFill.style.width = `${pct}%`;
    if (xmlProgressText) {
        xmlProgressText.innerHTML = isXmlBatchRunning
            ? `<i class="fa-solid fa-spinner fa-spin text-emerald-600"></i> Đang xác thực: ${completed}/${total} hóa đơn XML (${pct}%)`
            : `<i class="fa-solid fa-check-double text-emerald-600"></i> Tiến độ: ${completed}/${total} hóa đơn XML (${pct}%)`;
    }
}

async function startXmlBatchProcess() {
    const btnXmlStartBatch = document.getElementById('btnXmlStartBatch');
    const btnXmlPauseBatch = document.getElementById('btnXmlPauseBatch');
    const xmlRpaStatusIndicator = document.getElementById('xmlRpaStatusIndicator');

    isXmlBatchRunning = true;
    isXmlPaused = false;
    if (btnXmlStartBatch) btnXmlStartBatch.classList.add('hidden');
    if (btnXmlPauseBatch) btnXmlPauseBatch.classList.remove('hidden');
    if (xmlRpaStatusIndicator) xmlRpaStatusIndicator.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Đang chạy RPA XML`;

    addXmlLog(`=== BẮT ĐẦU XÁC THỰC HÀNG LOẠT (${xmlQueue.length} HÓA ĐƠN XML) ===`, 'info');

    for (let i = 0; i < xmlQueue.length; i++) {
        if (isXmlPaused) {
            addXmlLog('Tiến trình xác thực XML đã tạm dừng. Nhấn Tiếp Tục để chạy tiếp.', 'warning');
            break;
        }

        const item = xmlQueue[i];
        if (item.status_code === 'VERIFIED') {
            continue;
        }

        await processXmlItem(item, i + 1, xmlQueue.length);
        updateXmlStats();

        if (i < xmlQueue.length - 1 && !isXmlPaused) {
            await new Promise(r => setTimeout(r, 2000));
        }
    }

    isXmlBatchRunning = false;
    if (btnXmlPauseBatch) btnXmlPauseBatch.classList.add('hidden');
    if (btnXmlStartBatch) {
        btnXmlStartBatch.classList.remove('hidden');
        btnXmlStartBatch.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Xác Thực Lại Toàn Bộ`;
    }
    if (xmlRpaStatusIndicator) xmlRpaStatusIndicator.innerHTML = `<span class="w-2 h-2 rounded-full bg-slate-500"></span> Chờ lệnh`;

    addXmlLog('=== HOÀN TẤT ĐỢT XÁC THỰC HÓA ĐƠN XML ===', 'success');
    loadXmlHistory();
}

async function runSingleXmlItem(itemId) {
    const item = xmlQueue.find(x => x.id === itemId);
    if (!item) return;
    const index = xmlQueue.indexOf(item) + 1;
    await processXmlItem(item, index, xmlQueue.length);
    updateXmlStats();
    loadXmlHistory();
}
window.runSingleXmlItem = runSingleXmlItem;

function removeXmlQueueItem(id) {
    xmlQueue = xmlQueue.filter(x => x.id !== id);
    renderXmlQueueTable();
    updateXmlStats();
}
window.removeXmlQueueItem = removeXmlQueueItem;

async function processXmlItem(item, currentIdx, totalCount) {
    const xmlHeadlessCheckbox = document.getElementById('xmlHeadlessCheckbox');
    item.status = 'running';
    renderXmlQueueTable();

    addXmlLog(`[${currentIdx}/${totalCount}] Đang nạp XML lên Cổng Thuế: ${item.file_name} (Ký hiệu: ${item.ky_hieu}, Số: ${item.so_hd})...`, 'info');

    const payload = {
        xml_path: item.xml_path,
        invoice_info: {
            mst_nguoi_ban: item.mst_nguoi_ban || '',
            ten_nguoi_ban: item.ten_nguoi_ban || '',
            ky_hieu: item.ky_hieu || '',
            so_hd: item.so_hd || '',
            ngay_lap: item.ngay_lap || '',
            tong_tien: item.tong_tien || '',
            loai_hd: item.loai_hd || 'Hóa đơn điện tử giá trị gia tăng'
        },
        headless: xmlHeadlessCheckbox ? xmlHeadlessCheckbox.checked : false
    };

    try {
        const response = await fetch('/api/xml/lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();

        if (res.logs && res.logs.length > 0) {
            res.logs.forEach(msg => addXmlLog(`  ↳ ${msg}`, 'console'));
        }

        item.status = res.success ? 'success' : 'error';
        item.status_code = res.status_code || (res.success ? 'VERIFIED' : 'ERROR');
        item.message = res.message || '';
        item.details = res.details || [];
        item.screenshot_url = res.screenshot_url || '';
        item.screenshot_filename = res.screenshot_filename || '';
        item.confirmation_crop_url = res.confirmation_crop_url || '';
        item.confirmation_crop_filename = res.confirmation_crop_filename || '';
        item.timestamp = res.timestamp || '';

        if (res.success) {
            addXmlLog(`[${currentIdx}/${totalCount}] ✅ KẾT QUẢ: HÓA ĐƠN XML HỢP LỆ & ĐÃ XÁC THỰC! (${item.file_name})`, 'success');
        } else {
            addXmlLog(`[${currentIdx}/${totalCount}] ⚠️ KẾT QUẢ: ${res.message || 'Lỗi xác thực'}`, 'warning');
        }

        viewXmlActiveScreenshot(item.id);

    } catch (err) {
        item.status = 'error';
        item.message = err.message;
        addXmlLog(`[${currentIdx}/${totalCount}] Lỗi mạng khi tra cứu XML: ${err.message}`, 'error');
    }

    renderXmlQueueTable();
}

function viewXmlActiveScreenshot(itemId) {
    const item = xmlQueue.find(x => x.id === itemId) || (window._lastXmlHistory && window._lastXmlHistory.find(x => x.id === itemId));
    if (!item) return;
    currentActiveXmlId = itemId;

    const imgToDisplay = activeXmlPreviewMode === 'crop'
        ? (item.confirmation_crop_url || item.screenshot_url)
        : (item.screenshot_url || item.confirmation_crop_url);

    if (!imgToDisplay) return;

    const placeholder = document.getElementById('xmlActiveScreenshotPlaceholder');
    const img = document.getElementById('xmlActiveScreenshotImg');
    const overlay = document.getElementById('xmlActiveScreenshotOverlay');
    const btnDownload = document.getElementById('btnDownloadXmlActiveScreenshot');
    const badge = document.getElementById('xmlActiveResultBadge');
    const details = document.getElementById('xmlActiveResultDetails');
    const title = document.getElementById('xmlActiveResultTitle');
    const sub = document.getElementById('xmlActiveResultSub');

    if (placeholder) placeholder.classList.add('hidden');
    if (img) {
        img.src = imgToDisplay;
        img.classList.remove('hidden');
    }
    if (overlay) overlay.classList.remove('hidden');
    if (btnDownload) btnDownload.href = imgToDisplay;

    if (badge) {
        badge.classList.remove('hidden');
        if (item.status_code === 'VERIFIED' || item.status_code === 'FOUND' || item.success) {
            badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800';
            badge.textContent = 'HỢP LỆ (CHỮ KÝ ĐÚNG)';
        } else {
            badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800';
            badge.textContent = 'LỖI / KHÔNG HỢP LỆ';
        }
    }

    if (details) details.classList.remove('hidden');
    if (title) title.textContent = `${item.file_name || 'Hóa đơn XML'} - Số: ${item.so_hd || ''} (Ký hiệu: ${item.ky_hieu || ''})`;
    if (sub) sub.textContent = item.message || (item.details ? item.details.join(' | ') : '');
}
window.viewXmlActiveScreenshot = viewXmlActiveScreenshot;

function switchXmlPreview(mode) {
    activeXmlPreviewMode = mode;
    const btnViewCrop = document.getElementById('btnViewCrop');
    const btnViewFull = document.getElementById('btnViewFull');

    if (btnViewCrop && btnViewFull) {
        if (mode === 'crop') {
            btnViewCrop.className = 'px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white shadow-xs';
            btnViewFull.className = 'px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100';
        } else {
            btnViewFull.className = 'px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white shadow-xs';
            btnViewCrop.className = 'px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100';
        }
    }

    if (currentActiveXmlId) {
        viewXmlActiveScreenshot(currentActiveXmlId);
    }
}
window.switchXmlPreview = switchXmlPreview;

async function exportXmlExcel(invoices) {
    if (!invoices || invoices.length === 0) {
        alert('Không có dữ liệu hóa đơn XML để xuất Excel.');
        return;
    }

    addXmlLog('Đang khởi tạo tệp Excel báo cáo đối soát hóa đơn XML...', 'info');
    try {
        const response = await fetch('/api/xml/export-excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ invoices: invoices })
        });

        if (!response.ok) throw new Error('Lỗi xuất tệp Excel XML.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BangKe_XacThuc_HoaDon_XML_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        addXmlLog('Đã tải về tệp Báo cáo đối soát XML thành công!', 'success');
    } catch (e) {
        addXmlLog(`Lỗi xuất Excel XML: ${e.message}`, 'error');
        alert(`Lỗi xuất Excel XML: ${e.message}`);
    }
}

async function downloadXmlCertificatesZip(invoices) {
    const urls = invoices.map(x => x.confirmation_crop_url || x.screenshot_url).filter(Boolean);
    if (urls.length === 0) {
        alert('Chưa có bản chụp xác nhận nào để tải về.');
        return;
    }

    addXmlLog(`Đang đóng gói ${urls.length} bản chụp xác nhận vào tệp .zip...`, 'info');
    try {
        const response = await fetch('/api/xml/download-batch-certificates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ certificates: urls, images: urls })
        });

        if (!response.ok) throw new Error('Lỗi đóng gói tệp ZIP bản chụp.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BanChup_XacNhan_XML_${new Date().toISOString().slice(0, 10)}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        addXmlLog('Đã tải về gói Bản chụp xác nhận XML (.zip) thành công!', 'success');
    } catch (e) {
        addXmlLog(`Lỗi tải ZIP: ${e.message}`, 'error');
        alert(`Lỗi tải ZIP: ${e.message}`);
    }
}

async function loadXmlHistory() {
    const xmlHistoryTableBody = document.getElementById('xmlHistoryTableBody');
    if (!xmlHistoryTableBody) return;

    try {
        const res = await fetch('/api/xml/history');
        const data = await res.json();
        const history = data.history || [];
        window._lastXmlHistory = history;

        if (history.length === 0) {
            xmlHistoryTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="py-6 text-center text-slate-400">Chưa có lịch sử xác thực XML nào được lưu.</td>
                </tr>
            `;
            return;
        }

        xmlHistoryTableBody.innerHTML = '';
        history.forEach(item => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition';

            const statusBadge = item.success || item.status_code === 'VERIFIED'
                ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                     <i class="fa-solid fa-check"></i> Hợp lệ
                   </span>`
                : `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                     <i class="fa-solid fa-xmark"></i> Lỗi
                   </span>`;

            const previewUrl = item.confirmation_crop_url || item.screenshot_url;
            const screenshotLink = previewUrl
                ? `<button onclick="openLightbox('${previewUrl}')" class="text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1 ml-auto">
                     <i class="fa-solid fa-certificate"></i> Xem ảnh
                   </button>`
                : `<span class="text-slate-300">-</span>`;

            tr.innerHTML = `
                <td class="py-2 px-3 font-mono text-slate-500">${item.timestamp || '-'}</td>
                <td class="py-2 px-3 font-medium text-slate-800 max-w-[150px] truncate" title="${escapeHtml(item.file_name || '')}">${escapeHtml(item.file_name || '-')}</td>
                <td class="py-2 px-3 font-mono font-bold text-slate-800">${escapeHtml(item.mst_nguoi_ban || '-')}</td>
                <td class="py-2 px-3 font-mono text-slate-700">${escapeHtml(item.ky_hieu || '-')}</td>
                <td class="py-2 px-3 font-mono font-semibold text-slate-800">${escapeHtml(item.so_hd || '-')}</td>
                <td class="py-2 px-3 font-mono text-emerald-800 font-bold">${item.tong_tien ? formatCurrency(item.tong_tien) + ' đ' : '-'}</td>
                <td class="py-2 px-3">${statusBadge}</td>
                <td class="py-2 px-3 text-right">${screenshotLink}</td>
            `;
            xmlHistoryTableBody.appendChild(tr);
        });
    } catch (e) {
        console.error('Lỗi nạp lịch sử XML:', e);
    }
}

function addXmlLog(message, type = 'info') {
    const xmlLogConsole = document.getElementById('xmlLogConsole');
    if (!xmlLogConsole) return;
    const p = document.createElement('p');
    const time = new Date().toLocaleTimeString('vi-VN');
    p.className = 'leading-relaxed';

    let colorClass = 'text-slate-300';
    if (type === 'success') colorClass = 'text-emerald-400 font-semibold';
    else if (type === 'error') colorClass = 'text-rose-400 font-semibold';
    else if (type === 'warning') colorClass = 'text-amber-400';
    else if (type === 'console') colorClass = 'text-slate-400 text-[11px] pl-2';

    p.innerHTML = `<span class="text-slate-500 font-mono text-[11px]">[${time}]</span> <span class="${colorClass}">${escapeHtml(message)}</span>`;
    xmlLogConsole.appendChild(p);
    xmlLogConsole.scrollTop = xmlLogConsole.scrollHeight;
}

// =========================================================================
// GENERAL HELPERS & LIGHTBOX
// =========================================================================
function formatCurrency(num) {
    if (!num) return '';
    const clean = String(num).replace(/[^\d]/g, '');
    if (!clean) return num;
    return Number(clean).toLocaleString('vi-VN');
}

function addLog(message, type = 'info') {
    const logConsole = document.getElementById('logConsole');
    if (!logConsole) return;
    const p = document.createElement('p');
    const time = new Date().toLocaleTimeString('vi-VN');
    p.className = 'leading-relaxed';

    let colorClass = 'text-slate-300';
    if (type === 'success') colorClass = 'text-emerald-400 font-semibold';
    else if (type === 'error') colorClass = 'text-rose-400 font-semibold';
    else if (type === 'warning') colorClass = 'text-amber-400';
    else if (type === 'console') colorClass = 'text-slate-400 text-[11px] pl-2';

    p.innerHTML = `<span class="text-slate-500 font-mono text-[11px]">[${time}]</span> <span class="${colorClass}">${escapeHtml(message)}</span>`;
    logConsole.appendChild(p);
    logConsole.scrollTop = logConsole.scrollHeight;
}

function addNntLog(message, type = 'info') {
    const nntLogConsole = document.getElementById('nntLogConsole');
    if (!nntLogConsole) return;
    const p = document.createElement('p');
    const time = new Date().toLocaleTimeString('vi-VN');
    p.className = 'leading-relaxed';

    let colorClass = 'text-slate-300';
    if (type === 'success') colorClass = 'text-emerald-400 font-semibold';
    else if (type === 'error') colorClass = 'text-rose-400 font-semibold';
    else if (type === 'warning') colorClass = 'text-amber-400';
    else if (type === 'console') colorClass = 'text-slate-400 text-[11px] pl-2';

    p.innerHTML = `<span class="text-slate-500 font-mono text-[11px]">[${time}]</span> <span class="${colorClass}">${escapeHtml(message)}</span>`;
    nntLogConsole.appendChild(p);
    nntLogConsole.scrollTop = nntLogConsole.scrollHeight;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openLightbox(imgSrc) {
    if (!imgSrc) return;
    const lightboxModal = document.getElementById('lightboxModal');
    const lightboxImg = document.getElementById('lightboxImg');
    if (lightboxImg) lightboxImg.src = imgSrc;
    if (lightboxModal) lightboxModal.classList.remove('hidden');
}
window.openLightbox = openLightbox;

function closeLightbox() {
    const lightboxModal = document.getElementById('lightboxModal');
    const lightboxImg = document.getElementById('lightboxImg');
    if (lightboxModal) lightboxModal.classList.add('hidden');
    if (lightboxImg) lightboxImg.src = '';
}
window.closeLightbox = closeLightbox;
