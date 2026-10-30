document.addEventListener('DOMContentLoaded', () => {
  let uploadedFiles = [];
  let calculatedPageCount = 0;

  const pdfInput = document.getElementById('pdfFile');
  const dropZone = document.getElementById('dropZone');
  const fileMetaList = document.getElementById('fileMetaList');
  const totalPageNum = document.getElementById('totalPageNum');
  const toStep2Btn = document.getElementById('toStep2');
  const largeFileNotice = document.getElementById('largeFileNotice');

  // Input change event
  if (pdfInput) {
    pdfInput.addEventListener('change', (e) => {
      handleFiles(e.target.files);
    });
  }

  // Drag & Drop
  if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        handleFiles(e.dataTransfer.files);
      }
    });
  }

  function handleFiles(files) {
    let hasOver100MB = false;
    
    Array.from(files).forEach(file => {
      if (file.size > 100 * 1024 * 1024) {
        hasOver100MB = true;
      } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
        uploadedFiles.push(file);
      }
    });

    if (hasOver100MB && largeFileNotice) {
      largeFileNotice.classList.remove('hidden');
    } else if (largeFileNotice) {
      largeFileNotice.classList.add('hidden');
    }

    renderFileList();
    calculateTotalPagesAndBill();
  }

  function renderFileList() {
    if (!fileMetaList) return;
    fileMetaList.innerHTML = '';
    
    if (uploadedFiles.length === 0) {
      if (toStep2Btn) toStep2Btn.disabled = true;
      return;
    }
    if (toStep2Btn) toStep2Btn.disabled = false;

    uploadedFiles.forEach((file, index) => {
      const item = document.createElement('div');
      item.className = 'flex items-center justify-between rounded-xl bg-paper p-3.5 border border-slate-200 text-sm';
      item.innerHTML = `
        <div class="flex items-center gap-3">
          <i data-lucide="file-text" class="h-5 w-5 text-royalBlue"></i>
          <div>
            <strong class="block text-navy font-bold">${file.name}</strong>
            <span class="text-xs text-slate-500">${(file.size / (1024 * 1024)).toFixed(2)} MB</span>
          </div>
        </div>
        <button type="button" onclick="removeFile(${index})" class="text-slate-400 hover:text-red-500 p-1">
          <i data-lucide="x" class="h-4 w-4"></i>
        </button>
      `;
      fileMetaList.appendChild(item);
    });
    if (window.lucide) lucide.createIcons();
  }

  window.removeFile = (index) => {
    uploadedFiles.splice(index, 1);
    renderFileList();
    calculateTotalPagesAndBill();
  };

  async function calculateTotalPagesAndBill() {
    if (uploadedFiles.length === 0) {
      calculatedPageCount = 0;
      if (totalPageNum) totalPageNum.innerText = '0';
      updateBill(0);
      return;
    }

    // Estimate total pages dynamically across all uploaded files
    let estimatedPages = 0;
    uploadedFiles.forEach(f => {
      estimatedPages += Math.max(1, Math.round(f.size / (80 * 1024)));
    });

    calculatedPageCount = estimatedPages;
    if (totalPageNum) totalPageNum.innerText = calculatedPageCount;
    updateBill(calculatedPageCount);
  }

  function updateBill(pages) {
    const billPages = document.getElementById('billPages');
    const billPrint = document.getElementById('billPrint');
    const billBinding = document.getElementById('billBinding');
    const billDelivery = document.getElementById('billDelivery');
    const billTotal = document.getElementById('billTotal');

    if (pages === 0) {
      if (billPages) billPages.innerText = '0 pages';
      if (billPrint) billPrint.innerText = '৳ 0.00';
      if (billBinding) billBinding.innerText = '৳ 0.00';
      if (billDelivery) billDelivery.innerText = '৳ 0.00';
      if (billTotal) billTotal.innerText = '৳ 0.00';
      return;
    }

    // Rate rules
    const printRate = 1.50; // Default B&W 80GSM Single Side
    const printCost = pages * printRate;
    const deliveryCost = 60.00; // Default Dhaka

    if (billPages) billPages.innerText = `${pages} pages`;
    if (billPrint) billPrint.innerText = `৳ ${printCost.toFixed(2)}`;
    if (billDelivery) billDelivery.innerText = `৳ ${deliveryCost.toFixed(2)}`;
    if (billTotal) billTotal.innerText = `৳ ${(printCost + deliveryCost).toFixed(2)}`;
  }

  // Wizard Step Navigation
  const steps = document.querySelectorAll('.step-panel');
  const progressSteps = document.querySelectorAll('.progress-step');

  window.goToStep = (stepNumber) => {
    steps.forEach(s => s.classList.add('hidden'));
    const target = document.querySelector(`.step-panel[data-panel="${stepNumber}"]`);
    if (target) target.classList.remove('hidden');

    progressSteps.forEach(p => {
      const pStep = parseInt(p.dataset.step);
      if (pStep <= stepNumber) {
        p.classList.add('bg-navy', 'text-white');
        p.classList.remove('bg-white', 'text-slate-400');
      } else {
        p.classList.remove('bg-navy', 'text-white');
        p.classList.add('bg-white', 'text-slate-400');
      }
    });

    const stepCounter = document.getElementById('stepCounter');
    if (stepCounter) stepCounter.innerText = `Step ${stepNumber} of 4`;
  };

  if (toStep2Btn) toStep2Btn.addEventListener('click', () => goToStep(2));
  
  document.querySelectorAll('.next-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const currentPanel = e.target.closest('.step-panel').dataset.panel;
      goToStep(parseInt(currentPanel) + 1);
    });
  });

  document.querySelectorAll('.back-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const currentPanel = e.target.closest('.step-panel').dataset.panel;
      goToStep(parseInt(currentPanel) - 1);
    });
  });
});