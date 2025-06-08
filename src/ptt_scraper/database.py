from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship, Session, Mapped, mapped_column
from datetime import datetime
from typing import final
import os

from .models import Article, Comment


class Base(DeclarativeBase):
    pass


class SqlArticle(Base):
    """SQLAlchemy model for Article table"""
    __tablename__: str = 'articles'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ptt_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True, index=True)
    author: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # Relationship with comments
    comments: Mapped[list["SqlComment"]] = relationship("SqlComment", back_populates="article", cascade="all, delete-orphan")
    
    def to_pydantic(self) -> Article:
        """Convert SQLAlchemy model to Pydantic model"""
        return Article(
            id=self.ptt_id,
            title=self.title,
            url=self.url,
            author=self.author,
            content=self.content,
            created_at=self.created_at,
            comments=[comment.to_pydantic() for comment in self.comments]
        )


@final
class SqlComment(Base):
    """SQLAlchemy model for Comment table"""
    __tablename__: str = 'comments'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    floor: Mapped[int] = mapped_column(nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    
    # Foreign key to article
    article_id: Mapped[int] = mapped_column(ForeignKey('articles.id'), nullable=False, index=True)
    
    # Relationship with article
    article: Mapped["SqlArticle"] = relationship("SqlArticle", back_populates="comments")
    
    # Unique constraint on (article_id, floor) to prevent duplicate comments
    __table_args__: tuple[UniqueConstraint, ...] = (
        UniqueConstraint('article_id', 'floor', name='unique_article_floor'),
    )
    
    def to_pydantic(self) -> Comment:
        """Convert SQLAlchemy model to Pydantic model"""
        return Comment(
            floor=self.floor,
            author=self.author,
            content=self.content,
            reaction_type=self.reaction_type,
            created_at=self.created_at
        )


@final
class DatabaseManager:
    """Database manager for handling SQLite operations with SQLAlchemy"""

    def __init__(self, db_path: str = "ptt_scraper.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        self.create_tables()
    
    def create_tables(self) -> None:
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def save_article(self, article: Article) -> int:
        """
        Save an article with its comments to the database
        Uses (article_id, ptt_id) as composite key to preserve existing comments
        
        Args:
            article: Pydantic Article model to save
            
        Returns:
            int: ID of the saved article
        """
        session = self.get_session()
        try:
            # Check if article already exists by PTT ID
            existing_article = session.query(SqlArticle).filter_by(ptt_id=article.id).first()
            
            if existing_article:
                # Update existing article
                existing_article.title = article.title
                existing_article.author = article.author
                existing_article.content = article.content
                existing_article.created_at = article.created_at
                existing_article.updated_at = datetime.now()
                
                # Get existing comment floors for this article
                existing_comment_floors = set(
                    session.query(SqlComment.floor)
                    .filter_by(article_id=existing_article.id)
                    .all()
                )
                existing_comment_floors = {floor[0] for floor in existing_comment_floors}
                
                # Use SQLAlchemy SQLite INSERT ON CONFLICT DO NOTHING to handle duplicates gracefully
                new_comments_count = 0
                for comment in article.comments:
                    # Use SQLAlchemy's SQLite dialect INSERT ON CONFLICT DO NOTHING
                    stmt = (
                        insert(SqlComment)
                        .values(
                            floor=comment.floor,
                            author=comment.author,
                            content=comment.content,
                            reaction_type=comment.reaction_type,
                            created_at=comment.created_at,
                            article_id=existing_article.id
                        )
                        .on_conflict_do_nothing(
                            index_elements=['article_id', 'floor']
                        )
                    )
                    result = session.execute(stmt)
                    # Check if the row was actually inserted (rowcount > 0)
                    if getattr(result, 'rowcount', 0) > 0:
                        new_comments_count += 1
                
                session.commit()
                print(f"\t[*] Added {new_comments_count} new comments (preserved {len(existing_comment_floors)} existing)")
                
                return existing_article.id
            else:
                # Create new article
                article_db = SqlArticle(
                    ptt_id=article.id,
                    title=article.title,
                    url=article.url,
                    author=article.author,
                    content=article.content,
                    created_at=article.created_at
                )
                session.add(article_db)
                session.flush()  # Get the ID
                
                # Add all comments for new article using INSERT ON CONFLICT DO NOTHING
                comments_added = 0
                for comment in article.comments:
                    # Use SQLAlchemy's SQLite dialect INSERT ON CONFLICT DO NOTHING
                    stmt = (
                        insert(SqlComment)
                        .values(
                            floor=comment.floor,
                            author=comment.author,
                            content=comment.content,
                            reaction_type=comment.reaction_type,
                            created_at=comment.created_at,
                            article_id=article_db.id
                        )
                        .on_conflict_do_nothing(
                            index_elements=['article_id', 'floor']
                        )
                    )
                    result = session.execute(stmt)
                    # Check if the row was actually inserted
                    if getattr(result, 'rowcount', 0) > 0:
                        comments_added += 1
                
                session.commit()
                print(f"\t[*] Added {comments_added} comments to new article")
                return article_db.id
                
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_article_by_id(self, article_id: int) -> Article | None:
        """
        Get article by database ID
        
        Args:
            article_id: Database ID of the article
            
        Returns:
            Article or None if not found
        """
        session = self.get_session()
        try:
            article_db = session.query(SqlArticle).filter_by(id=article_id).first()
            if article_db:
                return article_db.to_pydantic()
            return None
        finally:
            session.close()
    
    def get_article_by_ptt_id(self, ptt_id: str) -> Article | None:
        """
        Get article by PTT ID
        
        Args:
            ptt_id: PTT ID of the article
            
        Returns:
            Article or None if not found
        """
        session = self.get_session()
        try:
            article_db = session.query(SqlArticle).filter_by(ptt_id=ptt_id).first()
            if article_db:
                return article_db.to_pydantic()
            return None
        finally:
            session.close()
    
    def get_article_by_url(self, url: str) -> Article | None:
        """
        Get article by URL
        
        Args:
            url: URL of the article
            
        Returns:
            Article or None if not found
        """
        session = self.get_session()
        try:
            article_db = session.query(SqlArticle).filter_by(url=url).first()
            if article_db:
                return article_db.to_pydantic()
            return None
        finally:
            session.close()
    
    def get_articles_by_author(self, author: str) -> list[Article]:
        """
        Get all articles by a specific author
        
        Args:
            author: Author name
            
        Returns:
            List of articles
        """
        session = self.get_session()
        try:
            articles_db = session.query(SqlArticle).filter_by(author=author).all()
            return [article.to_pydantic() for article in articles_db]
        finally:
            session.close()
    
    def get_all_articles(self, limit: int | None = None, offset: int = 0) -> list[Article]:
        """
        Get all articles with optional pagination
        
        Args:
            limit: Maximum number of articles to return
            offset: Number of articles to skip
            
        Returns:
            List of articles
        """
        session = self.get_session()
        try:
            query = session.query(SqlArticle).order_by(SqlArticle.created_at.desc())
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            articles_db = query.all()
            return [article.to_pydantic() for article in articles_db]
        finally:
            session.close()
    
    def search_articles(self, keyword: str) -> list[Article]:
        """
        Search articles by keyword in title or content
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of matching articles
        """
        session = self.get_session()
        try:
            articles_db = session.query(SqlArticle).filter(
                (SqlArticle.title.contains(keyword)) | 
                (SqlArticle.content.contains(keyword))
            ).all()
            return [article.to_pydantic() for article in articles_db]
        finally:
            session.close()
    
    def get_comments_by_article_id(self, article_id: int) -> list[Comment]:
        """
        Get all comments for a specific article
        
        Args:
            article_id: Database ID of the article
            
        Returns:
            List of comments
        """
        session = self.get_session()
        try:
            comments_db = session.query(SqlComment).filter_by(
                article_id=article_id
            ).order_by(SqlComment.created_at).all()
            return [comment.to_pydantic() for comment in comments_db]
        finally:
            session.close()
    
    def get_article_count(self) -> int:
        """Get total number of articles in database"""
        session = self.get_session()
        try:
            return session.query(SqlArticle).count()
        finally:
            session.close()
    
    def get_comment_count(self) -> int:
        """Get total number of comments in database"""
        session = self.get_session()
        try:
            return session.query(SqlComment).count()
        finally:
            session.close()
    
    def delete_article(self, article_id: int) -> bool:
        """
        Delete an article and its comments
        
        Args:
            article_id: Database ID of the article to delete
            
        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            article_db = session.query(SqlArticle).filter_by(id=article_id).first()
            if article_db:
                session.delete(article_db)  # Comments will be deleted due to cascade
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_database_stats(self) -> "DatabaseStats":
        """
        Get database statistics
        
        Returns:
            DatabaseStats object with database statistics
        """
        return DatabaseStats(
            total_articles=self.get_article_count(),
            total_comments=self.get_comment_count(),
            database_path=self.db_path,
            database_size_mb=round(os.path.getsize(self.db_path) / (1024 * 1024), 2) if os.path.exists(self.db_path) else 0
        )
    
    def close(self) -> None:
        """Close database connection"""
        self.engine.dispose()


class DatabaseStats(BaseModel):
    total_articles: int = Field(description="Total number of articles in database")
    total_comments: int = Field(description="Total number of comments in database")
    database_path: str = Field(description="Path to the database file")
    database_size_mb: float = Field(description="Size of the database file in MB")
