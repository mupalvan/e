import pyodbc
from woocommerce import API
import os
import csv
from time import sleep
import sqlite3

conn = sqlite3.connect('ehsanDBproduct.db')  # به جای your_database.db اسم فایل دیتابیست رو بذار

# ساختن کرسر
cursor = conn.cursor()



# اتصال به ووکامرس
wcapi = API(
    url="https://ehsanstore.ir/",
    consumer_key="ck_000fbb9f08fcd924776db7af5e040d179b044f75",
    consumer_secret="cs_61ec024891b4b178006ffcf3199e3ab0178b817b",
    version="wc/v3",
    timeout=120,
    verify_ssl=True,
    headers={"User-Agent": "Mozilla/5.0 (compatible; SyncScript/1.0)"}
)

# ⚙️ دیکشنری ثابت: نام فارسی → slug
CATEGORY_SLUG_MAP = {
    "اکسسوری": "accessories",
    "کفشور": "floor-drain-cover",
    "جای دستمال": "tissue-holder",
    "جای مایع": "soap-dispenser",
    "رخت آویز": "clothes-hanger",
    "سرویس حمام": "bathroom-set",
    "شلنگ و شاتاف": "shower-hose-shattaf",
    "دوش": "shower",
    "دوش پیانویی": "piano-shower",
    "سر دوش": "shower-head",
    "علم دوش": "shower-arm",
    "سینک": "sink",
    "سینک آبشاری": "waterfall-sink",
    "سینک پیانویی": "piano-sink"
}
colors_dict = {
    "nickel": "کروم مات",
    "black": "مشکی",
    "gold": "طلایی",
    "cream": "کرم",
    "chrome": "کروم",
    "gray": "طوسی",
    "white": "سفید",
    "bronze": "برنز",
    "mgold": "طلایی مات",
    "dodi": "دودی",
    "rozegold": "رزگلد"
}

# 📦 گرفتن همه دسته‌بندی‌ها از ووکامرس
resp = wcapi.get("products/categories", params={"per_page": 100, "hide_empty": False})
if resp.status_code != 200:
    print("❌ خطا در دریافت دسته‌بندی‌ها از ووکامرس")
    exit()

all_categories = resp.json()
slug_to_id = {cat['slug']: cat['id'] for cat in all_categories}

# ✅ تابع نگاشت دسته
def resolve_category_id(persian_name):
    slug = CATEGORY_SLUG_MAP.get(persian_name)
    if not slug:
        print(f"❌ دسته‌بندی «{persian_name}» در دیکشنری تعریف نشده.")
        return None
    return slug_to_id.get(slug)

# 📌 دریافت ویژگی رنگ
response = wcapi.get("products/attributes")
attributes = response.json()
pa_color_id = next((attr['id'] for attr in attributes if attr['slug'] == 'pa_color'), None)
if not pa_color_id:
    print("ویژگی pa_color پیدا نشد!")
    exit()

# 📥 دریافت محصولات
cursor.execute("""
    SELECT *
    FROM products
    ORDER BY id
""")
products = []
for row in cursor.fetchall():
    products.append({
        'sku': str(row[0]) if row[0] is not None else '',
        'name': row[1] or '',
        'description': row[2] or '',
        'keyword': row[3] or '',
        'price': row[4] if row[4] is not None else 0.0,
        'category': row[5] or '',
        'stock_quantity': row[6] if row[6] is not None else 0,
        'productType': row[7] or '',
        'color': row[8] or '',
        'material': row[9] or '',
        'type': row[10] or '',
        'dimensions': row[11] or '',
        'brand': row[12] or '',
        'guarantee': row[13] or '',
        'label': row[14] or ''
    })


cursor.close()
conn.close()

# 📝 فایل لاگ
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "sync_log.csv")
csv_writer = csv.writer(open(log_file, mode='w', newline='', encoding='utf-8'))
csv_writer.writerow(['نوع عملیات', 'SKU', 'نام محصول', 'وضعیت', 'توضیحات'])

# 👪 گروه‌بندی محصولات
groups = {}
for p in products:
    groups.setdefault(p['name'], []).append(p)

# 📷 مسیر تصاویر
base_image_url = "https://ehsanstore.ir/wp-content/uploads/images/"

# 🧩 ایجاد محصولات متغیر و وارییشن‌ها
for name, group_products in groups.items():
    parent = group_products[0]
    parent_image_url = f"{base_image_url}{parent['sku']}.webp"
    category_id = resolve_category_id(parent['category'])

    if not category_id:
        csv_writer.writerow(['ایجاد والد', '', name, 'خطا', 'دسته‌بندی یافت نشد'])
        continue
    
    parent_data = {
        "name": name,
        "type": parent['type'],
        "description": parent['description'],
        "categories": [{"id": category_id}],
        "attributes": [{
            "id": pa_color_id,
            "name": "رنگ",
            "slug": "pa_color",
            "visible": True,
            "variation": True,
            "options": list(set(colors_dict[p['color']] for p in group_products))
        }],
        "images": [{"src": parent_image_url}]
    }


    # بررسی وجود محصول والد
    existing = wcapi.get("products", params={"search": name}).json()
    if isinstance(existing, list) and any(p['name'] == name for p in existing):
        parent_id = existing[0]['id']
        wcapi.put(f"products/{parent_id}", parent_data)

        csv_writer.writerow(['آپدیت والد', '', name, 'موفق', f"ID: {parent_id}"])
    else:
        resp = wcapi.post("products", parent_data)

        if resp.status_code != 201:
            csv_writer.writerow(['ایجاد والد', '', name, 'خطا', str(resp.json())])
            continue
        parent_id = resp.json()['id']
        csv_writer.writerow(['ایجاد والد', '', name, 'موفق', f"ID: {parent_id}"])

    # وارییشن‌ها
    for var in group_products:
        sku = var['sku']
        stock = var['stock_quantity']
        var_image_url = f"{base_image_url}{sku}.webp"
        # print(stock)
        var_data = {
            "regular_price": str(var['price']),
            "sku": sku,
            "meta_data": [{"key": "gtin", "value": sku}],
            "attributes": [{"id": pa_color_id, "name": "رنگ", "option": colors_dict[var['color']]}],
            "image": {"src": var_image_url},
            "manage_stock": True,
            "stock_quantity": stock,
            "stock_status": "instock" if stock > 0 else "outofstock"
        }

        variations = wcapi.get(f"products/{parent_id}/variations").json()
        existing_var = next((v for v in variations if v.get('sku') == sku), None)

        if existing_var:
            var_id = existing_var['id']
            wcapi.put(f"products/{parent_id}/variations/{var_id}", var_data)
            csv_writer.writerow(['آپدیت وارییشن', sku, name, 'موفق', f"ID: {var_id}"])
        else:
            resp = wcapi.post(f"products/{parent_id}/variations", var_data)
            if resp.status_code != 201:
                csv_writer.writerow(['ایجاد وارییشن', sku, name, 'خطا', str(resp.json())])
            else:
                var_id = resp.json()['id']
                csv_writer.writerow(['ایجاد وارییشن', sku, name, 'موفق', f"ID: {var_id}"])
    sleep(3)
print(f"✅ اسکریپت با موفقیت اجرا شد. فایل لاگ: {log_file}")
