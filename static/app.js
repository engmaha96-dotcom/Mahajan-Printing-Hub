let currentSessionId = "";
let calculatedGrandTotal = 0;

async function calculateBill() {
    const fileInput = document.getElementById('pdfFile');
    if (!fileInput || !fileInput.files[0]) return;

    // HTML এর সঠিক ID থেকে ভ্যালু সংগ্রহ
    const paperSize = document.getElementById('paperSize')?.value || 'A4';
    const gsm = parseInt(document.getElementById('gsm')?.value || 80);
    const colorType = document.getElementById('colorType')?.value || 'bw';
    const printSide = document.getElementById('printSide')?.value || 'single';
    const binding = document.getElementById('binding')?.value || 'none';
    const lamination = document.getElementById('lamination')?.checked ? 'true' : 'false';
    const delivery = document.getElementById('deliveryOption')?.value || 'regular_dhaka';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('paper_size', paperSize);
    formData.append('gsm', gsm);
    formData.append('color_type', colorType);
    formData.append('print_side', printSide);
    formData.append('binding', binding);
    formData.append('lamination', lamination);
    formData.append('delivery_option', delivery);

    try {
        const response = await fetch('/api/calculate', { method: 'POST', body: formData });
        if (!response.ok) {
            const err = await response.json();
            alert("এরর: " + (err.detail || "ফাইল প্রসেস করা যায়নি"));
            return;
        }

        const data = await response.json();
        if (data.status === "success") {
            currentSessionId = data.session_id;
            calculatedGrandTotal = data.grand_total;

            // index.html-এর সঠিক ID গুলোতে ডেটা সেট করা
            document.getElementById('resPages').innerText = data.page_count;
            document.getElementById('resPrint').innerText = data.print_cost;
            document.getElementById('resBinding').innerText = data.binding_cost;
            document.getElementById('resLamination').innerText = data.lamination_cost;
            document.getElementById('resDelivery').innerText = data.delivery_cost;
            document.getElementById('resTotal').innerText = data.grand_total;

            // সামারি এবং পেমেন্ট সেকশন শো (Display) করা
            document.getElementById('summaryBox').style.display = 'block';
            document.getElementById('checkoutSection').style.display = 'block';
        }
    } catch (error) {
        console.error("Error calculating bill:", error);
    }
}

// index.html-এ থাকা submitOrder() ফাংশন
async function submitOrder() {
    if (!currentSessionId) {
        alert("প্রথমে একটি PDF ফাইল আপলোড করুন!");
        return;
    }

    const custName = document.getElementById("custName")?.value;
    const custPhone = document.getElementById("custPhone")?.value;
    const custAddress = document.getElementById("custAddress")?.value;

    if (!custName || !custPhone || !custAddress) {
        alert("অনুগ্রহ করে আপনার নাম, মোবাইল নম্বর এবং ঠিকানা পূরণ করুন!");
        return;
    }

    const formData = new FormData();
    formData.append("session_id", currentSessionId);
    formData.append("customer_name", custName);
    formData.append("customer_phone", custPhone);
    formData.append("address", custAddress);
    formData.append("payment_method", document.getElementById("payMethod")?.value || "bkash");
    formData.append("trx_id", document.getElementById("trxId")?.value || "");
    formData.append("amount", calculatedGrandTotal);

    try {
        const response = await fetch("/api/checkout", { method: "POST", body: formData });
        const result = await response.json();
        if (result.status === "success") {
            // রিসিট দেখান এবং ফর্ম হাইড করুন
            document.getElementById('calcForm').style.display = 'none';
            document.getElementById('summaryBox').style.display = 'none';
            document.getElementById('checkoutSection').style.display = 'none';
            
            document.getElementById('outOrderId').innerText = result.order_id;
            document.getElementById('outMsg').innerText = result.message;
            document.getElementById('confirmationReceipt').style.display = 'block';
        } else {
            alert("অর্ডার সেভ করতে সমস্যা হয়েছে!");
        }
    } catch (error) {
        alert("নেটওয়ার্ক সমস্যা! অর্ডার কনফার্ম করা যায়নি।");
    }
}

// পেজ লোড হলে ইভেন্ট লিসেনার যুক্ত করা
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('pdfFile');
    if (fileInput) {
        fileInput.addEventListener('change', calculateBill);
    }
    
    // যেকোনো অপশন চেঞ্জ করলে অটোমেটিক হিসাব আপডেট হওয়া
    const inputs = document.querySelectorAll('select, input[type="checkbox"]');
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            if (fileInput && fileInput.files[0]) {
                calculateBill();
            }
        });
    });
});