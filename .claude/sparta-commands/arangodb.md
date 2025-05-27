# ArangoDB Slash Commands

This file contains useful slash commands for the ArangoDB Memory Bank project - a sophisticated memory and knowledge management system for AI agents.

## Setup & Configuration

/arango-setup
Description: Initialize ArangoDB connection and create necessary collections
Arguments: None
```bash
# Set up environment variables (if not already set)
export ARANGO_HOST=localhost
export ARANGO_PORT=8529
export ARANGO_USERNAME=root
export ARANGO_PASSWORD=your_password
export ARANGO_DB=memory_bank

# Run setup script
python scripts/setup_database.py
```

/arango-docker
Description: Start ArangoDB using Docker Compose
Arguments: None
```bash
docker-compose up -d arangodb
# Wait for ArangoDB to be ready
sleep 10
# Access web UI at http://localhost:8529
```

/arango-test-connection
Description: Test ArangoDB connection
Arguments: None
```bash
python -c "
from arangodb.core.database import ArangoDBManager
db = ArangoDBManager()
print('✅ Connected to ArangoDB' if db.client else '❌ Connection failed')
"
```

## Memory Management

/arango-memory-store [conversation_file]
Description: Store a conversation in memory
Arguments: 
  - conversation_file: Path to JSON file containing conversation
```bash
arangodb-cli memory store --file [conversation_file]
# or with metadata
arangodb-cli memory store --file [conversation_file] --user "user123" --session "session456"
```

/arango-memory-list
Description: List recent conversations in memory
Arguments: None
```bash
arangodb-cli memory list --limit 10
# or filter by user
arangodb-cli memory list --user "user123" --limit 10
```

/arango-memory-get [memory_id]
Description: Retrieve a specific memory by ID
Arguments:
  - memory_id: The ID of the memory to retrieve
```bash
arangodb-cli memory get [memory_id]
```

/arango-memory-compact [conversation_id]
Description: Create a compact summary of a long conversation
Arguments:
  - conversation_id: ID of the conversation to compact
```bash
arangodb-cli compaction compact --conversation-id [conversation_id]
# or compact all conversations over a certain length
arangodb-cli compaction compact-all --min-messages 50
```

## Search Operations

/arango-search-bm25 "[query]"
Description: Full-text search using BM25 algorithm
Arguments:
  - query: Search query text
```bash
arangodb-cli search bm25 --query "[query]" --limit 10
# with specific collections
arangodb-cli search bm25 --query "[query]" --collections memories entities --limit 10
```

/arango-search-semantic "[query]"
Description: Semantic search using vector embeddings
Arguments:
  - query: Search query text
```bash
arangodb-cli search semantic --query "[query]" --limit 10
# with similarity threshold
arangodb-cli search semantic --query "[query]" --threshold 0.8 --limit 10
```

/arango-search-hybrid "[query]"
Description: Hybrid search combining multiple algorithms with reranking
Arguments:
  - query: Search query text
```bash
arangodb-cli search hybrid --query "[query]" --limit 10
# with custom weights
arangodb-cli search hybrid --query "[query]" --bm25-weight 0.3 --semantic-weight 0.7 --limit 10
```

/arango-search-graph [start_id]
Description: Graph traversal search from a starting node
Arguments:
  - start_id: Starting node ID
```bash
arangodb-cli search graph --start-id [start_id] --depth 3
# with direction control
arangodb-cli search graph --start-id [start_id] --depth 3 --direction outbound
```

/arango-search-tag "[tags]"
Description: Search by tags
Arguments:
  - tags: Comma-separated list of tags
```bash
arangodb-cli search tag --tags "[tags]" --limit 10
# example
arangodb-cli search tag --tags "python,tutorial,beginner" --limit 10
```

## Entity & Relationship Management

/arango-entity-extract "[text]"
Description: Extract entities from text using NLP
Arguments:
  - text: Text to extract entities from
```bash
arangodb-cli memory extract-entities --text "[text]"
# or from file
arangodb-cli memory extract-entities --file document.txt
```

/arango-relationship-create [from_id] [to_id] [type]
Description: Create a relationship between two documents
Arguments:
  - from_id: Source document ID
  - to_id: Target document ID
  - type: Relationship type (e.g., "references", "contradicts", "supports")
```bash
arangodb-cli graph create-relationship --from [from_id] --to [to_id] --type [type]
# with properties
arangodb-cli graph create-relationship --from [from_id] --to [to_id] --type [type] --properties '{"confidence": 0.9}'
```

/arango-relationship-list [document_id]
Description: List all relationships for a document
Arguments:
  - document_id: Document ID to check relationships for
```bash
arangodb-cli graph list-relationships --document [document_id]
# with direction filter
arangodb-cli graph list-relationships --document [document_id] --direction inbound
```

## Visualization

/arango-graph-viz [output_file]
Description: Generate an interactive D3.js graph visualization
Arguments:
  - output_file: Output HTML file path
```bash
arangodb-cli visualize create --output [output_file]
# with specific layout
arangodb-cli visualize create --output [output_file] --layout force --width 1200 --height 800
```

/arango-graph-viz-recommend "[description]"
Description: Get LLM-powered visualization recommendations
Arguments:
  - description: Description of what you want to visualize
```bash
arangodb-cli visualize recommend --description "[description]"
# example
arangodb-cli visualize recommend --description "Show the relationship between AI concepts and their implementations"
```

/arango-graph-serve [viz_file]
Description: Serve a visualization file locally
Arguments:
  - viz_file: Path to the HTML visualization file
```bash
cd $(dirname [viz_file]) && python -m http.server 8000
# Then open http://localhost:8000/$(basename [viz_file])
```

## Community Detection

/arango-community-detect
Description: Detect communities in the entity graph using Louvain algorithm
Arguments: None
```bash
arangodb-cli community detect
# with resolution parameter
arangodb-cli community detect --resolution 1.5
```

/arango-community-list
Description: List all detected communities
Arguments: None
```bash
arangodb-cli community list
# with minimum size filter
arangodb-cli community list --min-size 5
```

/arango-community-members [community_id]
Description: List members of a specific community
Arguments:
  - community_id: Community ID
```bash
arangodb-cli community members --id [community_id]
```

## Temporal Operations

/arango-temporal-query "[query]" [date]
Description: Query memories at a specific point in time
Arguments:
  - query: Search query
  - date: Date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
```bash
arangodb-cli temporal search --query "[query]" --as-of [date]
# example
arangodb-cli temporal search --query "python tutorial" --as-of "2024-01-01"
```

/arango-temporal-history [document_id]
Description: View the history of changes for a document
Arguments:
  - document_id: Document ID
```bash
arangodb-cli temporal history --document [document_id]
# with date range
arangodb-cli temporal history --document [document_id] --from "2024-01-01" --to "2024-12-31"
```

## Q&A Generation

/arango-qa-generate [document_id]
Description: Generate Q&A pairs from a document for LLM fine-tuning
Arguments:
  - document_id: Document ID to generate Q&A from
```bash
arangodb-cli qa generate --document [document_id] --output qa_pairs.json
# with specific model
arangodb-cli qa generate --document [document_id] --model gpt-4 --output qa_pairs.json
```

/arango-qa-export [format]
Description: Export Q&A pairs in various formats
Arguments:
  - format: Export format (json, csv, parquet, alpaca, sharegpt)
```bash
arangodb-cli qa export --format [format] --output training_data.[format]
# with filtering
arangodb-cli qa export --format alpaca --min-quality 0.8 --output training_data.json
```

## Testing & Development

/arango-test
Description: Run the ArangoDB test suite
Arguments: None
```bash
pytest tests/ -v
# or specific test category
pytest tests/test_search.py -v
```

/arango-test-integration
Description: Run integration tests with real ArangoDB
Arguments: None
```bash
pytest tests/integration/ -v --integration
# with coverage
pytest tests/integration/ -v --integration --cov=src/arangodb --cov-report=html
```

/arango-mcp-server
Description: Start the MCP (Model Context Protocol) server
Arguments: None
```bash
python -m arangodb.mcp.server
# or with custom port
python -m arangodb.mcp.server --port 8080
```

## Pipeline Integration

/arango-sparta-integrate
Description: Process SPARTA downloaded files and store in ArangoDB
Arguments: None
```bash
# Assuming SPARTA has downloaded files
python -c "
from arangodb.cli.main import app
from typer.testing import CliRunner
import json

runner = CliRunner()

# Load SPARTA results
with open('sparta_enhanced_download/download_results.json', 'r') as f:
    sparta_results = json.load(f)

# Process each downloaded file
for url in sparta_results.get('downloaded_urls', []):
    result = runner.invoke(app, ['memory', 'store', '--url', url])
    print(f'Processed: {url}')
"
```

/arango-marker-integrate
Description: Process Marker-extracted content and create knowledge graph
Arguments: None
```bash
# Process Marker output and create relationships
python scripts/marker_integration.py --marker-output marker_results.json
```

/arango-report
Description: Generate an ArangoDB usage report
Arguments: None
```bash
python -c "
from src.sparta.reports.universal_report_generator import UniversalReportGenerator
from arangodb.core.database import ArangoDBManager
import json

# Get statistics
db = ArangoDBManager()
stats = {
    'memories': db.get_collection_count('memories'),
    'entities': db.get_collection_count('entities'),
    'relationships': db.get_collection_count('relationships'),
    'communities': db.get_collection_count('communities')
}

# Generate report
generator = UniversalReportGenerator(
    title='ArangoDB Memory Bank Report',
    theme_color='#ef4444',
    logo='🕸️'
)
report_file = generator.generate([stats], 'arangodb_report.html')
print(f'Report: {report_file}')
"
```

## Utility Commands

/arango-backup [backup_dir]
Description: Backup ArangoDB database
Arguments:
  - backup_dir: Directory to store backup
```bash
arangodump --server.database memory_bank --output-directory [backup_dir]
```

/arango-restore [backup_dir]
Description: Restore ArangoDB database from backup
Arguments:
  - backup_dir: Directory containing backup
```bash
arangorestore --server.database memory_bank --input-directory [backup_dir]
```

/arango-clear-cache
Description: Clear various caches (embeddings, search results)
Arguments: None
```bash
python -c "
from arangodb.core.database import ArangoDBManager
db = ArangoDBManager()
db.clear_cache('embeddings')
db.clear_cache('search_results')
print('✅ Caches cleared')
"
```

/arango-stats
Description: Display database statistics
Arguments: None
```bash
arangodb-cli crud stats --format table
# or as JSON
arangodb-cli crud stats --format json
```

---

## Common Workflows

### 1. Store and Search Workflow
```bash
# Store a conversation
/arango-memory-store conversation.json

# Search for related content
/arango-search-hybrid "machine learning concepts"

# Create relationships
/arango-relationship-create memory_123 entity_456 "references"

# Visualize the knowledge graph
/arango-graph-viz knowledge_graph.html
```

### 2. Q&A Generation Workflow
```bash
# Extract entities from documents
/arango-entity-extract "Your document text here"

# Generate Q&A pairs
/arango-qa-generate document_123

# Export for fine-tuning
/arango-qa-export alpaca
```

### 3. Temporal Analysis Workflow
```bash
# Query historical data
/arango-temporal-query "python tutorials" "2024-01-01"

# View document history
/arango-temporal-history document_123

# Detect changes over time
/arango-temporal-diff document_123 "2024-01-01" "2024-06-01"
```