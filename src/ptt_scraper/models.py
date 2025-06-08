from pydantic import BaseModel, Field
from datetime import datetime


class Comment(BaseModel):
    """PTT 文章的留言模型"""

    floor: int = Field(description="留言樓層")
    content: str = Field(description="留言內容")
    author: str = Field(description="留言作者")
    created_at: datetime = Field(description="留言時間")
    reaction_type: str = Field(description="反應類型 (+1, -1, 0)")


class Article(BaseModel):
    """PTT 文章模型"""

    id: str = Field(description="文章ID")
    title: str = Field(description="文章標題")
    url: str = Field(description="文章URL")
    author: str | None = Field(default=None, description="文章作者")
    content: str = Field(description="文章內容")
    created_at: datetime = Field(description="文章時間")
    comments: list[Comment] = Field(default_factory=list, description="文章留言")


class SearchResult(BaseModel):
    """PTT 搜尋結果項目"""
    
    id: str = Field(description="文章ID")
    title: str = Field(description="文章標題")
    url: str = Field(description="文章URL")
    created_at: datetime = Field(description="文章時間")


class PaginationInfo(BaseModel):
    """分頁資訊模型"""
    
    current_page: int = Field(description="目前頁數")
    has_next: bool = Field(description="是否有下一頁")
    has_previous: bool = Field(description="是否有上一頁")
    next_page_url: str | None = Field(description="下一頁URL")
    previous_page_url: str | None = Field(description="上一頁URL")
    total_results: int = Field(description="總結果數")


# Output models for JSON serialization
class MetadataOutput(BaseModel):
    """輸出 JSON 的元數據模型"""
    scraped_at: datetime = Field(description="抓取時間")
    total_comments: int = Field(description="留言總數")
    board: str = Field(description="看板名稱")
    keyword: str = Field(description="搜尋關鍵字")
    scraper_version: str = Field(description="爬蟲版本")


class ArticleOutput(BaseModel):
    """輸出 JSON 的文章模型"""
    id: str = Field(description="文章ID")
    title: str = Field(description="文章標題")
    url: str = Field(description="文章URL")
    author: str | None = Field(default=None, description="文章作者")
    content: str = Field(description="文章內容")
    created_at: datetime = Field(description="文章時間")


class CommentOutput(BaseModel):
    """輸出 JSON 的留言模型"""
    floor: int = Field(description="留言樓層")
    content: str = Field(description="留言內容")
    author: str = Field(description="留言作者")
    created_at: datetime = Field(description="留言時間")
    reaction_type: str = Field(description="反應類型")


class ArticleExport(BaseModel):
    """完整的文章輸出模型"""
    metadata: MetadataOutput = Field(description="元數據")
    article: ArticleOutput = Field(description="文章資料")
    comments: list[CommentOutput] = Field(description="留言列表") 