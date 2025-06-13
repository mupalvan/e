from woocommerce import API
from time import sleep
import csv
import os

# تنظیم اتصال به ووکامرس
wcapi = API(
    url="https://ehsanstore.ir/",
    consumer_key="ck_000fbb9f08fcd924776db7af5e040d179b044f75",
    consumer_secret="cs_61ec024891b4b178006ffcf3199e3ab0178b817b",
    version="wc/v3",
    timeout=120,
    verify_ssl=True,
    headers={"User-Agent": "Mozilla/5.0 (compatible; SyncScript/1.0)"}
)

# ایجاد دایرکتوری لاگ
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "update_product_type_log.csv")
csv_file = open(log_file, mode='w', newline='', encoding='utf-8')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Product ID', 'Product Name', 'Old Type', 'New Type', 'Status', 'Message'])

page = 1
while True:
    response = wcapi.get("products", params={"per_page": 100, "page": page})
    if response.status_code != 200:
        print(f"❌ خطا در دریافت محصولات صفحه {page}: {response.text}")
        break

    products = response.json()
    if not products:
        print("✅ همه محصولات پردازش شدند.")
        break

    for product in products:
        prod_id = product['id']
        prod_name = product['name']
        prod_type = product['type']

        if prod_type == 'simple':
            print(f"⏳ تغییر نوع محصول {prod_id} - '{prod_name}' از simple به variable...")
            update_resp = wcapi.put(f"products/{prod_id}", {"type": "variable"})
            if update_resp.status_code == 200:
                print(f"✅ محصول {prod_id} با موفقیت به variable تغییر یافت.")
                csv_writer.writerow([prod_id, prod_name, prod_type, 'variable', 'موفق', ''])
            else:
                print(f"❌ خطا در تغییر محصول {prod_id}: {update_resp.text}")
                csv_writer.writerow([prod_id, prod_name, prod_type, 'variable', 'خطا', update_resp.text])
        else:
            print(f"⚠️ محصول {prod_id} - '{prod_name}' قبلاً variable است، رد شد.")
            csv_writer.writerow([prod_id, prod_name, prod_type, prod_type, 'رد شد', 'از قبل variable بود'])

        sleep(1)  # جلوگیری از فشار بیش از حد روی سرور

    page += 1

csv_file.close()
print(f"🔚 عملیات تمام شد. لاگ در فایل {log_file} ذخیره شده.")
