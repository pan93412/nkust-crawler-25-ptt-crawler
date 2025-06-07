import asyncio
import httpx
from datetime import datetime
from typing import final
import logging

from .models import Article, SearchResult
from .scrapers import ArticleScraper, CommentScraper, PaginationScraper
from .database import DatabaseManager, DatabaseStats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.ptt.cc"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
}
COOKIES = {
    'over18': '1'
}


@final
class PTTCrawler:
    """PTT 爬蟲主類"""
    
    def __init__(self, db_path: str = "ptt_scraper.db", cutoff_days: int = 5):
        """
        初始化 PTT 爬蟲
        
        Args:
            db_path: 資料庫檔案路徑
            cutoff_days: 只抓取幾天內的文章（從今天往前算）
        """
        self.db_manager = DatabaseManager(db_path)
        self.cutoff_days = cutoff_days
        self.client: httpx.AsyncClient | None = None
        
    async def __aenter__(self):
        """非同步上下文管理器進入"""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器退出"""
        if self.client:
            await self.client.aclose()
    
    def get_cutoff_date(self) -> datetime:
        """取得截止日期"""
        today = datetime.today()
        return today.replace(day=today.day - self.cutoff_days, hour=0, minute=0, second=0, microsecond=0)
    
    async def fetch_html(self, url: str) -> str:
        """
        取得網頁 HTML 內容
        
        Args:
            url: 目標URL
            
        Returns:
            HTML 內容
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")
            
        try:
            response = await self.client.get(url, headers=HEADERS, cookies=COOKIES)
            _ = response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching HTML from {url}: {e}")
            return ""
    
    async def search_articles(self, board: str, keyword: str) -> list[SearchResult]:
        """
        搜尋指定看板的文章
        
        Args:
            board: 看板名稱
            keyword: 搜尋關鍵字
            
        Returns:
            搜尋結果列表
        """
        search_url = f"{BASE_URL}/bbs/{board}/search?q={keyword}"
        cutoff_date = self.get_cutoff_date()
        logger.info(f"📆 Only crawling articles from {cutoff_date.strftime('%Y/%m/%d')}")
        
        all_results = list[SearchResult]()
        next_url = search_url
        
        while next_url:
            try:
                html_content = await self.fetch_html(next_url)
                if not html_content:
                    break
                    
                pagination_scraper = PaginationScraper(html_content)
                results, stop_flag = self._extract_search_results_from_page(
                    html_content, cutoff_date
                )
                
                all_results.extend(results)
                
                if stop_flag:
                    break
                
                # 取得下一頁URL（注意PTT的分頁順序）
                pagination_info = pagination_scraper.get_pagination_info()
                if pagination_info.has_next:
                    next_url = pagination_info.next_page_url
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error searching articles: {e}")
                break
        
        logger.info(f"✅ Found {len(all_results)} articles")
        return all_results
    
    def _extract_search_results_from_page(self, html_content: str, cutoff_date: datetime) -> tuple[list[SearchResult], bool]:
        """
        從搜尋結果頁面提取文章列表
        
        Args:
            html_content: 頁面HTML內容
            cutoff_date: 截止日期
            
        Returns:
            (搜尋結果列表, 是否應該停止搜尋)
        """
        from bs4 import BeautifulSoup
        
        results = list[SearchResult]()
        soup = BeautifulSoup(html_content, 'html.parser')
        r_ents = soup.select('div.r-ent')
        stop_flag = False
        
        for r in r_ents:
            date_element = r.select_one('.date')
            if not date_element:
                continue
                
            date_str = date_element.get_text(strip=True)
            link_element = r.select_one('div.title a')
            
            if not link_element:
                continue
            
            try:
                this_year = datetime.today().year
                full_date = datetime.strptime(f"{this_year}/{date_str}", "%Y/%m/%d")
            except ValueError:
                continue
            
            if full_date < cutoff_date:
                logger.info(f"⛔ Stopping: {full_date.strftime('%Y/%m/%d')} is earlier than {cutoff_date.strftime('%Y/%m/%d')}")
                stop_flag = True
                break
            
            title = link_element.get_text(strip=True)
            href = link_element.get('href')
            
            if not isinstance(href, str):
                continue
                
            full_url = BASE_URL + href
            article_id = href.split('/')[-1].strip().replace('.html', '')
            
            logger.info(f"📄 {full_date.strftime('%m/%d')} {title} -> {full_url}")
            
            results.append(SearchResult(
                id=article_id,
                title=title,
                url=full_url,
                created_at=full_date
            ))
        
        return results, stop_flag
    
    async def scrape_article(self, url: str) -> Article | None:
        """
        抓取單一文章及其留言
        
        Args:
            url: 文章URL
            
        Returns:
            Article 物件或 None
        """
        try:
            html_content = await self.fetch_html(url)
            if not html_content:
                return None
            
            # 提取文章資訊
            article_scraper = ArticleScraper(html_content)
            
            article_id = url.split('/')[-1].strip().replace('.html', '')
            title = article_scraper.extract_title()
            author = article_scraper.extract_author()
            content = article_scraper.extract_content()
            created_at = article_scraper.extract_datetime()
            
            # 提取留言
            comment_scraper = CommentScraper()
            soup = article_scraper.get_soup()
            comments = comment_scraper.extract_comments(soup, created_at.year)
            
            return Article(
                id=article_id,
                title=title,
                url=url,
                author=author,
                content=content,
                created_at=created_at,
                comments=comments
            )
            
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
            return None
    
    async def crawl_board(self, board: str, keyword: str, max_articles: int | None = None) -> int:
        """
        爬取指定看板的文章
        
        Args:
            board: 看板名稱
            keyword: 搜尋關鍵字
            max_articles: 最大文章數量限制
            
        Returns:
            成功處理的文章數量
        """
        # 搜尋文章
        search_results = await self.search_articles(board, keyword)
        
        if max_articles:
            search_results = search_results[:max_articles]
        
        # 建立 semaphore 限制並發數量
        semaphore = asyncio.Semaphore(4)
        processed_count = 0
        
        async def process_article(search_result: SearchResult) -> bool:
            nonlocal processed_count
            async with semaphore:
                logger.info(f"🔎 Processing: {search_result.title}")
                
                article = await self.scrape_article(search_result.url)
                if article:
                    try:
                        _ = self.db_manager.save_article(article)
                        logger.info(f"✅ Saved: {article.title}")
                        processed_count += 1
                        return True
                    except Exception as e:
                        logger.error(f"❌ Failed to save {article.title}: {e}")
                        return False
                else:
                    logger.warning(f"⚠️ Failed to scrape: {search_result.title}")
                    return False
        
        # 並發處理所有文章
        tasks = [process_article(result) for result in search_results]
        _ = await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"✅ Crawling completed. Processed {processed_count} articles.")
        return processed_count
    
    def get_stats(self) -> DatabaseStats:
        """
        取得資料庫統計資訊
        
        Returns:
            統計資訊字典
        """
        return self.db_manager.get_database_stats()
    
    def close(self) -> None:
        """關閉資料庫連線"""
        self.db_manager.close()


async def crawl_ptt(board: str, keyword: str, db_path: str = "ptt_scraper.db", 
                   cutoff_days: int = 5, max_articles: int | None = None) -> int:
    """
    便利函數：爬取 PTT 文章
    
    Args:
        board: 看板名稱
        keyword: 搜尋關鍵字
        db_path: 資料庫檔案路徑
        cutoff_days: 只抓取幾天內的文章
        max_articles: 最大文章數量限制
        
    Returns:
        成功處理的文章數量
    """
    async with PTTCrawler(db_path, cutoff_days) as crawler:
        return await crawler.crawl_board(board, keyword, max_articles) 