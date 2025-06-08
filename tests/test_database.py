# pyright: reportUnusedFunction=false

import pytest
import tempfile
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from ptt_scraper.database import DatabaseManager
from ptt_scraper.models import Article, Comment


@pytest.fixture
def temp_db():
    """提供臨時資料庫的fixture"""
    # 創建臨時資料庫檔案
    temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_file.close()
    
    db_manager = DatabaseManager(temp_file.name)
    
    yield db_manager
    
    # 清理
    db_manager.close()
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def sample_article():
    """提供樣本文章的fixture"""
    return Article(
        id="M.1234567890.A.123",
        title="測試文章標題",
        url="https://www.ptt.cc/bbs/Test/M.1234567890.A.123.html",
        author="testauthor",
        content="測試文章內容",
        created_at=datetime(2025, 1, 15, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")),
                    comments=[
                Comment(
                    floor=2,
                    content="測試留言1",
                    author="user1",
                    created_at=datetime(2025, 1, 15, 11, 0, tzinfo=ZoneInfo("Asia/Taipei")),
                    reaction_type="+1"
                ),
                Comment(
                    floor=3,
                    content="測試留言2",
                    author="user2",
                    created_at=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("Asia/Taipei")),
                    reaction_type="-1"
                )
        ]
    )


def describe_database_manager():
    """測試 DatabaseManager 類別"""
    
    def test_database_initialization(temp_db: DatabaseManager):
        """測試資料庫初始化"""
        assert temp_db is not None
        assert temp_db.db_path.endswith('.db')
        
        # 檢查資料表是否被創建
        stats = temp_db.get_database_stats()
        assert stats.total_articles == 0
        assert stats.total_comments == 0
    
    def test_save_article(temp_db: DatabaseManager, sample_article: Article):
        """測試儲存文章"""
        article_id = temp_db.save_article(sample_article)
        assert isinstance(article_id, int)
        assert article_id > 0
        
        # 檢查統計資訊
        stats = temp_db.get_database_stats()
        assert stats.total_articles == 1
        assert stats.total_comments == 2
    
    def test_get_article_by_ptt_id(temp_db: DatabaseManager, sample_article: Article):
        """測試根據 PTT ID 取得文章"""
        # 先儲存文章
        _ = temp_db.save_article(sample_article)
        
        # 取得文章
        retrieved_article = temp_db.get_article_by_ptt_id(sample_article.id)
        assert retrieved_article is not None
        assert retrieved_article.id == sample_article.id
        assert retrieved_article.title == sample_article.title
        assert retrieved_article.author == sample_article.author
        assert len(retrieved_article.comments) == 2
    
    def test_get_article_by_url(temp_db: DatabaseManager, sample_article: Article):
        """測試根據 URL 取得文章"""
        # 先儲存文章
        _ = temp_db.save_article(sample_article)
        
        # 取得文章
        retrieved_article = temp_db.get_article_by_url(sample_article.url)
        assert retrieved_article is not None
        assert retrieved_article.url == sample_article.url
        assert retrieved_article.title == sample_article.title
    
    def test_duplicate_article_handling(temp_db: DatabaseManager, sample_article: Article):
        """測試重複文章處理"""
        # 第一次儲存
        article_id1 = temp_db.save_article(sample_article)
        
        # 修改文章內容後再次儲存
        sample_article.content = "更新後的文章內容"
        article_id2 = temp_db.save_article(sample_article)
        
        # 應該是同一篇文章被更新
        assert article_id1 == article_id2
        
        # 檢查內容是否被更新
        retrieved_article = temp_db.get_article_by_ptt_id(sample_article.id)
        assert retrieved_article is not None
        assert retrieved_article.content == "更新後的文章內容"
        
        # 文章數量應該還是 1
        stats = temp_db.get_database_stats()
        assert stats.total_articles == 1
    
    def test_search_articles(temp_db: DatabaseManager, sample_article: Article):
        """測試搜尋文章"""
        # 儲存文章
        _ = temp_db.save_article(sample_article)
        
        # 搜尋標題
        results = temp_db.search_articles("測試")
        assert len(results) == 1
        assert results[0].title == sample_article.title
        
        # 搜尋內容
        results = temp_db.search_articles("內容")
        assert len(results) == 1
        
        # 搜尋不存在的關鍵字
        results = temp_db.search_articles("不存在的關鍵字")
        assert len(results) == 0
    
    def test_get_articles_by_author(temp_db: DatabaseManager):
        """測試根據作者取得文章"""
        # 創建多篇不同作者的文章
        article1 = Article(
            id="M.1111111111.A.111",
            title="作者1的文章",
            url="https://www.ptt.cc/bbs/Test/M.1111111111.A.111.html",
            author="author1",
            content="作者1的內容",
            created_at=datetime.now(ZoneInfo("Asia/Taipei"))
        )
        
        article2 = Article(
            id="M.2222222222.A.222",
            title="作者2的文章",
            url="https://www.ptt.cc/bbs/Test/M.2222222222.A.222.html",
            author="author2",
            content="作者2的內容",
            created_at=datetime.now(ZoneInfo("Asia/Taipei"))
        )
        
        # 儲存文章
        _ = temp_db.save_article(article1)
        _ = temp_db.save_article(article2)
        
        # 搜尋特定作者的文章
        author1_articles = temp_db.get_articles_by_author("author1")
        assert len(author1_articles) == 1
        assert author1_articles[0].author == "author1"
        
        author2_articles = temp_db.get_articles_by_author("author2")
        assert len(author2_articles) == 1
        assert author2_articles[0].author == "author2"
    
    def test_delete_article(temp_db: DatabaseManager, sample_article: Article):
        """測試刪除文章"""
        # 先儲存文章
        article_id = temp_db.save_article(sample_article)
        
        # 確認文章存在
        stats_before = temp_db.get_database_stats()
        assert stats_before.total_articles == 1
        assert stats_before.total_comments == 2
        
        # 刪除文章
        deleted = temp_db.delete_article(article_id)
        assert deleted is True
        
        # 確認文章和留言都被刪除
        stats_after = temp_db.get_database_stats()
        assert stats_after.total_articles == 0
        assert stats_after.total_comments == 0
        
        # 嘗試刪除不存在的文章
        deleted_again = temp_db.delete_article(article_id)
        assert deleted_again is False
    
    def test_get_all_articles_pagination(temp_db: DatabaseManager):
        """測試分頁取得所有文章"""
        # 創建多篇文章
        for i in range(5):
            article = Article(
                id=f"M.{i}{i}{i}{i}{i}{i}{i}{i}{i}{i}.A.{i}{i}{i}",
                title=f"測試文章{i}",
                url=f"https://www.ptt.cc/bbs/Test/M.{i}{i}{i}{i}{i}{i}{i}{i}{i}{i}.A.{i}{i}{i}.html",
                author=f"author{i}",
                content=f"測試內容{i}",
                created_at=datetime.now(ZoneInfo("Asia/Taipei"))
            )
            _ = temp_db.save_article(article)
        
        # 取得所有文章
        all_articles = temp_db.get_all_articles()
        assert len(all_articles) == 5
        
        # 測試分頁
        page1 = temp_db.get_all_articles(limit=2, offset=0)
        assert len(page1) == 2
        
        page2 = temp_db.get_all_articles(limit=2, offset=2)
        assert len(page2) == 2
        
        page3 = temp_db.get_all_articles(limit=2, offset=4)
        assert len(page3) == 1


def describe_database_edge_cases():
    """測試資料庫邊緣情況"""
    
    def test_get_nonexistent_article(temp_db: DatabaseManager):
        """測試取得不存在的文章"""
        article = temp_db.get_article_by_ptt_id("NONEXISTENT")
        assert article is None
        
        article_by_url = temp_db.get_article_by_url("https://nonexistent.url")
        assert article_by_url is None
    
    def test_empty_database_stats(temp_db: DatabaseManager):
        """測試空資料庫的統計資訊"""
        stats = temp_db.get_database_stats()
        assert stats.total_articles == 0
        assert stats.total_comments == 0
        assert stats.database_size_mb >= 0


@pytest.mark.parametrize("article_count", [1, 5, 10])
def test_multiple_articles_storage(temp_db: DatabaseManager, article_count: int):
    """測試儲存多篇文章參數化"""
    for i in range(article_count):
        article = Article(
            id=f"M.{i:10d}.A.{i:03d}",
            title=f"測試文章{i}",
            url=f"https://www.ptt.cc/bbs/Test/M.{i:10d}.A.{i:03d}.html",
            author=f"author{i}",
            content=f"測試內容{i}",
            created_at=datetime.now(ZoneInfo("Asia/Taipei"))
        )
        _ = temp_db.save_article(article)
    
    stats = temp_db.get_database_stats()
    assert stats.total_articles == article_count 