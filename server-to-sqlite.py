import sqlite3
import pyodbc

# اتصال به SQLite
sqlite_conn = sqlite3.connect('ehsanDBproduct.db')
sqlite_cursor = sqlite_conn.cursor()

# اتصال به SQL Server
sqlserver_conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=DESKTOP-RFH2G51;'
    'DATABASE=KarbinoEMP_Ehsan_1404;'
    'Trusted_Connection=yes;'
)
sqlserver_cursor = sqlserver_conn.cursor()

# مرحله ۱: دریافت کالاها با SitePrice معتبر
sqlserver_cursor.execute("""
    SELECT Code_Kala, SitePrice 
    FROM Kalas 
    WHERE SitePrice != 0
""")
kalas_data = sqlserver_cursor.fetchall()

# ساخت مجموعه‌ای از آی‌دی‌های معتبر
valid_ids = set(str(codekala) for codekala, _ in kalas_data)

# مرحله ۲ و ۳: بررسی وجود، آپدیت یا درج قیمت
for codekala, siteprice in kalas_data:
    sqlite_cursor.execute("SELECT price FROM products WHERE id = ?", (codekala,))
    row = sqlite_cursor.fetchone()

    if row:
        current_price = row[0]
        if current_price != siteprice:
            sqlite_cursor.execute("UPDATE products SET price = ? WHERE id = ?", (siteprice, codekala))
            print(f"Updated: id={codekala}, price: {current_price} -> {siteprice}")
    else:
        sqlite_cursor.execute("INSERT INTO products (id, price) VALUES (?, ?)", (codekala, siteprice))
        print(f"Inserted: id={codekala}, price: {siteprice}")

# مرحله ۴: دریافت موجودی کالا از SQL Server
sqlserver_cursor.execute("""
    SELECT CodeKala, 
           SUM(ISNULL(TededVorodi, 0)) - SUM(ISNULL(TedadOut, 0)) AS Mojoodi
    FROM GardeshKala1
    GROUP BY CodeKala
""")
stock_data = sqlserver_cursor.fetchall()

# تبدیل به دیکشنری {id: stock}
stock_by_sku = {str(row.CodeKala): int(row.Mojoodi or 0) for row in stock_data}

# مرحله ۵: بروزرسانی stock_quantity فقط برای آی‌دی‌های معتبر
for codekala, stock in stock_by_sku.items():
    if codekala not in valid_ids:
        continue

    sqlite_cursor.execute("SELECT id FROM products WHERE id = ?", (codekala,))
    row = sqlite_cursor.fetchone()

    if row:
        sqlite_cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (stock, codekala))
        print(f"Stock updated: id={codekala}, stock={stock}")
    else:
        # اگر لازم باشه آی‌دی‌های معتبر ولی غایب رو درج کنیم (معمولاً نیازی نیست)
        sqlite_cursor.execute("INSERT INTO products (id, stock_quantity) VALUES (?, ?)", (codekala, stock))
        print(f"Inserted new with stock: id={codekala}, stock={stock}")

# ذخیره تغییرات
sqlite_conn.commit()

# بستن اتصال‌ها
sqlite_conn.close()
sqlserver_conn.close()
