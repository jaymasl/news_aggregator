# RSS Feed Aggregator

This is a Python Flask-based web application that aggregates and displays news articles from multiple RSS feeds. The app allows users to view articles from different news sources, search for specific articles, and load more content dynamically as they scroll. Cached articles are automatically refreshed in the background.

## Features
- **Multiple RSS Feeds**: The app fetches news from various sources, including BBC, NPR, MIT Technology Review, Science Daily, and more.
- **Article Caching**: Articles are cached for faster load times, with automatic updates occurring every 5 minutes.
- **Search Functionality**: Search for articles by keywords within the available news articles.
- **Endless Scrolling**: Articles load automatically as the user scrolls down the page, enabling seamless browsing.
- **Background Fetching**: Articles are fetched in the background using multithreading.

## Endpoints
- `/`: Home page displaying articles from selected sources, with endless scrolling for more content.
- `/search`: Search for articles by keyword.
- `/load_more`: Load more articles dynamically as the user scrolls.
- `/check_articles`: Check if articles are available for the selected source.

## Background Process
- A separate background thread runs to update cached articles every 5 minutes from the specified RSS sources.

## RSS Sources
- BBC, NPR, MIT Technology Review, Science Daily, Financial Times, Deutsche Welle, ABC, Ars Technica.
