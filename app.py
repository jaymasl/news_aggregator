import feedparser
import re
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from flask_caching import Cache
import threading
import time
import html
import logging
import concurrent.futures

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 300})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RSS_FEEDS = {
    'BBC': 'https://feeds.bbci.co.uk/news/world/rss.xml',
    'NPR': 'https://feeds.npr.org/1004/rss.xml',
    'MIT Technology Review': 'https://www.technologyreview.com/feed/',
    'Science Daily': 'https://www.sciencedaily.com/rss/all.xml',
    'Financial Times': 'https://www.ft.com/world?format=rss',
    'Deutsche Welle': 'https://rss.dw.com/rdf/rss-en-world',
    'ABC': 'https://abcnews.go.com/abcnews/internationalheadlines',
    'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/technology-lab'
}

from urllib.parse import unquote

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    selected_source = request.args.get('source', '')
    
    if selected_source:
        selected_source = unquote(selected_source)
    
    articles = load_cached_articles(selected_source)
    if not articles and selected_source:
        articles = fetch_and_cache_articles(selected_source)
    
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    paginated_articles = articles[start:end]
    total_pages = len(articles) // per_page + (1 if len(articles) % per_page else 0)
    
    return render_template('index.jinja', articles=paginated_articles, page=page, total_pages=total_pages, sources=RSS_FEEDS.keys(), selected_source=selected_source)

@app.route('/search')
def search():
    query = request.args.get('q')
    selected_source = request.args.get('source', '')
    articles = load_cached_articles(selected_source)
    results = [article for article in articles if query.lower() in article[1].title.lower()]
    return render_template('search_results.jinja', articles=results, query=query, sources=RSS_FEEDS.keys(), selected_source=selected_source)

@app.route('/load_more')
def load_more():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    selected_source = request.args.get('source', '')
    articles = load_cached_articles(selected_source)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_articles = articles[start:end]
    return render_template('article_items.jinja', articles=paginated_articles) if paginated_articles else ''

@app.route('/check_articles')
def check_articles():
    selected_source = request.args.get('source', '')
    articles = load_cached_articles(selected_source)
    if not articles and selected_source:
        articles = fetch_and_cache_articles(selected_source)
    return jsonify({'articles_available': len(articles) > 0, 'article_count': len(articles)})

def background_article_fetch():
    while True:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(update_cache_for_source, source) for source in RSS_FEEDS.keys()]
            concurrent.futures.wait(futures)
        time.sleep(300)

def update_cache_for_source(source):
    try:
        articles = get_articles(source)
        cache.set(f'articles_{source}', articles)
        logger.info(f"Updated cache for source: {source}")
    except Exception as e:
        logger.error(f"Error fetching articles for {source}: {str(e)}")

def load_cached_articles(selected_source=None):
    if selected_source:
        return cache.get(f'articles_{selected_source}') or []
    
    all_articles = []
    seen_urls = set()
    
    for source in RSS_FEEDS.keys():
        source_articles = cache.get(f'articles_{source}')
        if not source_articles:
            source_articles = fetch_and_cache_articles(source)
        
        if source_articles:
            for article_tuple in source_articles:
                article_url = article_tuple[1].link
                if article_url not in seen_urls:
                    all_articles.append(article_tuple)
                    seen_urls.add(article_url)

    return sorted(all_articles, key=lambda x: x[1].sort_key, reverse=True)

def fetch_and_cache_articles(source):
    articles = get_articles(source)
    cache.set(f'articles_{source}', articles)
    return articles

def get_articles(source):
    feed = RSS_FEEDS[source]
    try:
        parsed_feed = feedparser.parse(feed)
        articles = []
        seen_urls = set()
        for entry in parsed_feed.entries:
            try:
                article = process_entry(source, entry)
                article_url = entry.link
                if article_url not in seen_urls:
                    articles.append((source, article))
                    seen_urls.add(article_url)
            except Exception as e:
                logger.error(f"Error processing entry for {source}: {str(e)}")
        return articles
    except Exception as e:
        logger.error(f"Error parsing feed for {source}: {str(e)}")
        return []

def process_entry(source, entry):
    entry.title = html.unescape(entry.title)
    entry.link = entry.link
    text = getattr(entry, 'summary_detail', getattr(entry, 'description', ''))
    text_value = re.sub(r'<[^>]+>', '', text.value if hasattr(text, 'value') else text)
    entry.text_clip = (text_value[:300] + '...') if len(text_value) > 300 else text_value
    if hasattr(entry, 'published_parsed'):
        entry.published = datetime(*entry.published_parsed[:6]).strftime('%d %B %Y %H:%M')
        entry.sort_key = entry.published_parsed
    elif hasattr(entry, 'updated_parsed'):
        entry.published = datetime(*entry.updated_parsed[:6]).strftime('%d %B %Y %H:%M')
        entry.sort_key = entry.updated_parsed
    else:
        entry.published = "Unknown date"
        entry.sort_key = datetime.min.timetuple()
    return entry

if __name__ == '__main__':
    threading.Thread(target=background_article_fetch, daemon=True).start()
    app.run(debug=True)
