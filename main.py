import html
import io
import json
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

try:
    import fitz
except ImportError:
    fitz = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


app = FastAPI(title="Mahajan IT Printing Hub Portal")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_files"
ORDERS_FILE = "orders.json"
MAX_FILE_BYTES = 50 * 1024 * 1024
HOTLINE = "01839802001"

os.makedirs(UPLOAD_DIR, exist_ok=True)
if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w", encoding="utf-8") as orders_file:
        json.dump([], orders_file)

# The established per-page print rates remain the source of truth for the
# calculator; GSM adds a small paper-cost adjustment around the standard 80 GSM.
BASE_RATES = {
    "A4": {"bw_single": 1.20, "bw_double": 1.50, "color_single": 1.80, "color_double": 2.20},
    "Legal": {"bw_single": 1.30, "bw_double": 1.60, "color_single": 2.00, "color_double": 2.50},
}
GSM_ADJUSTMENTS = {70: -0.10, 80: 0.0, 100: 0.20}
BINDING_RATES = {"none": 0, "staple": 0, "spiral": 70, "hardcover": 150}
DELIVERY_RATES = {"dhaka": 60, "outside_dhaka": 160, "pickup": 0}
ALLOWED_GSM = set(GSM_ADJUSTMENTS)
ALLOWED_SIZES = set(BASE_RATES)
ALLOWED_COLOR_TYPES = {"bw", "color"}
ALLOWED_SIDES = {"single", "double"}
ALLOWED_BINDINGS = set(BINDING_RATES)
ALLOWED_DELIVERY = set(DELIVERY_RATES)
ORDER_STATUSES = [
    "Order Received",
    "Printing in Progress",
    "Binding & Finishing",
    "Ready for Pickup",
    "Delivered",
]
LEGACY_STATUS_MAP = {"received": "Order Received"}
temp_file_store: dict[str, dict[str, Any]] = {}


def read_orders() -> list[dict[str, Any]]:
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as orders_file:
            data = json.load(orders_file)
        if not isinstance(data, list):
            return []
        changed = False
        for order in data:
            current_status = order.get("status", "Order Received")
            normalized_status = LEGACY_STATUS_MAP.get(current_status, current_status)
            if normalized_status not in ORDER_STATUSES:
                normalized_status = "Order Received"
            if order.get("status") != normalized_status:
                order["status"] = normalized_status
                changed = True
        if changed:
            write_orders(data)
        return data
    except (OSError, json.JSONDecodeError):
        return []


def write_orders(orders: list[dict[str, Any]]) -> None:
    with open(ORDERS_FILE, "w", encoding="utf-8") as orders_file:
        json.dump(orders, orders_file, ensure_ascii=False, indent=2)


def count_pdf_pages(contents: bytes) -> int:
    if fitz is not None:
        try:
            document = fitz.open(stream=contents, filetype="pdf")
            page_count = document.page_count
            document.close()
            return page_count
        except Exception:
            pass
    if PdfReader is not None:
        try:
            return len(PdfReader(io.BytesIO(contents)).pages)
        except Exception:
            pass
    raise HTTPException(status_code=400, detail="অবৈধ বা ক্ষতিগ্রস্ত PDF ফাইল।")


def validate_options(
    paper_size: str, color_type: str, print_side: str, gsm: int, binding: str, delivery_option: str
) -> None:
    if paper_size not in ALLOWED_SIZES:
        raise HTTPException(status_code=400, detail="A4 অথবা Legal সাইজ নির্বাচন করুন।")
    if color_type not in ALLOWED_COLOR_TYPES or print_side not in ALLOWED_SIDES:
        raise HTTPException(status_code=400, detail="প্রিন্ট মোডের তথ্য সঠিক নয়।")
    if gsm not in ALLOWED_GSM:
        raise HTTPException(status_code=400, detail="70, 80 অথবা 100 GSM নির্বাচন করুন।")
    if binding not in ALLOWED_BINDINGS:
        raise HTTPException(status_code=400, detail="বাইন্ডিং অপশন সঠিক নয়।")
    if delivery_option not in ALLOWED_DELIVERY:
        raise HTTPException(status_code=400, detail="ডেলিভারি অপশন সঠিক নয়।")


@app.post("/api/calculate")
async def calculate_price(
    file: UploadFile = File(...),
    paper_size: str = Form("A4"),
    color_type: str = Form("bw"),
    print_side: str = Form("single"),
    gsm: int = Form(80),
    binding: str = Form("staple"),
    delivery_option: str = Form("dhaka"),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="শুধুমাত্র PDF ফাইল আপলোড করুন।")

    validate_options(paper_size, color_type, print_side, gsm, binding, delivery_option)
    contents = await file.read()
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"ফাইলটি ৫০ MB-এর বেশি। WhatsApp-এ {HOTLINE} নম্বরে পাঠান।",
        )

    page_count = count_pdf_pages(contents)
    if page_count < 1:
        raise HTTPException(status_code=400, detail="PDF ফাইলে কোনো পেজ পাওয়া যায়নি।")

    rate_key = f"{color_type}_{print_side}"
    unit_price = BASE_RATES[paper_size][rate_key] + GSM_ADJUSTMENTS[gsm]
    total_sheets = (page_count + 1) // 2 if print_side == "double" else page_count
    print_cost = total_sheets * unit_price
    binding_cost = BINDING_RATES[binding]
    delivery_cost = DELIVERY_RATES[delivery_option]
    grand_total = print_cost + binding_cost + delivery_cost

    session_id = str(uuid.uuid4())
    temp_file_store[session_id] = {
        "file_name": os.path.basename(file.filename),
        "contents": contents,
        "details": {
            "paper_size": paper_size,
            "color_type": color_type,
            "print_side": print_side,
            "gsm": gsm,
            "binding": binding,
            "delivery_option": delivery_option,
            "page_count": page_count,
            "total_sheets": total_sheets,
            "print_cost": round(print_cost, 2),
            "binding_cost": round(binding_cost, 2),
            "delivery_cost": round(delivery_cost, 2),
            "grand_total": round(grand_total, 2),
        },
    }

    return {"status": "success", "session_id": session_id, **temp_file_store[session_id]["details"]}


@app.post("/api/checkout")
async def process_checkout(
    session_id: str = Form(""),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    address: str = Form(...),
    area: str = Form(""),
    instructions: str = Form(""),
    payment_method: str = Form(...),
    trx_id: str = Form(""),
    amount: float = Form(...),
):
    customer_name = customer_name.strip()
    customer_phone = customer_phone.strip()
    address = address.strip()
    if not customer_name or not customer_phone or not address:
        raise HTTPException(status_code=400, detail="নাম, ফোন নম্বর এবং বিস্তারিত ঠিকানা দিন।")
    if session_id not in temp_file_store:
        raise HTTPException(status_code=400, detail="অর্ডার সেশনটি পাওয়া যায়নি। PDF আবার আপলোড করুন।")

    session_data = temp_file_store.pop(session_id)
    expected_amount = float(session_data["details"]["grand_total"])
    if abs(float(amount) - expected_amount) > 0.01:
        raise HTTPException(status_code=400, detail="অর্ডারের মোট বিল পরিবর্তিত হয়েছে। আবার হিসাব করুন।")

    order_id = f"MJ-{uuid.uuid4().hex[:6].upper()}"
    saved_filename = f"{order_id}_{os.path.basename(session_data['file_name'])}"
    with open(os.path.join(UPLOAD_DIR, saved_filename), "wb") as saved_file:
        saved_file.write(session_data["contents"])

    order_entry = {
        "order_id": order_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "address": address,
        "area": area.strip(),
        "instructions": instructions.strip(),
        "payment_method": payment_method,
        "trx_id": trx_id.strip(),
        "amount": expected_amount,
        "status": "Order Received",
        "file_name": saved_filename,
        "details": session_data["details"],
    }
    orders = read_orders()
    orders.insert(0, order_entry)
    write_orders(orders)

    return {
        "status": "success",
        "order_id": order_id,
        "amount": expected_amount,
        "message": f"ধন্যবাদ {customer_name}! আপনার অর্ডারটি সফলভাবে গ্রহণ করা হয়েছে।",
    }


@app.get("/api/orders/track/{order_id}")
@app.get("/api/track/{order_id}")
async def track_order(order_id: str):
    order = next((item for item in read_orders() if item.get("order_id") == order_id.strip().upper()), None)
    if not order:
        raise HTTPException(status_code=404, detail="এই Order ID-এর কোনো অর্ডার পাওয়া যায়নি।")
    return {
        "status": "success",
        "order_id": order["order_id"],
        "status_code": order.get("status", "Order Received"),
        "status_label": order.get("status", "Order Received"),
        "timestamp": order.get("timestamp"),
        "amount": order.get("amount", 0),
        "customer_name": order.get("customer_name", ""),
        "paper_size": order.get("details", {}).get("paper_size"),
        "page_count": order.get("details", {}).get("page_count"),
    }


class OrderStatusUpdate(BaseModel):
    order_id: str
    status: str


@app.post("/api/admin/orders/update-status")
@app.patch("/api/admin/orders/update-status")
async def update_order_status(payload: OrderStatusUpdate):
    order_id = payload.order_id.strip().upper()
    if payload.status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status.")

    orders = read_orders()
    order = next((item for item in orders if item.get("order_id") == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    order["status"] = payload.status
    order["status_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_orders(orders)
    return {
        "status": "success",
        "order_id": order_id,
        "order_status": payload.status,
        "updated_at": order["status_updated_at"],
    }


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    orders = read_orders()
    rows = []
    for order in orders:
        order_id = html.escape(str(order.get("order_id", "N/A")))
        filename = order.get("file_name")
        download = (
            f'<a href="/download/{html.escape(str(filename))}" class="btn-download">Download PDF</a>'
            if filename and filename != "N/A"
            else '<span class="muted">No file</span>'
        )
        order_status = order.get("status", "Order Received")
        status_options = "".join(
            f'<option value="{html.escape(status)}" {"selected" if status == order_status else ""}>{html.escape(status)}</option>'
            for status in ORDER_STATUSES
        )
        rows.append(
            f"""
            <tr class="order-row" data-status="{html.escape(order_status)}">
                <td><strong>{order_id}</strong><small>{html.escape(str(order.get("timestamp", "N/A")))}</small></td>
                <td><strong>{html.escape(str(order.get("customer_name", "N/A")))}</strong><small>{html.escape(str(order.get("customer_phone", "N/A")))}</small></td>
                <td>{html.escape(str(order.get("area", "N/A")))}<small>{html.escape(str(order.get("address", "N/A")))}</small></td>
                <td><select class="status-select" data-order-id="{order_id}">{status_options}</select><small class="status-meta">{html.escape(str(order.get("payment_method", "")).upper())} · {html.escape(str(order.get("trx_id", "No TrxID")))}</small></td>
                <td class="amount">৳ {float(order.get("amount", 0)):.2f}</td>
                <td>{download}</td>
            </tr>
            """
        )

    order_rows = "".join(rows) if rows else '<tr class="empty-row"><td colspan="6">No orders received yet.</td></tr>'
    return HTMLResponse(
        f"""<!doctype html>
        <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Admin · Mahajan IT Printing Hub</title>
        <style>
        :root{{font-family:Inter,Segoe UI,sans-serif;color:#10233b;background:#f6f8fb}}*{{box-sizing:border-box}}body{{margin:0;padding:32px}}.shell{{max-width:1400px;margin:auto;background:#fff;border:1px solid #dfe7ef;border-radius:20px;box-shadow:0 18px 50px #10233b12;overflow:hidden}}header{{padding:28px 32px;background:#0f3863;color:#fff;display:flex;justify-content:space-between;gap:20px;align-items:center}}h1{{margin:0;font-size:clamp(1.35rem,3vw,2rem)}}header p{{margin:6px 0 0;color:#d4e4f0}}.count{{background:#00a8b5;padding:10px 14px;border-radius:99px;font-weight:800;white-space:nowrap}}.filters{{display:flex;gap:10px;padding:20px 24px;border-bottom:1px solid #e8eef4}}.filter{{border:1px solid #dfe7ef;background:#fff;color:#52708b;border-radius:10px;padding:10px 14px;font-weight:800;cursor:pointer}}.filter.active{{background:#0f3863;color:#fff;border-color:#0f3863}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;min-width:980px}}th,td{{padding:16px 18px;text-align:left;border-bottom:1px solid #e8eef4;vertical-align:top}}th{{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:#52708b;background:#f8fafc}}td strong{{display:block;color:#0f3863}}td small{{display:block;margin-top:5px;color:#6b8194;line-height:1.45}}.status-select{{min-height:38px;border:1px solid #cdd9e4;border-radius:8px;background:#fff;color:#0f3863;padding:6px 9px;font-weight:800;max-width:210px}}.status-select:focus{{border-color:#00a8b5;outline:3px solid #00a8b522}}.status-select.saving{{opacity:.6}}.status-select.saved{{border-color:#00a8b5;background:#e8fbfa}}.status-select.failed{{border-color:#d94b4b;background:#fff1f1}}.amount{{font-weight:800;color:#d37d19;white-space:nowrap}}.btn-download{{display:inline-block;padding:9px 12px;background:#0f3863;color:#fff;border-radius:8px;text-decoration:none;font-size:.8rem;font-weight:700}}.muted{{color:#9aa8b4;font-size:.85rem}}.empty-row td{{text-align:center;padding:56px;color:#6b8194}}@media(max-width:700px){{body{{padding:12px}}header{{padding:22px;align-items:flex-start;flex-direction:column}}.filters{{padding:16px;overflow:auto}}}}
        </style></head><body><main class="shell"><header><div><h1>Mahajan IT Printing Hub</h1><p>Incoming orders · Admin dashboard</p></div><div class="count"><span id="orderCount">{len(orders)} orders</span></div></header>
        <div class="filters"><button class="filter active" data-filter="active">Active Orders</button><button class="filter" data-filter="completed">Completed Orders</button></div>
        <div class="table-wrap"><table><thead><tr><th>Order</th><th>Customer</th><th>Delivery</th><th>Payment / status</th><th>Total</th><th>File</th></tr></thead><tbody id="ordersBody">
        {order_rows}
        </tbody></table></div></main><script>
        const statuses = {json.dumps(ORDER_STATUSES)};
        const emptyRow = '<tr class="empty-row"><td colspan="6">No orders in this view.</td></tr>';
        function applyFilter(filter) {{
          const rows = [...document.querySelectorAll('.order-row')];
          let visible = 0;
          rows.forEach(row => {{
            const isCompleted = row.dataset.status === 'Delivered';
            const show = filter === 'completed' ? isCompleted : !isCompleted;
            row.style.display = show ? '' : 'none';
            if (show) visible++;
          }});
          document.querySelector('.empty-row')?.remove();
          if (!visible) document.querySelector('#ordersBody').insertAdjacentHTML('beforeend', emptyRow);
          document.querySelector('#orderCount').textContent = `${{visible}} ${{visible === 1 ? 'order' : 'orders'}}`;
        }}
        document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => {{
          document.querySelectorAll('.filter').forEach(item => item.classList.remove('active'));
          button.classList.add('active');
          applyFilter(button.dataset.filter);
        }}));
        document.querySelectorAll('.status-select').forEach(select => select.addEventListener('change', async () => {{
          const previous = select.dataset.previous || select.value;
          select.dataset.previous = previous;
          select.classList.add('saving');
          try {{
            const response = await fetch('/api/admin/orders/update-status', {{
              method: 'PATCH',
              headers: {{'Content-Type': 'application/json'}},
              body: JSON.stringify({{order_id: select.dataset.orderId, status: select.value}})
            }});
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Could not update status.');
            select.closest('tr').dataset.status = data.order_status;
            select.classList.remove('failed');
            select.classList.add('saved');
            select.dataset.previous = data.order_status;
            const activeFilter = document.querySelector('.filter.active').dataset.filter;
            applyFilter(activeFilter);
            setTimeout(() => select.classList.remove('saved'), 1200);
          }} catch (error) {{
            select.value = previous;
            select.classList.add('failed');
            alert(error.message);
          }} finally {{
            select.classList.remove('saving');
          }}
        }}));
        applyFilter('active');
        </script></body></html>"""
    )


@app.get("/download/{file_name}")
async def download_file(file_name: str):
    safe_name = os.path.basename(file_name)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=safe_name, media_type="application/pdf")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
