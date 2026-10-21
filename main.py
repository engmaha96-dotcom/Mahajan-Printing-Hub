import os
import uuid
import json
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import io

# PDF Reader fallback setup
try:
    import fitz  # PyMuPDF
    USE_FITZ = True
except ImportError:
    from pypdf import PdfReader
    USE_FITZ = False

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

os.makedirs(UPLOAD_DIR, exist_ok=True)

if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

BASE_RATES = {
    "A4": {"bw_single": 1.20, "bw_double": 1.50, "color_single": 1.80, "color_double": 2.20},
    "Legal": {"bw_single": 1.30, "bw_double": 1.60, "color_single": 2.00, "color_double": 2.50},
    "A3": {"bw_single": 8.00, "bw_double": 10.00, "color_single": 13.00, "color_double": 15.00}
}

DELIVERY_RATES = {
    "express_dhaka": 150,
    "regular_dhaka": 70,
    "outside_dhaka": 160,
    "pickup": 0
}

temp_file_store = {}

@app.post("/api/calculate")
async def calculate_price(
    file: UploadFile = File(...),
    paper_size: str = Form("A4"),
    color_type: str = Form("bw"),
    print_side: str = Form("single"),
    gsm: int = Form(80),
    binding: str = Form("none"),
    lamination: str = Form("false"),
    delivery_option: str = Form("regular_dhaka")
):
    try:
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        
        if file_size_mb > 50:
            raise HTTPException(status_code=400, detail="ফাইলের সাইজ ৫০ মেগাবাইটের বেশি হতে পারবে না।")

        page_count = 0
        if USE_FITZ:
            try:
                doc = fitz.open(stream=contents, filetype="pdf")
                page_count = doc.page_count
                doc.close()
            except Exception:
                pass

        if page_count == 0:
            try:
                pdf_reader = PdfReader(io.BytesIO(contents))
                page_count = len(pdf_reader.pages)
            except Exception:
                raise HTTPException(status_code=400, detail="অবৈধ বা ক্ষতিগ্রস্ত PDF ফাইল!")

        if page_count == 0:
            raise HTTPException(status_code=400, detail="PDF ফাইলে কোনো পেজ পাওয়া যায়নি।")

        rate_key = f"{color_type}_{print_side}"
        base_unit_price = BASE_RATES.get(paper_size, {}).get(rate_key, 1.20)

        gsm_diff = (gsm - 80) / 10
        adjusted_unit_price = base_unit_price + (gsm_diff * 0.10)

        if print_side == "double":
            total_sheets = (page_count + 1) // 2
            print_cost = total_sheets * adjusted_unit_price
        else:
            total_sheets = page_count
            print_cost = page_count * adjusted_unit_price

        lamination_cost = 0
        if str(lamination).lower() in ["true", "1", "yes"]:
            rate_per_page = 20 if paper_size == "Legal" else 15
            lamination_cost = page_count * rate_per_page

        binding_cost = 0
        if binding == "stapler":
            binding_cost = 10
        elif binding == "spiral":
            binding_cost = 80 if paper_size == "Legal" else 60
        elif binding == "hardcover":
            binding_cost = 130 if paper_size == "Legal" else 100

        delivery_cost = DELIVERY_RATES.get(delivery_option, 70)
        grand_total = print_cost + lamination_cost + binding_cost + delivery_cost

        session_id = str(uuid.uuid4())
        temp_file_store[session_id] = {
            "file_name": file.filename,
            "contents": contents,
            "details": {
                "paper_size": paper_size,
                "color_type": color_type,
                "print_side": print_side,
                "gsm": gsm,
                "binding": binding,
                "lamination": lamination,
                "delivery_option": delivery_option,
                "page_count": page_count,
                "grand_total": round(grand_total, 2)
            }
        }

        return {
            "status": "success",
            "session_id": session_id,
            "page_count": page_count,
            "total_sheets": total_sheets,
            "print_cost": round(print_cost, 2),
            "lamination_cost": round(lamination_cost, 2),
            "binding_cost": round(binding_cost, 2),
            "delivery_cost": round(delivery_cost, 2),
            "grand_total": round(grand_total, 2)
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")

@app.post("/api/checkout")
async def process_checkout(
    session_id: str = Form(""),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    address: str = Form(...),
    payment_method: str = Form(...),
    trx_id: str = Form(""),
    amount: float = Form(...)
):
    order_id = f"MICL-{uuid.uuid4().hex[:8].upper()}"
    saved_filename = "N/A"

    if session_id in temp_file_store:
        session_data = temp_file_store.pop(session_id)
        original_name = session_data["file_name"]
        saved_filename = f"{order_id}_{original_name}"
        file_path = os.path.join(UPLOAD_DIR, saved_filename)
        
        with open(file_path, "wb") as f:
            f.write(session_data["contents"])

    order_entry = {
        "order_id": order_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "address": address,
        "payment_method": payment_method,
        "trx_id": trx_id,
        "amount": amount,
        "file_name": saved_filename
    }

    try:
        with open(ORDERS_FILE, "r+", encoding="utf-8") as f:
            orders = json.load(f)
            orders.insert(0, order_entry)
            f.seek(0)
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving order:", e)

    return {
        "status": "success",
        "order_id": order_id,
        "message": f"ধন্যবাদ {customer_name}! আপনার অর্ডারটি সফলভাবে সেভ হয়েছে।"
    }

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            orders = json.load(f)
    except Exception:
        orders = []

    rows = ""
    for o in orders:
        download_link = f'<a href="/download/{o["file_name"]}" target="_blank" class="btn-download">📄 ডাউনলোড</a>' if o.get("file_name") and o["file_name"] != "N/A" else '<span style="color:#888;">ফাইল নেই</span>'
        rows += f"""
        <tr>
            <td><b style="color:#0F3863;">{o.get('order_id', 'N/A')}</b></td>
            <td><small>{o.get('timestamp', 'N/A')}</small></td>
            <td><b>{o.get('customer_name', 'N/A')}</b><br><small style="color:#555;">📞 {o.get('customer_phone', 'N/A')}</small></td>
            <td>{o.get('address', 'N/A')}</td>
            <td><span class="badge">{str(o.get('payment_method', '')).upper()}</span><br><small style="color:#333;">Trx: <b>{o.get('trx_id', 'N/A')}</b></small></td>
            <td style="color:#27ae60; font-weight:bold;">৳ {o.get('amount', 0)}</td>
            <td>{download_link}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Dashboard - Mahajan IT Printing Hub</title>
        <style>
            * {{ box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            body {{ background-color: #f4f7f6; margin: 0; padding: 30px; color: #333; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: #ffffff; border-radius: 10px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0F3863; padding-bottom: 15px; margin-bottom: 20px; }}
            .header h2 {{ color: #0F3863; margin: 0; font-size: 24px; }}
            .stats {{ background: #0F3863; color: #fff; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 14px 12px; border-bottom: 1px solid #eee; text-align: left; font-size: 14px; }}
            th {{ background-color: #0F3863; color: white; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }}
            tr:hover {{ background-color: #f8f9fa; }}
            .badge {{ background-color: #00A8B5; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
            .btn-download {{ background-color: #E58E26; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 12px; transition: 0.2s; display: inline-block; }}
            .btn-download:hover {{ background-color: #d37e1a; }}
            .no-orders {{ text-align: center; padding: 40px; color: #777; font-size: 16px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📦 Mahajan IT Printing Hub — Admin Dashboard</h2>
                <div class="stats">মোট অর্ডার: {len(orders)} টি</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>অর্ডার আইডি</th>
                        <th>তারিখ ও সময়</th>
                        <th>গ্রাহক তথ্য</th>
                        <th>ডেলিভারি ঠিকানা</th>
                        <th>পেমেন্ট & TrxID</th>
                        <th>মোট বিল</th>
                        <th>প্রিন্ট ফাইল</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="7" class="no-orders">এখনো কোনো অর্ডার রিসিভ হয়নি।</td></tr>'}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/download/{file_name}")
async def download_file(file_name: str):
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=file_name)
    raise HTTPException(status_code=404, detail="File not found")

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")