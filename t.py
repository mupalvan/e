import sqlite3

conn = sqlite3.connect('ehsanDBproduct.db')
cursor = conn.cursor()

# اگر لازم داری قبلی‌ها رو پاک کنی:
cursor.execute('DELETE FROM products')

cursor.execute('''
SELECT
    p.id,
    p.name,
    p.description,
    p.keyword,
    ip.price,
    p.category,
    f.stock_quantity,
    ip.productType,
    f.color,
    f.material,
    f.type,
    ip.dimensions,
    COALESCE(f.brand, p.brand) AS brand,
    f.guarantee,
    p.label
FROM product p
LEFT JOIN feature f ON p.id = f.id
LEFT JOIN infoProduct ip ON p.id = ip.id
''')

rows = cursor.fetchall()

cursor.executemany('''
INSERT INTO products (
    id, name, description, keyword, price, category,
    stock_quantity, productType, color, material, type,
    dimensions, brand, guarantee, label
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', rows)

conn.commit()
conn.close()
