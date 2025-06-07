#!/usr/bin/env python3
"""
PTT Scraper - Example Usage

This script demonstrates how to use the PTT scraper programmatically
with the new OOP structure.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ptt_scraper import PTTCrawler, DatabaseManager


async def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Create a crawler with custom settings
    async with PTTCrawler("example.db", cutoff_days=3) as crawler:
        # Crawl a small number of articles for demonstration
        count = await crawler.crawl_board("Test", "測試", max_articles=5)
        print(f"✅ Processed {count} articles")
        
        # Get statistics
        stats = crawler.get_stats()
        print(f"📊 Database stats: {stats}")


async def example_database_operations():
    """Database operations example"""
    print("\n=== Database Operations Example ===")
    
    db = DatabaseManager("example.db")
    try:
        # Search for articles
        articles = db.search_articles("測試")
        print(f"🔍 Found {len(articles)} articles containing '測試'")
        
        # Get all articles with pagination
        recent_articles = db.get_all_articles(limit=3)
        print(f"📄 Recent articles (limit 3): {len(recent_articles)}")
        
        for article in recent_articles:
            print(f"  - {article.title} by {article.author}")
            print(f"    Comments: {len(article.comments)}")
        
        # Get database statistics
        stats = db.get_database_stats()
        print(f"📊 Total articles: {stats.total_articles}")
        print(f"📊 Total comments: {stats.total_comments}")
        print(f"📊 Database size: {stats.database_size_mb} MB")
        
    finally:
        db.close()


async def example_single_article():
    """Single article scraping example"""
    print("\n=== Single Article Example ===")
    
    # Example PTT article URL (replace with a real one for testing)
    test_url = "https://www.ptt.cc/bbs/Test/M.1234567890.A.123.html"
    
    async with PTTCrawler("example.db") as crawler:
        article = await crawler.scrape_article(test_url)
        
        if article:
            print(f"📄 Title: {article.title}")
            print(f"👤 Author: {article.author}")
            print(f"📅 Created: {article.created_at}")
            print(f"💬 Comments: {len(article.comments)}")
            print(f"📝 Content preview: {article.content[:100]}...")
        else:
            print("❌ Failed to scrape article (URL might not exist)")


def example_model_usage():
    """Pydantic models usage example"""
    print("\n=== Models Usage Example ===")
    
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from ptt_scraper.models import Article, Comment
    
    # Create a comment
    comment = Comment(
        id="c1",
        content="這是一個測試留言",
        author="test_user",
        created_at=datetime.now(ZoneInfo("Asia/Taipei")),
        reaction_type="+1"
    )
    
    # Create an article
    article = Article(
        id="M.1234567890.A.123",
        title="測試文章",
        url="https://www.ptt.cc/bbs/Test/M.1234567890.A.123.html",
        author="test_author",
        content="這是測試文章的內容",
        created_at=datetime.now(ZoneInfo("Asia/Taipei")),
        comments=[comment]
    )
    
    # Serialize to JSON
    article_json = article.model_dump()
    print(f"📄 Article JSON keys: {list(article_json.keys())}")
    print(f"💬 First comment: {article.comments[0].content}")
    print(f"👍 Reaction type: {article.comments[0].reaction_type}")


async def main():
    """Main example function"""
    print("🚀 PTT Scraper Examples")
    print("=" * 50)
    
    # Run model example (synchronous)
    example_model_usage()
    
    # Run async examples
    try:
        # Note: These examples use "Test" board which might not exist
        # Replace with real board names for actual testing
        await example_basic_usage()
        await example_database_operations()
        await example_single_article()
        
    except Exception as e:
        print(f"❌ Error during examples: {e}")
        print("💡 This is expected if using example URLs that don't exist")
    
    print("\n✅ Examples completed!")
    print("💡 To run with real data, modify the board names and URLs in this script")


if __name__ == "__main__":
    asyncio.run(main()) 