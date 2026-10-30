import os
import json
import uuid
from typing import List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="Mahajan IT Printing Hub API")

# Directory setup
UPLOAD_DIR = "uploaded_files"
ORDERS_FILE = "orders.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)

if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.post("/api/order")
async def create_order(
    files: List[UploadFile] = File(...),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    address: str = Form(...),
    paper_size: str = Form("A4"),
    gsm: str = Form("80"),
    color_type: str = Form("bw"),
    print_side: str = Form("single"),
    binding: str = Form("none"),
    delivery_option: str = Form("dhaka"),
    payment_method: str = Form("bkash"),
    trx_id: str = Form("")
):
    saved_files = []
    max_size = 100 * 1024 * 1024  # 100 MB Limit

    # Process and save uploaded PDF files
    for file in files:
        contents = await file.read()
        if len(contents) > max_size:
            raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 100 MB limit.")
        
        file_id = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, file_id)
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        saved_files.append({"filename": file.filename, "path": file_path, "size": len(contents)})

    # Generate unique order ID
    order_id = f"MJ-{uuid.uuid4().hex[:6].upper()}"
    new_order = {
        "order_id": order_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "address": address,
        "paper_size": paper_size,
        "gsm": gsm,
        "color_type": color_type,
        "print_side": print_side,
        "binding": binding,
        "delivery_option": delivery_option,
        "payment_method": payment_method,
        "trx_id": trx_id,
        "files": saved_files,
        "status": "Received"
    }

    try:
        with open(ORDERS_FILE, "r+", encoding="utf-8") as f:
            orders = json.load(f)
            orders.append(new_order)
            f.seek(0)
            json.dump(orders, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save order")

    return {"status": "success", "order_id": order_id, "customer_name": customer_name}

@app.get("/api/track/{order_id}")
async def track_order(order_id: str):
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            orders = json.load(f)
            for order in orders:
                if order["order_id"].upper() == order_id.upper():
                    return {"status": "success", "order": order}
    except Exception:
        pass
    
    raise HTTPException(status_code=404, detail="Order ID not found")