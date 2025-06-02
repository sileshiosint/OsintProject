
def parse_instagram_html(html):
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    scripts = soup.find_all("script", type="text/javascript")
    for script in scripts:
        if 'window._sharedData' in script.text:
            try:
                import json, re
                raw_json = re.search(r'window._sharedData = (.*);', script.text).group(1)
                data = json.loads(raw_json)
                edges = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]
                for edge in edges[:10]:
                    post = edge["node"]
                    posts.append({
                        "caption": post["edge_media_to_caption"]["edges"][0]["node"]["text"] if post["edge_media_to_caption"]["edges"] else "",
                        "likes": post["edge_liked_by"]["count"],
                        "shortcode": post["shortcode"]
                    })
            except Exception as e:
                posts.append({"error": str(e)})
            break
    return posts



def parse_youtube_html(html):
    soup = BeautifulSoup(html, "html.parser")
    videos = []
    for video_div in soup.find_all("ytd-video-renderer", limit=10):
        title_elem = video_div.find("a", id="video-title")
        channel_elem = video_div.find("a", class_="yt-simple-endpoint style-scope yt-formatted-string")
        views_elem = video_div.find("span", class_="inline-metadata-item style-scope ytd-video-meta-block")
        video = {}
        if title_elem:
            video["title"] = title_elem.get_text(strip=True)
        if channel_elem:
            video["channel"] = channel_elem.get_text(strip=True)
        if views_elem:
            video["views"] = views_elem.get_text(strip=True)
        if video:
            videos.append(video)
    return videos



def parse_facebook_html(html):
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    divs = soup.find_all("div")
    for div in divs:
        text = div.get_text(strip=True)
        if text and len(text) > 80 and "like" not in text.lower():  # crude filter for meaningful content
            posts.append({"content": text[:280]})
            if len(posts) >= 10:
                break
    return posts



def parse_twitter_html(html):
    soup = BeautifulSoup(html, "html.parser")
    tweets = []
    for article in soup.find_all("article"):
        tweet = {}
        user_elem = article.find("div", attrs={"data-testid": "User-Name"})
        content_elem = article.find("div", attrs={"data-testid": "tweetText"})
        timestamp = article.find("time")
        if user_elem:
            tweet["user"] = user_elem.get_text(strip=True)
        if content_elem:
            tweet["content"] = content_elem.get_text(strip=True)
        if timestamp:
            tweet["time"] = timestamp["datetime"]
        if tweet:
            tweets.append(tweet)
    return tweets


from bs4 import BeautifulSoup

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_chrome_with_debugger():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def run_scraper(query, search_type, platform):
    driver = get_chrome_with_debugger()
    results = []
    html = ""
    screenshot = None

    if platform == "twitter":
        driver.get(f"https://twitter.com/search?q={query}&src=typed_query")
        time.sleep(5)
        html = driver.page_source
        screenshot = driver.get_screenshot_as_base64()
        
        soup = BeautifulSoup(html, "html.parser")
        tweets = soup.find_all("div", {"data-testid": "cellInnerDiv"})
        for tweet in tweets[:10]:
            content = tweet.get_text(separator=" ", strip=True)
            results.append({"tweet": content})
        

    elif platform == "facebook":
        driver.get(f"https://www.facebook.com/search/top?q={query}")
        time.sleep(5)
        html = driver.page_source
        screenshot = driver.get_screenshot_as_base64()
        results = parse_facebook_html(html)

    
    elif platform == "youtube":
        driver.get(f"https://www.youtube.com/results?search_query={query}")
        time.sleep(5)
        html = driver.page_source
        screenshot = driver.get_screenshot_as_base64()
        results = parse_youtube_html(html)


    
    elif platform == "instagram":
        driver.get(f"https://www.instagram.com/{query}/")
        time.sleep(5)
        html = driver.page_source
        screenshot = driver.get_screenshot_as_base64()
        results = parse_instagram_html(html)


    else:
        results = [{"error": f"Platform '{platform}' is not yet supported."}]

    driver.quit()

    return {
        "results": results,
        "html": html,
        "screenshot": screenshot
    }



import csv
import os

def export_results_to_csv(results, query, platform, output_dir="exports"):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{platform}_{query.replace(' ', '_')}.csv"
    if not results:
        return filename

    keys = set()
    for r in results:
        keys.update(r.keys())
    keys = sorted(keys)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
    return filename



def export_enriched_results(results, query, platform, output_dir="exports"):
    import json
    import os
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{platform}_{query.replace(' ', '_')}_enriched.csv"
    if not results:
        return filename

    # Flatten entity and Detoxify fields into strings
    flat_results = []
    for r in results:
        flat = r.copy()
        if "entities" in flat:
            flat["entities"] = ", ".join([f"{e['text']} ({e['label']})" for e in flat["entities"]])
        flat_results.append(flat)

    import csv
    keys = sorted(set().union(*(r.keys() for r in flat_results)))
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(flat_results)
    return filename
