# PTT Scraper

A Python package for scraping PTT (Taiwan bulletin board system) articles and comments with OOP structure, SQLite storage, and comprehensive testing.

## Features

- **Object-Oriented Design**: Clean separation of concerns with dedicated classes for scraping, database operations, and crawling
- **Pydantic Models**: Type-safe data structures with validation
- **SQLite Database**: Persistent storage with SQLAlchemy ORM
- **Async/Await Support**: Efficient concurrent scraping
- **Comprehensive Testing**: pytest-based test suite with fixtures
- **Command Line Interface**: Easy-to-use CLI with multiple options

## Installation

```bash
# Install dependencies
uv sync

# Or with pip
pip install -e .
```

## Quick Start

### Command Line Usage

```bash
# Basic usage
python -m ptt_scraper.main --board Gossiping --keyword 政治

# With options
python -m ptt_scraper.main --board TechJob --keyword 軟體工程師 --max-articles 50 --cutoff-days 7

# Show database statistics
python -m ptt_scraper.main --stats

# Interactive mode (legacy)
python main.py
```

### Programmatic Usage

```python
import asyncio
from ptt_scraper import PTTCrawler, DatabaseManager

async def main():
    # Using the crawler
    async with PTTCrawler("my_database.db", cutoff_days=7) as crawler:
        count = await crawler.crawl_board("Gossiping", "政治", max_articles=10)
        print(f"Processed {count} articles")
    
    # Using the database
    db = DatabaseManager("my_database.db")
    try:
        articles = db.search_articles("政治")
        print(f"Found {len(articles)} articles about 政治")
        
        stats = db.get_database_stats()
        print(f"Total articles: {stats['total_articles']}")
        print(f"Total comments: {stats['total_comments']}")
    finally:
        db.close()

asyncio.run(main())
```

## Project Structure

```
ptt-scraper/
├── src/ptt_scraper/           # Main package
│   ├── __init__.py           # Package exports
│   ├── models.py             # Pydantic data models
│   ├── database.py           # SQLAlchemy database operations
│   ├── scrapers.py           # HTML parsing classes
│   ├── crawler.py            # Main crawler orchestration
│   └── main.py               # CLI entry point
├── tests/                    # Test suite
│   ├── test_models.py        # Model tests
│   ├── test_database.py      # Database tests
│   └── test_scrapers.py      # Scraper tests (to be added)
├── main.py                   # Legacy entry point
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## Architecture

### Models (`models.py`)

- **Article**: Represents a PTT article with metadata and comments
- **Comment**: Represents a comment/push with reaction type
- **SearchResult**: Lightweight article representation for search results
- **PaginationInfo**: Pagination metadata for search results

### Database (`database.py`)

- **DatabaseManager**: SQLAlchemy-based database operations
- **SqlArticle**: SQLAlchemy model for articles table
- **SqlComment**: SQLAlchemy model for comments table
- Automatic schema creation and migration
- Duplicate handling with upsert operations

### Scrapers (`scrapers.py`)

- **ArticleScraper**: Extracts article content, title, author, and metadata
- **CommentScraper**: Extracts comments/pushes with reaction types
- **PaginationScraper**: Handles PTT's pagination system
- Utility functions for date parsing and text cleaning

### Crawler (`crawler.py`)

- **PTTCrawler**: Main orchestration class
- Async context manager for resource management
- Concurrent processing with semaphore limiting
- Configurable date cutoffs and article limits

## Testing

Run the test suite:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/ptt_scraper

# Run specific test file
uv run pytest tests/test_models.py

# Run with verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "test_article"
```

### Test Structure

- **Fixtures**: Reusable test data and database instances
- **Parametrized Tests**: Testing multiple scenarios efficiently
- **Describe Blocks**: Organized test grouping with pytest-describe
- **Temporary Databases**: Isolated test environments

### Example Test

```python
def describe_article_model():
    def test_article_creation(sample_article: Article):
        assert sample_article.title == "測試文章標題"
        assert len(sample_article.comments) == 1
    
    def test_article_json_serialization(sample_article: Article):
        json_data = sample_article.model_dump()
        assert json_data["title"] == "測試文章標題"
```

## Configuration

### Command Line Options

- `--board`: PTT board name (required)
- `--keyword`: Search keyword (required)
- `--db-path`: Database file path (default: ptt_scraper.db)
- `--cutoff-days`: Only scrape articles from N days ago (default: 5)
- `--max-articles`: Maximum number of articles to process
- `--stats`: Show database statistics and exit

### Environment Variables

Currently, the scraper uses hardcoded constants. Future versions may support:

- `PTT_USER_AGENT`: Custom user agent string
- `PTT_TIMEOUT`: Request timeout in seconds
- `PTT_CONCURRENT_LIMIT`: Maximum concurrent requests

## Database Schema

### Articles Table

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ptt_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000) UNIQUE NOT NULL,
    author VARCHAR(100),
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Comments Table

```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ptt_id VARCHAR(100) NOT NULL,
    author VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    reaction_type VARCHAR(10) NOT NULL,
    created_at DATETIME NOT NULL,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    article_id INTEGER REFERENCES articles(id),
    UNIQUE(article_id, ptt_id)
);
```

## Development

### Adding New Features

1. **Models**: Add new Pydantic models in `models.py`
2. **Database**: Extend `DatabaseManager` with new operations
3. **Scrapers**: Create new scraper classes for different content types
4. **Tests**: Add comprehensive tests for new functionality

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Document classes and methods with docstrings
- Use descriptive variable names

### Dependencies

- **Core**: `pydantic`, `sqlalchemy`, `beautifulsoup4`, `httpx`
- **Development**: `pytest`, `pytest-describe`, `ruff`

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure to install the package in development mode: `pip install -e .`
2. **Database Locked**: Close any existing database connections before running tests
3. **Rate Limiting**: PTT may rate limit requests; consider adding delays between requests
4. **Encoding Issues**: PTT uses Big5 encoding; the scraper handles this automatically

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Tips

- Use `--max-articles` to limit processing during development
- Adjust the semaphore limit in `PTTCrawler` for different concurrency levels
- Consider using a faster database like PostgreSQL for large datasets

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is for educational purposes. Please respect PTT's terms of service and rate limits when using this scraper.

## Changelog

### v0.1.0
- Initial OOP restructure
- SQLAlchemy database integration
- Pydantic models
- Comprehensive test suite
- CLI interface
