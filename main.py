import asyncio
import os
from zoneinfo import ZoneInfo
import httpx
from bs4 import BeautifulSoup, Tag
from datetime import datetime
import logging
from typing import List, Dict, Any, Tuple

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

# API configuration
API_BASE_URL = os.getenv("STORAGE_API_BASE_URL", "http://localhost:8080")  # Change this to your actual API base URL


async def get_month_first_day() -> datetime:
    """Get the first day of the current month."""
    today = datetime.today()
    return today.replace(day=today.day - 5, hour=0, minute=0, second=0, microsecond=0)


async def get_article_content_and_comments(client: httpx.AsyncClient, url: str) -> Tuple[str, datetime | None, List[Dict[str, str]]]:
    """Fetch article content and comments from a PTT article URL."""
    try:
        response = await client.get(url, headers=HEADERS, cookies=COOKIES)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.find('div', id='main-content')
        
        if not main_content:
            return '', None, []

        # Extract comments (pushes)
        pushes = []
        for push in soup.select('div.push'):
            tag = push.select_one('span.push-tag')
            user = push.select_one('span.push-userid')
            content = push.select_one('span.push-content')
            ipdatetime = push.select_one('span.push-ipdatetime')

            assert isinstance(ipdatetime, Tag)

            # 111.240.96.24 03/29 22:49
            _, time = ipdatetime.get_text(strip=True).split(' ', maxsplit=1)

            pushes.append({
                'tag': tag.text.strip() if tag else '',
                'user': user.text.strip() if user else '',
                'content': content.text.strip(': ').strip() if content else '',
                'time': time
            })

        # Find metadata with article-meta-tag=時間
        article_meta_datetime_tag_name = soup.find('span', class_='article-meta-tag', string='時間')
        assert isinstance(article_meta_datetime_tag_name, Tag), "Article meta datetime tag not found"
        article_meta_datetime_tag = article_meta_datetime_tag_name.parent
        assert isinstance(article_meta_datetime_tag, Tag), "Article meta datetime tag not found"

        # Sun Apr 13 14:05:20 2025
        article_meta_datetime_value = article_meta_datetime_tag.find('span', class_='article-meta-value')
        assert isinstance(article_meta_datetime_value, Tag), "Article meta datetime value not found"
        article_meta_datetime = datetime.strptime(article_meta_datetime_value.get_text(strip=True), "%a %b %d %H:%M:%S %Y")
        article_meta_datetime = article_meta_datetime.replace(tzinfo=ZoneInfo("Asia/Taipei"))

        # Remove metadata and pushes from content
        assert isinstance(main_content, Tag)
        for tag in main_content.select('div.article-metaline') + main_content.select('div.article-metaline-right') + main_content.select('div.push'):
            tag.decompose()

        content_text = main_content.text.strip()
        return content_text, article_meta_datetime, pushes
    
    except Exception as e:
        logger.error(f"Error fetching article content: {e}")
        return '', None, []


async def search_articles(client: httpx.AsyncClient, board: str, keyword: str) -> List[Dict[str, Any]]:
    """Search for articles matching the keyword on the specified board."""
    base_url = f"{BASE_URL}/bbs/{board}/search?q={keyword}"
    cutoff_date = await get_month_first_day()
    logger.info(f"📆 Only crawling articles from {cutoff_date.strftime('%Y/%m/%d')}")

    all_data = []
    next_url = base_url

    while next_url:
        try:
            response = await client.get(next_url, headers=HEADERS, cookies=COOKIES)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            r_ents = soup.select('div.r-ent')
            stop_flag = False

            for r in r_ents:
                date = r.select_one('.date')
                assert isinstance(date, Tag)
                date_str = date.text.strip()
                link_tag = r.select_one('div.title a')
                
                if not link_tag:
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

                title = link_tag.text.strip()
                href = link_tag['href']

                assert isinstance(href, str)
                href = BASE_URL + href
                article_id = href.split('/')[-1].strip().replace('.html', '')
                
                logger.info(f"📄 {full_date.strftime('%m/%d')} {title} -> {href}")

                all_data.append({
                    'id': article_id,
                    'title': title,
                    'url': href,
                    'created_at': full_date
                })

            if stop_flag:
                break

            prev_link = soup.select_one('a.btn.wide:contains("上頁")')
            if prev_link:
                href = prev_link['href']
                assert isinstance(href, str)
                next_url = BASE_URL + href
            else:
                break
                
        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            break

    logger.info(f"✅ Found {len(all_data)} articles")
    return all_data


async def post_article(client: httpx.AsyncClient, platform: str, article: Dict[str, Any]) -> bool:
    """Post article data to the API."""
    try:
        url = f"{API_BASE_URL}/{platform}/articles"
        
        # Format the article data according to the API schema
        payload = {
            "id": article["id"],
            "title": article["title"],
            "created_at": article["created_at"].isoformat(),
            "content": article["content"],
            "url": article["url"]
        }
        
        response = await client.post(url, json=payload)
        
        if response.status_code == 201:
            result = response.json()

            # if this article has been always posted, return False (do nothing)
            if result.get("existed", False):
                return False

            return result.get("success", False)
        else:
            logger.error(f"API error posting article: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error posting article to API: {e}")
        return False


async def post_comment(
    client: httpx.AsyncClient, 
    platform: str, 
    article_id: str, 
    comment: Dict[str, Any]
) -> bool:
    """Post comment data to the API."""
    try:
        url = f"{API_BASE_URL}/{platform}/articles/{article_id}/comments"
        
        # Format the comment data according to the API schema
        payload = {
            "id": comment["id"],
            "content": comment["content"],
            "created_at": comment["created_at"].isoformat(),
            "author": comment["author"],
            "reaction_type": comment["reaction_type"]
        }
        
        response = await client.post(url, json=payload)
        
        if response.status_code == 201:
            result = response.json()
            return result.get("success", False)
        else:
            logger.error(f"API error posting comment: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error posting comment to API: {e}")
        return False


async def process_article(
    client: httpx.AsyncClient, 
    platform: str, 
    article: Dict[str, Any]
) -> None:
    """Process an article and its comments, then post to the API."""
    logger.info(f"🔎 Processing: {article['title']}")
    
    try:
        # Get article content and comments
        content, time, comments = await get_article_content_and_comments(client, article['url'])
        article['content'] = content
        
        if time is not None:
            article['created_at'] = time

        # Post article to API
        posted = await post_article(client, platform, article)
        if posted:
            logger.info(f"✅ Successfully posted article: {article['title']}")
        else:
            logger.warning(f"⚠️ Failed to post article: {article['title']}")
            return

        # Process and post comments concurrently
        comment_tasks = []
        for id, comment_data in enumerate(comments):
            # Parse comment time if available
            try:
                comment_time = datetime.strptime(comment_data['time'].strip(), "%m/%d %H:%M")
                # fixme: it might be a last year's comment
                comment_time = comment_time.replace(year=article['created_at'].year, tzinfo=ZoneInfo("Asia/Taipei"))
            except ValueError:
                logger.warning(f"Bad time format: {comment_data['time']}")
                comment_time = datetime.now()

            # Create comment object
            comment = {
                "id": f"c{id}",
                "content": comment_data['content'],
                "created_at": comment_time,
                "author": comment_data['user'],
                "reaction_type": tag_to_reaction_type(comment_data['tag'])
            }
            
            # Add post comment task
            comment_tasks.append(post_comment(client, platform, article['id'], comment))
        
        # Execute all comment posting tasks concurrently
        results = await asyncio.gather(*comment_tasks, return_exceptions=True)
        
        # Check results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Failed to post comment: {result}")
            elif not result:
                logger.warning(f"⚠️ Failed to post comment by {comments[i]['user']}")

    except Exception as e:
        logger.error(f"⚠️ Error processing article: {e}")


def tag_to_reaction_type(tag: str) -> str:
    if tag == '推':
        return '+1'
    elif tag == '噓':
        return '-1'
    return '0'


async def main():
    board = input("Enter the board name: ")
    keyword = input("Enter the keyword: ")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search for articles
        articles = await search_articles(client, board, keyword)
        
        # Process each article and its comments
        # Create a semaphore to limit concurrent tasks to 4
        semaphore = asyncio.Semaphore(4)
        
        async def process_with_semaphore(article):
            async with semaphore:
                return await process_article(client, "ptt", article)
        
        tasks = (process_with_semaphore(article) for article in articles)
        await asyncio.gather(*tasks)
    
    logger.info("✅ Crawling completed")


if __name__ == "__main__":
    asyncio.run(main())
