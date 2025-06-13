import pyodbc
from woocommerce import API
import os
import csv
from time import sleep
import sqlite3

# اتصال به SQLite
conn = sqlite3.connect("ehsanDBproduct.db")
cursor = conn.cursor()

# اتصال به ووکامرس
wcapi = API(
    url="https://ehsanstore.ir/",
    consumer_key="ck_000fbb9f08fcd924776db7af5e040d179b044f75",
    consumer_secret="cs_61ec024891b4b178006ffcf3199e3ab0178b817b",
    version="wc/v3",
    timeout=120,
    verify_ssl=True,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:115.0) Gecko/20100101 Firefox/115.0",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
)

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

resp = wcapi.get("products/categories", params={"per_page": 100, "hide_empty": False})
if resp.status_code != 200:
    print("❌ خطا در دریافت دسته‌بندی‌ها از ووکامرس")
    exit()

all_categories = resp.json()
slug_to_id = {cat['slug']: cat['id'] for cat in all_categories}

def resolve_category_id(persian_name):
    slug = CATEGORY_SLUG_MAP.get(persian_name)
    if not slug:
        print(f"❌ دسته‌بندی «{persian_name}» در دیکشنری تعریف نشده.")
        return None
    return slug_to_id.get(slug)

response = wcapi.get("products/attributes")
attributes = response.json()
pa_color_id = next((attr['id'] for attr in attributes if attr['slug'] == 'pa_color'), None)
if not pa_color_id:
    print("ویژگی pa_color پیدا نشد!")
    exit()

cursor.execute("""
    SELECT *
    FROM products
    WHERE name = 'کفشور استیل مدل 7000'
    ORDER BY id
""")

columns = [column[0] for column in cursor.description]
products = [dict(zip(columns, row)) for row in cursor.fetchall()]
cursor.close()
conn.close()

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "sync_log.csv")
csv_writer = csv.writer(open(log_file, mode='w', newline='', encoding='utf-8'))
csv_writer.writerow(['نوع عملیات', 'SKU', 'نام محصول', 'وضعیت', 'توضیحات'])

groups = {}
for p in products:
    groups.setdefault(p['name'], []).append(p)

base_image_url = "https://ehsanstore.ir/wp-content/uploads/images/"
price = 0
default_attributes = ''
for name, group_products in groups.items():
    for var in group_products:
        if price == 0:
            price = int(var['price'])
            default_attributes = var['color']
        if price > int(var['price']):
            price = int(var['price'])
            default_attributes = var['color']
    parent = group_products[0]
    parent_image_url = f"{base_image_url}{parent['id']}.webp"
    category_id = resolve_category_id(parent['category'])

    if not category_id:
        csv_writer.writerow(['ایجاد والد', '', name, 'خطا', 'دسته‌بندی یافت نشد'])
        continue
    length, width, height = map(str, str(parent['dimensions']).split('x'))
    tags_str = parent.get("label", "")  # فرض بر اینه که ستون label توی دیتابیس خوندی
    tags_list = [t.strip() for t in tags_str.split('-') if t.strip()]
    tag_objects = [{"name": tag} for tag in tags_list]
    
    parent_data = {
        "name": name,
        "type": "variable",  # حتما نوع محصول والد variable باشد
        "description": str(parent['description']),
        "categories": [{"id": category_id}],
        "default_attributes": [
            {
                "id": 1,
                "name": "رنگ",
                "option": default_attributes
            }
        ],
        "tags": tag_objects,
        "dimensions": {
        "length": length,
        "width": width,
        "height": height
        },
        "attributes": [{
            "id": 1,
            "name": "رنگ",
            "slug": "pa_color",
            "visible": True,
            "variation": True,
            "options": list(set(colors_dict.get(p['color'], p['color']) for p in group_products))
        },
        {
            "id": 2,
            "name": "گارانتی",
            "slug": "گارانتی",
            "position": 2,
            "visible": True,
            "variation": False,
            "options": [str(parent['guarantee'])]
        },
        {
            "id": 3,
            "name": "جنس بدنه",
            "slug": "جنس بدنه",
            "position": 3,
            "visible": True,
            "variation": False,
            "options": [str(parent['material'])]
        },
        {
            "id": 4,
            "name": "نوع",
            "slug": "نوع",
            "position": 4,
            "visible": True,
            "variation": False,
            "options": [str(parent['type'])]
        }
        ],
        "images": [{"src": parent_image_url}],
        "brands": [
        {
            "id": int(parent['brand']),
        }
        ],
        "meta_data": [
            {
                "key": "rank_math_focus_keyword",
                "value": str(parent['keyword']).replace('-', ',')
            }
        ]
    }
    existing = wcapi.get("products", params={"search": name}).json()
    if isinstance(existing, list) and any(p['name'] == name for p in existing):
        parent_id = existing[0]['id']
        resp = wcapi.put(f"products/{parent_id}", parent_data)
        if resp.status_code in [200, 201]:
            sleep(3)  # مکث تا داده‌ها ثبت شود
            # دریافت محصول به‌روز شده برای اطمینان
            updated_product = wcapi.get(f"products/{parent_id}").json()
            if updated_product.get('type') != 'variable':
                print(f"⚠️ هشدار: محصول {name} هنوز variable نشده!")
            csv_writer.writerow(['آپدیت والد', '', name, 'موفق', f"ID: {parent_id}"])
        else:
            csv_writer.writerow(['آپدیت والد', '', name, 'خطا', str(resp.json())])
            continue
    else:
        resp = wcapi.post("products", parent_data)
        if resp.status_code != 201:
            csv_writer.writerow(['ایجاد والد', '', name, 'خطا', str(resp.json())])
            continue
        parent_id = resp.json()['id']
        sleep(3)  # مکث برای ثبت نهایی
        updated_product = wcapi.get(f"products/{parent_id}").json()
        if updated_product.get('type') != 'variable':
            print(f"⚠️ هشدار: محصول {name} هنوز variable نشده!")
        csv_writer.writerow(['ایجاد والد', '', name, 'موفق', f"ID: {parent_id}"])
    
    for var in group_products:
        sku = str(var['id'])
        stock = var['stock_quantity']
        var_image_url = f"{base_image_url}{sku}.webp"

        var_data = {
            "regular_price": str(var['price']),
            "sku": sku,
            "meta_data": [{"key": "gtin", "value": sku}],
            "attributes": [{"id": pa_color_id, "name": "رنگ", "option": colors_dict.get(var['color'], var['color'])}],
            "image": {"src": var_image_url},
            "manage_stock": True,
            "stock_quantity": stock,
            "stock_status": "instock" if stock > 0 else "outofstock"
            
        }

        variations = wcapi.get(f"products/{parent_id}/variations").json()
        existing_var = next((v for v in variations if v.get('sku') == sku), None)

        if existing_var:
            var_id = existing_var['id']
            resp = wcapi.put(f"products/{parent_id}/variations/{var_id}", var_data)
            if resp.status_code == 200:
                csv_writer.writerow(['آپدیت وارییشن', sku, name, 'موفق', f"ID: {var_id}"])
            else:
                csv_writer.writerow(['آپدیت وارییشن', sku, name, 'خطا', str(resp.json())])
        else:
            resp = wcapi.post(f"products/{parent_id}/variations", var_data)
            if resp.status_code != 201:
                csv_writer.writerow(['ایجاد وارییشن', sku, name, 'خطا', str(resp.json())])
            else:
                var_id = resp.json()['id']
                csv_writer.writerow(['ایجاد وارییشن', sku, name, 'موفق', f"ID: {var_id}"])

    sleep(3)
    price = 0
print(f"✅ اسکریپت با موفقیت اجرا شد. فایل لاگ: {log_file}")

