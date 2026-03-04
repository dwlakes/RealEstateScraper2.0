import json
from scrapegraphai.graphs import SmartScraperGraph
from schema import PropertyList # Importing your new schema

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
}

# We pass the 'schema' argument here to FORCE the 8B model to behave
smart_scraper = SmartScraperGraph(
    prompt="Extract all individual property listings from the search results.",
    source="https://www.properstar.com/colombia/buy",
    schema=PropertyList,
    config=graph_config
)

print("Starting validated scrape...")
result = smart_scraper.run()
print(json.dumps(result, indent=2))