import json
from scrapegraphai.graphs import SmartScraperGraph
from schema import PropertyList

graph_config = {
    "llm": {
        "model": "ollama/llama3.1:8b",
        "base_url": "http://localhost:11434",
        "format": "json",
    },
    "embeddings": {
        "model": "ollama/nomic-embed-text",
        "base_url": "http://localhost:11434",
    },
    "verbose": True,
    "headless": False,  # Opens a visible browser window to bypass simple bot detection
}

smart_scraper = SmartScraperGraph(
    prompt="Extract all individual property listings from the search results. Include price, location, and rooms.",
    source="https://www.fincaraiz.com.co/finca-raiz/venta/colombia",
    schema=PropertyList,
    config=graph_config
)

print("🚀 Starting visible scrape on Finca Raíz...")
result = smart_scraper.run()
print(json.dumps(result, indent=2))