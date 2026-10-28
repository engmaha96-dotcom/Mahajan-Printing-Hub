let currentStep = 1;
let currentSessionId = '';
let calculatedTotal = 60;
let selectedFile = null;
let latestCalculation = null;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function money(value) {
  return `৳ ${Number(value || 0).toFixed(2)}`;
}

function showError(message) {
  const error = $('#orderError');
  error.textContent = message;
  error.classList.remove('hidden');
}

function clearError() {
  $('#orderError').classList.add('hidden');
  $('#orderError').textContent = '';
}

function setStep(step) {
  currentStep = step;
  $$('.step-panel').forEach((panel) => panel.classList.toggle('hidden', Number(panel.dataset.panel) !== step));
  $$('.progress-step').forEach((item) => {
    const itemStep = Number(item.dataset.step);
    item.classList.toggle('bg-navy', itemStep === step || itemStep < step);
    item.classList.toggle('text-white', itemStep === step || itemStep < step);
    item.classList.toggle('bg-white', itemStep > step);
    item.classList.toggle('text-slate-400', itemStep > step);
  });
  $('#stepCounter').textContent = `Step ${step} of 4`;
  clearError();
  window.scrollTo({ top: document.querySelector('#order').offsetTop - 20, behavior: 'smooth' });
  if (step === 4) renderReview();
}

function selectedValue(name) {
  return document.querySelector(`input[name="${name}"]:checked`)?.value || '';
}

function updateBill(data = latestCalculation) {
  const pages = data?.page_count ? `${data.page_count} pages · ${data.total_sheets} sheets` : '—';
  $('#billPages').textContent = pages;
  $('#billPrint').textContent = money(data?.print_cost);
  $('#billBinding').textContent = money(data?.binding_cost);
  $('#billDelivery').textContent = money(data?.delivery_cost ?? 60);
  calculatedTotal = Number(data?.grand_total ?? 60);
  $('#billTotal').textContent = money(calculatedTotal);
}

async function calculateBill() {
  if (!selectedFile) return false;
  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('paper_size', selectedValue('paper_size'));
  formData.append('gsm', $('#gsm').value);
  formData.append('color_type', selectedValue('color_type'));
  formData.append('print_side', selectedValue('print_side'));
  formData.append('binding', $('#binding').value);
  formData.append('delivery_option', $('#deliveryOption').value);

  try {
    const response = await fetch('/api/calculate', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'PDF প্রসেস করা যায়নি।');
    currentSessionId = data.session_id;
    latestCalculation = data;
    updateBill(data);
    $('#toStep2').disabled = false;
    clearError();
    return true;
  } catch (error) {
    showError(error.message);
    $('#toStep2').disabled = true;
    return false;
  }
}

function displayFile(file) {
  selectedFile = file;
  $('#fileMeta').classList.remove('hidden');
  $('#fileMeta').classList.add('flex');
  $('#fileName').textContent = file.name;
  $('#fileSize').textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
  if (file.size > 50 * 1024 * 1024) {
    $('#largeFileNotice').classList.remove('hidden');
    $('#toStep2').disabled = true;
    showError('এই ফাইলটি ৫০ MB-এর বেশি। WhatsApp support ব্যবহার করুন।');
    return;
  }
  $('#largeFileNotice').classList.add('hidden');
  calculateBill();
}

function renderReview() {
  const detail = latestCalculation || {};
  const labels = {
    paper: `${selectedValue('paper_size')} · ${$('#gsm').value} GSM`,
    print: `${selectedValue('color_type') === 'color' ? 'Color' : 'B&W'} · ${selectedValue('print_side') === 'double' ? 'Both sides' : 'Single-sided'}`,
    binding: $('#binding').selectedOptions[0].textContent,
    delivery: $('#deliveryOption').selectedOptions[0].textContent,
  };
  $('#reviewSummary').innerHTML = `
    <div class="flex justify-between gap-4"><span class="text-slate-500">File</span><strong class="max-w-[65%] truncate text-right text-navy">${selectedFile?.name || 'PDF'}</strong></div>
    <div class="flex justify-between gap-4"><span class="text-slate-500">Paper</span><strong class="text-right text-navy">${labels.paper}</strong></div>
    <div class="flex justify-between gap-4"><span class="text-slate-500">Print</span><strong class="text-right text-navy">${labels.print}</strong></div>
    <div class="flex justify-between gap-4"><span class="text-slate-500">Binding</span><strong class="text-right text-navy">${labels.binding}</strong></div>
    <div class="flex justify-between gap-4"><span class="text-slate-500">Delivery</span><strong class="text-right text-navy">${labels.delivery}</strong></div>
    <div class="mt-2 flex justify-between gap-4 border-t border-slate-200 pt-3"><span class="font-extrabold text-navy">Total</span><strong class="text-lg text-gold">${money(detail.grand_total ?? calculatedTotal)}</strong></div>`;
}

async function submitOrder(event) {
  event.preventDefault();
  clearError();
  const paymentMethod = $('#paymentMethod').value;
  const trxId = $('#trxId').value.trim();
  if (paymentMethod !== 'cod' && !trxId) {
    showError('ডিজিটাল পেমেন্টের জন্য Transaction ID দিন।');
    return;
  }
  if (!$('#customerName').value.trim() || !$('#customerPhone').value.trim() || !$('#address').value.trim()) {
    showError('নাম, ফোন নম্বর এবং বিস্তারিত ঠিকানা পূরণ করুন।');
    setStep(3);
    return;
  }
  const formData = new FormData();
  formData.append('session_id', currentSessionId);
  formData.append('customer_name', $('#customerName').value);
  formData.append('customer_phone', $('#customerPhone').value);
  formData.append('address', $('#address').value);
  formData.append('area', $('#area').value);
  formData.append('instructions', $('#instructions').value);
  formData.append('payment_method', paymentMethod);
  formData.append('trx_id', trxId);
  formData.append('amount', calculatedTotal);
  const button = $('#submitOrder');
  button.disabled = true;
  button.innerHTML = '<i data-lucide="loader-circle" class="h-4 w-4 animate-spin"></i> Sending...';
  lucide.createIcons();
  try {
    const response = await fetch('/api/checkout', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'অর্ডার সেভ করা যায়নি।');
    $('#orderForm').classList.add('hidden');
    $('#receipt').classList.remove('hidden');
    $('#receiptOrderId').textContent = data.order_id;
    $('#receiptMessage').textContent = data.message;
    window.scrollTo({ top: $('#receipt').offsetTop - 20, behavior: 'smooth' });
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = '<i data-lucide="check-circle-2" class="h-4 w-4"></i> Confirm order';
    lucide.createIcons();
  }
}

async function trackOrder(event) {
  event.preventDefault();
  const orderId = $('#trackId').value.trim();
  if (!orderId) return;
  const result = $('#trackResult');
  result.classList.remove('hidden');
  result.innerHTML = '<p class="text-sm font-semibold text-slate-500">Checking your order...</p>';
  try {
    const response = await fetch(`/api/track/${encodeURIComponent(orderId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Order not found.');
    result.innerHTML = `<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><span class="text-xs font-extrabold uppercase tracking-[.12em] text-teal">Order ${data.order_id}</span><h3 class="mt-1 text-xl font-extrabold text-navy">${data.customer_name || 'Customer'} · ${data.status_code.replace('_', ' ')}</h3><p class="mt-1 text-sm text-slate-500">Placed ${data.timestamp} · Total ${money(data.amount)}</p></div><span class="inline-flex w-fit items-center gap-2 rounded-full bg-teal/10 px-3 py-2 text-sm font-extrabold capitalize text-teal"><span class="h-2 w-2 rounded-full bg-teal"></span>${data.status_code.replace('_', ' ')}</span></div>`;
  } catch (error) {
    result.innerHTML = `<p class="text-sm font-semibold text-red-600">${error.message}</p>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  const fileInput = $('#pdfFile');
  const dropZone = $('#dropZone');
  $('#startUpload').addEventListener('click', () => {
    window.setTimeout(() => fileInput.click(), 120);
  });
  fileInput.addEventListener('change', (event) => event.target.files[0] && displayFile(event.target.files[0]));
  ['dragenter', 'dragover'].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.remove('dragover'); }));
  dropZone.addEventListener('drop', (event) => event.dataTransfer.files[0] && displayFile(event.dataTransfer.files[0]));
  $('#removeFile').addEventListener('click', () => { selectedFile = null; currentSessionId = ''; latestCalculation = null; fileInput.value = ''; $('#fileMeta').classList.add('hidden'); $('#fileMeta').classList.remove('flex'); $('#toStep2').disabled = true; updateBill(null); });
  $('#toStep2').addEventListener('click', () => setStep(2));
  $$('.next-btn').forEach((button) => button.addEventListener('click', async () => {
    if (currentStep === 2 && !(await calculateBill())) return;
    if (currentStep === 3 && (!$('#customerName').value.trim() || !$('#customerPhone').value.trim() || !$('#address').value.trim())) { showError('নাম, ফোন নম্বর এবং বিস্তারিত ঠিকানা পূরণ করুন।'); return; }
    setStep(currentStep + 1);
  }));
  $$('.back-btn').forEach((button) => button.addEventListener('click', () => setStep(currentStep - 1)));
  $$('#gsm, #binding, #deliveryOption').forEach((control) => control.addEventListener('change', async () => { await calculateBill(); updateBill(latestCalculation); }));
  $$('input[name="paper_size"], input[name="color_type"], input[name="print_side"]').forEach((control) => control.addEventListener('change', calculateBill));
  $('#orderForm').addEventListener('submit', submitOrder);
  $('#paymentMethod').addEventListener('change', (event) => { $('#paymentHint').textContent = event.target.value === 'cod' ? 'Cash on delivery selected. TrxID is not required.' : 'For digital payment, enter the TrxID so we can match your payment quickly.'; });
  $('#trackForm').addEventListener('submit', trackOrder);
  $('#newOrder').addEventListener('click', () => window.location.reload());
  updateBill(null);
});
