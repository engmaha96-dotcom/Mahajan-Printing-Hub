document.addEventListener('DOMContentLoaded', () => {
  let uploadedFiles = [];

  const pdfInput = document.getElementById('pdfFile');
  const dropZone = document.getElementById('dropZone');
  const fileMetaList = document.getElementById('fileMetaList');
  const totalPageNum = document.getElementById('totalPageNum');
  const toStep2Btn = document.getElementById('toStep2');
  const largeFileNotice = document.getElementById('largeFileNotice');
  const orderForm = document.getElementById('orderForm');
  const orderError = document.getElementById('orderError');

  // Multi-file Input Handling
  if (pdfInput) {
    pdfInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files);
        pdfInput.value = '';
      }
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
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    });
  }

  function handleFiles(files) {
    let hasOver100MB = false;
    
    Array.from(files).forEach(file => {
      if (file.size > 100 * 1024 * 1024) {
        hasOver100MB = true;
      } else {
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
      item.className = 'flex items-center justify-between rounded-xl bg-slate-50 p-3.5 border border-slate-200 text-sm mb-2';
      item.innerHTML = `
        <div class="flex items-center gap-3">
          <span class="grid h-8 w-8 place-items-center rounded-lg bg-blue-100 text-royalBlue font-bold text-xs">PDF</span>
          <div>
            <strong class="block text-navy font-bold">${file.name}</strong>
            <span class="text-xs text-slate-500">${(file.size / (1024 * 1024)).toFixed(2)} MB</span>
          </div>
        </div>
        <button type="button" onclick="window.removeFile(${index})" class="text-slate-400 hover:text-red-500 p-1 font-bold text-lg">
          ✕
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

  function calculateTotalPagesAndBill() {
    if (uploadedFiles.length === 0) {
      if (totalPageNum) totalPageNum.innerText = '0';
      updateBill(0);
      return;
    }

    let estimatedPages = 0;
    uploadedFiles.forEach(f => {
      estimatedPages += Math.max(1, Math.round(f.size / (80 * 1024)));
    });

    if (totalPageNum) totalPageNum.innerText = estimatedPages;
    updateBill(estimatedPages);
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

    const printRate = 1.50;
    const printCost = pages * printRate;
    const deliveryCost = 60.00;

    if (billPages) billPages.innerText = `${pages} pages`;
    if (billPrint) billPrint.innerText = `৳ ${printCost.toFixed(2)}`;
    if (billDelivery) billDelivery.innerText = `৳ ${deliveryCost.toFixed(2)}`;
    if (billTotal) billTotal.innerText = `৳ ${(printCost + deliveryCost).toFixed(2)}`;
  }

  // Step Navigation
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

  // Form Submission Logic
  if (orderForm) {
    orderForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (orderError) orderError.classList.add('hidden');

      if (uploadedFiles.length === 0) {
        if (orderError) {
          orderError.innerText = 'Please upload at least one PDF file.';
          orderError.classList.remove('hidden');
        }
        goToStep(1);
        return;
      }

      const submitBtn = document.getElementById('submitOrder');
      if (submitBtn) submitBtn.disabled = true;

      const formData = new FormData();
      uploadedFiles.forEach(file => {
        formData.append('files', file);
      });

      formData.append('customer_name', document.getElementById('customerName').value);
      formData.append('customer_phone', document.getElementById('customerPhone').value);
      formData.append('address', document.getElementById('address').value);
      formData.append('paper_size', document.querySelector('input[name="paper_size"]:checked').value);
      formData.append('gsm', document.getElementById('gsm').value);
      formData.append('color_type', document.querySelector('input[name="color_type"]:checked').value);
      formData.append('print_side', document.querySelector('input[name="print_side"]:checked').value);
      formData.append('binding', document.getElementById('binding').value);
      formData.append('delivery_option', document.getElementById('deliveryOption').value);
      formData.append('payment_method', document.getElementById('paymentMethod').value);
      formData.append('trx_id', document.getElementById('trxId').value);

      try {
        const response = await fetch('/api/order', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
          orderForm.classList.add('hidden');
          const receipt = document.getElementById('receipt');
          if (receipt) {
            document.getElementById('receiptOrderId').innerText = data.order_id;
            document.getElementById('receiptMessage').innerText = `Thank you, ${data.customer_name}. Your order has been placed.`;
            receipt.classList.remove('hidden');
          }
        } else {
          throw new Error(data.detail || 'Failed to submit order');
        }
      } catch (err) {
        if (orderError) {
          orderError.innerText = err.message || 'Error submitting order. Please try again.';
          orderError.classList.remove('hidden');
        }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // New Order Reset
  const newOrderBtn = document.getElementById('newOrder');
  if (newOrderBtn) {
    newOrderBtn.addEventListener('click', () => {
      window.location.reload();
    });
  }
});