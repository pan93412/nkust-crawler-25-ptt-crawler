import re
from typing import final
from bs4 import BeautifulSoup, Tag
from datetime import datetime
from zoneinfo import ZoneInfo

from .models import Comment, PaginationInfo


def parse_datetime(date_str: str) -> datetime:
    """
    解析 PTT 的日期時間格式
    例如: "Sun Apr 13 14:05:20 2025"

    Args:
        date_str: 日期時間字串

    Returns:
        解析後的 datetime 物件，若解析失敗則返回當前時間
    """
    try:
        # 移除多餘空白並標準化格式
        clean_date: str = date_str.strip()
        # Sun Apr 13 14:05:20 2025
        dt = datetime.strptime(clean_date, "%a %b %d %H:%M:%S %Y")
        return dt.replace(tzinfo=ZoneInfo("Asia/Taipei"))
    except ValueError:
        # 如果解析失敗，返回當前時間
        return datetime.now().replace(tzinfo=ZoneInfo("Asia/Taipei"))


def parse_comment_time(time_str: str, article_year: int) -> datetime:
    """
    解析 PTT 留言的時間格式
    例如: "03/29 22:49"

    Args:
        time_str: 時間字串
        article_year: 文章年份

    Returns:
        解析後的 datetime 物件
    """
    try:
        clean_time: str = time_str.strip()
        # 03/29 22:49
        dt = datetime.strptime(clean_time, "%m/%d %H:%M")
        return dt.replace(year=article_year, tzinfo=ZoneInfo("Asia/Taipei"))
    except ValueError:
        return datetime.now().replace(tzinfo=ZoneInfo("Asia/Taipei"))


def clean_text(text: str | None) -> str:
    """
    清理文本內容，移除多餘的空白和換行

    Args:
        text: 要清理的文本

    Returns:
        清理後的文本
    """
    if not text:
        return ""
    # 移除多餘的空白字符和換行
    cleaned: str = re.sub(r"\s+", " ", text.strip())
    return cleaned


def tag_to_reaction_type(tag: str) -> str:
    """
    將 PTT 推噓標籤轉換為反應類型
    
    Args:
        tag: PTT 標籤 (推, 噓, →)
        
    Returns:
        反應類型 (+1, -1, 0)
    """
    if tag == '推':
        return '+1'
    elif tag == '噓':
        return '-1'
    return '0'


@final
class ArticleScraper:
    """PTT 文章爬蟲類"""
    
    def __init__(self, html_content: str):
        """
        初始化文章爬蟲

        Args:
            html_content: HTML 內容字符串
        """
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.main_content = self.soup.find('div', id='main-content')

    def extract_title(self) -> str:
        """
        擷取文章標題

        Returns:
            文章標題
        """
        # Find title in meta-line
        meta_title = self.soup.find('span', class_='article-meta-tag', string='標題')
        if meta_title and isinstance(meta_title, Tag):
            parent = meta_title.parent
            assert isinstance(parent, Tag)
            title_value = parent.find('span', class_='article-meta-value')
            if title_value and isinstance(title_value, Tag):
                return clean_text(title_value.get_text())
        return "無標題"

    def extract_author(self) -> str | None:
        """
        擷取文章作者

        Returns:
            文章作者或None
        """
        meta_author = self.soup.find('span', class_='article-meta-tag', string='作者')
        if meta_author and isinstance(meta_author, Tag):
            parent = meta_author.parent
            assert isinstance(parent, Tag)
            author_value = parent.find('span', class_='article-meta-value')
            if author_value and isinstance(author_value, Tag):
                # 作者格式通常是 "username (nickname)"
                author_text = clean_text(author_value.get_text())
                # 提取括號前的用戶名
                match = re.match(r'^([^\s(]+)', author_text)
                if match:
                    return match.group(1)
                return author_text
        return None

    def extract_datetime(self) -> datetime:
        """
        擷取文章時間

        Returns:
            文章時間
        """
        meta_time = self.soup.find('span', class_='article-meta-tag', string='時間')
        if meta_time and isinstance(meta_time, Tag):
            parent = meta_time.parent
            assert isinstance(parent, Tag)
            time_value = parent.find('span', class_='article-meta-value')
            if time_value and isinstance(time_value, Tag):
                time_str = clean_text(time_value.get_text())
                return parse_datetime(time_str)
        return datetime.now().replace(tzinfo=ZoneInfo("Asia/Taipei"))

    def extract_content(self) -> str:
        """
        擷取文章內容

        Returns:
            文章內容
        """
        if not self.main_content or not isinstance(self.main_content, Tag):
            return ""
        
        # 複製主要內容以避免修改原始DOM
        content_copy = BeautifulSoup(str(self.main_content), 'html.parser')
        main_content = content_copy.find('div', id='main-content')
        
        if not main_content:
            return ""
        
        # 移除元數據和推文
        assert isinstance(main_content, Tag)

        for tag in main_content.select('div.article-metaline') + \
                   main_content.select('div.article-metaline-right') + \
                   main_content.select('div.push'):
            tag.decompose()
        
        return clean_text(main_content.get_text())

    def get_soup(self) -> BeautifulSoup:
        """
        獲取內部的 BeautifulSoup 物件

        Returns:
            BeautifulSoup 物件
        """
        return self.soup


class CommentScraper:
    """PTT 留言爬蟲類"""

    def extract_comments(self, soup: BeautifulSoup, article_year: int) -> list[Comment]:
        """
        從 BeautifulSoup 物件中擷取所有留言

        Args:
            soup: BeautifulSoup 物件
            article_year: 文章年份

        Returns:
            留言列表
        """
        comments: list[Comment] = []
        
        # 找到所有推文
        pushes = soup.select('div.push')
        
        for i, push in enumerate(pushes):
            comment = self.extract_single_comment(push, i, article_year)
            if comment:
                comments.append(comment)

        return comments

    def extract_single_comment(self, push_element: Tag, index: int, article_year: int) -> Comment | None:
        """
        從單個推文元素中擷取一個留言

        Args:
            push_element: 推文元素
            index: 留言索引
            article_year: 文章年份

        Returns:
            Comment 物件或 None
        """
        try:
            # 提取推噓標籤
            tag_element = push_element.select_one('span.push-tag')
            tag = clean_text(tag_element.get_text()) if tag_element else ''
            
            # 提取作者
            user_element = push_element.select_one('span.push-userid')
            author = clean_text(user_element.get_text()) if user_element else ''
            
            # 提取內容
            content_element = push_element.select_one('span.push-content')
            content = clean_text(content_element.get_text()) if content_element else ''
            # 移除開頭的冒號
            content = content.lstrip(': ')
            
            # 提取時間
            time_element = push_element.select_one('span.push-ipdatetime')
            if time_element:
                time_text = clean_text(time_element.get_text())
                # 時間格式: "111.240.96.24 03/29 22:49"
                parts = time_text.split(' ', 1)
                if len(parts) >= 2:
                    time_str = parts[1]  # "03/29 22:49"
                    created_at = parse_comment_time(time_str, article_year)
                else:
                    created_at = datetime.now().replace(tzinfo=ZoneInfo("Asia/Taipei"))
            else:
                created_at = datetime.now().replace(tzinfo=ZoneInfo("Asia/Taipei"))
            
            # 轉換反應類型
            reaction_type = tag_to_reaction_type(tag)
            
            return Comment(
                floor=index + 2,  # PTT樓層從2樓開始（1樓是原文）
                content=content,
                author=author,
                created_at=created_at,
                reaction_type=reaction_type
            )
        except Exception:
            return None


@final
class PaginationScraper:
    """PTT 分頁爬蟲類"""
    
    def __init__(self, html_content: str):
        """
        初始化分頁爬蟲

        Args:
            html_content: HTML 內容字符串
        """
        self.soup = BeautifulSoup(html_content, 'html.parser')

    def extract_next_page_url(self) -> str | None:
        """
        擷取下一頁URL

        Returns:
            下一頁URL或None
        """
        # 找到"上頁"按鈕（PTT的分頁是倒序的）
        prev_link = self.soup.find('a', class_='btn wide', string='‹ 上頁')
        
        if prev_link and isinstance(prev_link, Tag):
            href = prev_link.get('href')
            if isinstance(href, str):
                return f"https://www.ptt.cc{href}"
        return None

    def extract_previous_page_url(self) -> str | None:
        """
        擷取上一頁URL

        Returns:
            上一頁URL或None
        """
        # 找到"下頁"按鈕（PTT的分頁是倒序的）
        next_link = self.soup.find('a', class_='btn wide', string='下頁 ›')
        
        if next_link and isinstance(next_link, Tag):
            href = next_link.get('href')
            if isinstance(href, str):
                return f"https://www.ptt.cc{href}"
        return None

    def has_next_page(self) -> bool:
        """
        檢查是否有下一頁

        Returns:
            是否有下一頁
        """
        return self.extract_next_page_url() is not None

    def has_previous_page(self) -> bool:
        """
        檢查是否有上一頁

        Returns:
            是否有上一頁
        """
        return self.extract_previous_page_url() is not None

    def get_pagination_info(self) -> PaginationInfo:
        """
        獲取完整的分頁資訊

        Returns:
            PaginationInfo 物件
        """
        next_url = self.extract_next_page_url()
        prev_url = self.extract_previous_page_url()
        
        return PaginationInfo(
            current_page=1,  # PTT沒有明確的頁碼顯示
            has_next=next_url is not None,
            has_previous=prev_url is not None,
            next_page_url=next_url,
            previous_page_url=prev_url,
            total_results=0  # 無法從單一頁面得知總結果數
        ) 