import requests
from bs4 import BeautifulSoup
import json

url = "https://www.fincaraiz.com.co/proyectos-vivienda/maranta-casas-en-venta-en-serena-del-mar-cartagena/15017798"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

script = soup.find("script", type="application/ld+json")
if script:
    data = json.loads(script.string)
    lat = data.get("object", {}).get("geo", {}).get("latitude", "")
    lon = data.get("object", {}).get("geo", {}).get("longitude", "")
    print(f"lat: {lat}, lon: {lon}")
else:
    print("No JSON-LD found")