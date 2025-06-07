# pyright: reportUnusedFunction=false

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from ptt_scraper.models import Article, Comment, SearchResult, PaginationInfo


# Test data
SAMPLE_COMMENT = Comment(
    id="c1",
    content="測試留言內容",
    author="testuser",
    created_at=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    reaction_type="+1"
)

SAMPLE_ARTICLE = Article(
    id="M.1234567890.A.123",
    title="測試文章標題",
    url="https://www.ptt.cc/bbs/Test/M.1234567890.A.123.html",
    author="testauthor",
    content="測試文章內容",
    created_at=datetime(2025, 1, 15, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    comments=[SAMPLE_COMMENT]
)


@pytest.fixture
def sample_comment() -> Comment:
    """提供樣本留言的fixture"""
    return SAMPLE_COMMENT


@pytest.fixture
def sample_article() -> Article:
    """提供樣本文章的fixture"""
    return SAMPLE_ARTICLE


def describe_comment_model():
    """測試 Comment 模型"""
    
    def test_comment_creation(sample_comment: Comment):
        """測試留言建立"""
        assert sample_comment.id == "c1"
        assert sample_comment.content == "測試留言內容"
        assert sample_comment.author == "testuser"
        assert sample_comment.reaction_type == "+1"
        assert isinstance(sample_comment.created_at, datetime)
    
    def test_comment_json_serialization(sample_comment: Comment):
        """測試留言 JSON 序列化"""
        json_data = sample_comment.model_dump()
        assert json_data["id"] == "c1"
        assert json_data["content"] == "測試留言內容"
        assert json_data["author"] == "testuser"
        assert json_data["reaction_type"] == "+1"
    
    def test_comment_validation():
        """測試留言驗證"""
        # 測試有效的反應類型
        valid_comment = Comment(
            id="c2",
            content="測試",
            author="user",
            created_at=datetime.now(ZoneInfo("Asia/Taipei")),
            reaction_type="-1"
        )
        assert valid_comment.reaction_type == "-1"
        
        # 測試中性反應類型
        neutral_comment = Comment(
            id="c3",
            content="測試",
            author="user",
            created_at=datetime.now(ZoneInfo("Asia/Taipei")),
            reaction_type="0"
        )
        assert neutral_comment.reaction_type == "0"


def describe_article_model():
    """測試 Article 模型"""
    
    def test_article_creation(sample_article: Article):
        """測試文章建立"""
        assert sample_article.id == "M.1234567890.A.123"
        assert sample_article.title == "測試文章標題"
        assert sample_article.url == "https://www.ptt.cc/bbs/Test/M.1234567890.A.123.html"
        assert sample_article.author == "testauthor"
        assert sample_article.content == "測試文章內容"
        assert isinstance(sample_article.created_at, datetime)
        assert len(sample_article.comments) == 1
    
    def test_article_with_no_author():
        """測試沒有作者的文章"""
        article = Article(
            id="M.1234567890.A.124",
            title="匿名文章",
            url="https://www.ptt.cc/bbs/Test/M.1234567890.A.124.html",
            author=None,
            content="匿名文章內容",
            created_at=datetime.now(ZoneInfo("Asia/Taipei"))
        )
        assert article.author is None
        assert len(article.comments) == 0
    
    def test_article_json_serialization(sample_article: Article):
        """測試文章 JSON 序列化"""
        json_data = sample_article.model_dump()
        assert json_data["id"] == "M.1234567890.A.123"
        assert json_data["title"] == "測試文章標題"
        assert json_data["author"] == "testauthor"
        assert len(json_data["comments"]) == 1
    
    def test_article_comments_relationship(sample_article: Article):
        """測試文章與留言的關係"""
        assert len(sample_article.comments) == 1
        first_comment = sample_article.comments[0]
        assert isinstance(first_comment, Comment)
        assert first_comment.content == "測試留言內容"


def describe_search_result_model():
    """測試 SearchResult 模型"""
    
    def test_search_result_creation():
        """測試搜尋結果建立"""
        result = SearchResult(
            id="M.1234567890.A.125",
            title="搜尋結果標題",
            url="https://www.ptt.cc/bbs/Test/M.1234567890.A.125.html",
            created_at=datetime(2025, 1, 15, 14, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        )
        assert result.id == "M.1234567890.A.125"
        assert result.title == "搜尋結果標題"
        assert "Test" in result.url
        assert isinstance(result.created_at, datetime)


def describe_pagination_info_model():
    """測試 PaginationInfo 模型"""
    
    def test_pagination_info_creation():
        """測試分頁資訊建立"""
        pagination = PaginationInfo(
            current_page=1,
            has_next=True,
            has_previous=False,
            next_page_url="https://www.ptt.cc/bbs/Test/search?q=test&p=2",
            previous_page_url=None,
            total_results=25
        )
        assert pagination.current_page == 1
        assert pagination.has_next is True
        assert pagination.has_previous is False
        assert pagination.next_page_url is not None
        assert pagination.previous_page_url is None
        assert pagination.total_results == 25
    
    def test_pagination_info_last_page():
        """測試最後一頁的分頁資訊"""
        pagination = PaginationInfo(
            current_page=5,
            has_next=False,
            has_previous=True,
            next_page_url=None,
            previous_page_url="https://www.ptt.cc/bbs/Test/search?q=test&p=4",
            total_results=100
        )
        assert pagination.current_page == 5
        assert pagination.has_next is False
        assert pagination.has_previous is True
        assert pagination.next_page_url is None
        assert pagination.previous_page_url is not None


@pytest.mark.parametrize("reaction_type,expected", [
    ("+1", "+1"),
    ("-1", "-1"), 
    ("0", "0"),
])
def test_comment_reaction_types(reaction_type: str, expected: str):
    """測試留言反應類型參數化"""
    comment = Comment(
        id="test",
        content="test content",
        author="test_user",
        created_at=datetime.now(ZoneInfo("Asia/Taipei")),
        reaction_type=reaction_type
    )
    assert comment.reaction_type == expected


@pytest.mark.parametrize("field_name", ["id", "title", "url", "content", "created_at", "comments"])
def test_article_has_required_fields(sample_article: Article, field_name: str):
    """測試文章必要欄位參數化"""
    assert hasattr(sample_article, field_name)
    assert getattr(sample_article, field_name) is not None


@pytest.mark.parametrize("field_name", ["id", "content", "author", "created_at", "reaction_type"])
def test_comment_has_required_fields(sample_comment: Comment, field_name: str):
    """測試留言必要欄位參數化"""
    assert hasattr(sample_comment, field_name)
    assert getattr(sample_comment, field_name) is not None 