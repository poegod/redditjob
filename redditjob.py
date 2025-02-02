import praw
import requests
import json
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheck)
    server.serve_forever()

# In your main():
    # Start health check server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

# Configuration
REDDIT_CLIENT_ID = 'CmOllAmVOoOxGaepHjS19w'
REDDIT_CLIENT_SECRET = '2CBb9z0d90Jru10R47QF3pwdpbe4_w'
REDDIT_USER_AGENT = 'JobPostingBot/1.0'
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1335605490360520836/KDtDnFWFRGGMjg_33DK53EPJibH-VjI28YbL1aIXSs8F8Z1Z6d5iTFePRvlmcyZRxZFY'
SUBREDDITS = ['forhire', 'hiring', 'YouTubeEditorsForHire', 'VideoEditingRequests', 'HireAnEditor']  # Add your desired subreddits
CHECK_INTERVAL = 300  # Check every 5 minutes
POSTS_LIMIT = 30  # Number of recent posts to check each time

def setup_reddit():
    """Initialize Reddit API client"""
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

def is_hiring_post(post):
    """Check if the post is a hiring post"""
    return 'hiring' in post.title.lower()

def send_to_discord(post):
    """Send formatted message to Discord"""
    embed = {
        "title": post.title[:256],  # Discord limits title to 256 characters
        "url": f"https://reddit.com{post.permalink}",
        "color": 3447003,  # Blue color
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [
            {
                "name": "Subreddit",
                "value": f"r/{post.subreddit}",
                "inline": True
            },
            {
                "name": "Author",
                "value": f"u/{post.author}",
                "inline": True
            }
        ],
        "footer": {
            "text": "Posted on Reddit"
        }
    }

    # Add post content preview if available
    if post.selftext:
        # Truncate content to first 1000 characters
        preview = post.selftext[:1000] + "..." if len(post.selftext) > 1000 else post.selftext
        embed["description"] = preview

    payload = {
        "embeds": [embed]
    }

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 204:
        print(f"Failed to send message to Discord: {response.status_code}")
    return response.status_code == 204

def process_subreddit(reddit, subreddit_name, processed_posts):
    """Process recent posts from a subreddit"""
    subreddit = reddit.subreddit(subreddit_name)
    
    for post in subreddit.new(limit=POSTS_LIMIT):
        # Skip if we've already processed this post or if it's not a hiring post
        if post.id in processed_posts or not is_hiring_post(post):
            continue
            
        # Send to Discord
        if send_to_discord(post):
            processed_posts.add(post.id)
            print(f"Sent hiring post to Discord: {post.title}")
            # Add small delay to avoid Discord rate limits
            time.sleep(1)

def main():
    reddit = setup_reddit()
    processed_posts = set()
    
    print("Starting Reddit to Discord Hiring Posts Bot...")
    
    while True:
        try:
            for subreddit in SUBREDDITS:
                process_subreddit(reddit, subreddit, processed_posts)
                
            # Clean up old post IDs to prevent memory growth
            if len(processed_posts) > 1000:
                processed_posts.clear()
                
            print(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main()
