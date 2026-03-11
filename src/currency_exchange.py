import requests

def get_exchange_rate(from_currency: str, to_currency: str = "USD") -> float:
    response = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}")
    return response.json()["rates"][to_currency]

COP_TO_USD = get_exchange_rate("COP")
print(COP_TO_USD)