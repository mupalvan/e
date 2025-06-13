import requests
from requests.auth import HTTPBasicAuth

# کلیدهای API ووکامرس
ck = "ck_000fbb9f08fcd924776db7af5e040d179b044f75"
cs = "cs_61ec024891b4b178006ffcf3199e3ab0178b817b"

# جستجوی محصول با نام
url = "https://ehsanstore.ir/wp-json/wc/v3/products"
params = {
    "search": "کفشور استیل مدل 7000"
}

response = requests.get(url, auth=HTTPBasicAuth(ck, cs), params=params)
product_data = response.json()

print(product_data)