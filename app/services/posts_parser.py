def parse_apify_posts(raw_data: list) -> dict[str, dict]:
    """
    Parses the flat Apify engagement JSON (mixed posts + comments)
    and groups comments back under their parent posts.

    Returns a dict keyed by linkedin_url for easy profile lookup:
    {
        "https://www.linkedin.com/in/williamhgates": [ ...posts with comments... ],
        ...
    }
    """
    posts = {}      # post_id → post dict
    comments = []   # all comments, to be attached after

    for item in raw_data:
        item_type = item.get("type")

        if item_type == "post":
            post_id = item.get("id")
            if not post_id:
                continue

            # Extract reaction breakdown
            reactions = {
                r.get("type"): r.get("count", 0)
                for r in item.get("engagement", {}).get("reactions", [])
                if r.get("type")
            }

            posts[post_id] = {
                "post_id": post_id,
                "linkedin_url": item.get("query", {}).get("targetUrl", "").rstrip("/"),
                "content": item.get("content", ""),
                "date": item.get("postedAt", {}).get("date"),
                "has_image": bool(item.get("postImages")),
                "engagement": {
                    "likes": item.get("engagement", {}).get("likes", 0),
                    "comments": item.get("engagement", {}).get("comments", 0),
                    "shares": item.get("engagement", {}).get("shares", 0),
                    "reactions": reactions,
                },
                "comments": [],
                "author_reply_count": 0,
            }

        elif item_type == "comment":
            comments.append(item)

    # Attach comments to their parent posts
    for comment in comments:
        post_id = comment.get("postId")
        if not post_id or post_id not in posts:
            continue

        is_author = comment.get("actor", {}).get("author", False)

        # Extract author replies from nested replies list
        author_replies = [
            {
                "text": r.get("commentary", ""),
                "is_author": r.get("actor", {}).get("author", False),
            }
            for r in comment.get("replies", [])
        ]

        parsed_comment = {
            "text": comment.get("commentary", ""),
            "author_name": comment.get("actor", {}).get("name", ""),
            "is_author": is_author,
            "likes": comment.get("engagement", {}).get("likes", 0),
            "replies": author_replies,
        }

        posts[post_id]["comments"].append(parsed_comment)

        # Count how many times the post author replied
        if is_author:
            posts[post_id]["author_reply_count"] += 1
        posts[post_id]["author_reply_count"] += sum(
            1 for r in author_replies if r["is_author"]
        )

    # Group posts by linkedin_url
    grouped: dict[str, list] = {}
    for post in posts.values():
        url = post.pop("linkedin_url", "")  # remove from post dict, use as key
        if url:
            grouped.setdefault(url, []).append(post)

    return grouped


def trim_for_summarization(posts: list, max_comments: int = 5) -> str:
    """
    Converts a list of parsed posts into a compact plain-text string
    ready to be sent to the LLM for summarization.

    - Caps post content at 400 chars
    - Caps each comment at 150 chars
    - Keeps only top N comments (sorted by likes desc)
    - Flags author replies clearly
    - Includes reaction breakdown and engagement numbers
    """
    if not posts:
        return "No posts available."

    lines = []

    for i, post in enumerate(posts, start=1):
        engagement = post.get("engagement", {})
        reactions = engagement.get("reactions", {})

        # Reaction summary string e.g. "LIKE:255 EMPATHY:3 PRAISE:2"
        reaction_str = " ".join(
            f"{k}:{v}" for k, v in reactions.items() if v > 0
        )

        lines.append(
            f"--- POST {i} | {post.get('date', '')[:10]} | "
            f"👍{engagement.get('likes', 0)} "
            f"💬{engagement.get('comments', 0)} "
            f"🔁{engagement.get('shares', 0)} "
            f"{'🖼️ has image' if post.get('has_image') else ''} "
            f"| reactions: {reaction_str}"
        )

        # Post content capped at 400 chars
        content = (post.get("content") or "").strip()
        lines.append(content[:400] + ("..." if len(content) > 400 else ""))

        # Author reply count signal
        if post.get("author_reply_count", 0) > 0:
            lines.append(f"  [Author replied {post['author_reply_count']} time(s) in comments]")

        # Top N comments sorted by likes
        all_comments = post.get("comments", [])
        top_comments = sorted(all_comments, key=lambda c: c.get("likes", 0), reverse=True)[:max_comments]

        for comment in top_comments:
            prefix = "[AUTHOR] " if comment.get("is_author") else ""
            text = (comment.get("text") or "").strip()
            likes = comment.get("likes", 0)
            lines.append(f"  └ {prefix}{text[:150]} (👍{likes})")

            # Include author replies inside this comment thread
            for reply in comment.get("replies", []):
                if reply.get("is_author"):
                    reply_text = (reply.get("text") or "").strip()
                    lines.append(f"    └ [AUTHOR REPLY] {reply_text[:150]}")

        lines.append("")  # blank line between posts

    return "\n".join(lines)


def get_posts_for_profile(linkedin_url: str, raw_data: list, max_comments: int = 5) -> str:
    """
    Convenience function: parses raw Apify engagement JSON and returns
    the trimmed text string for a specific profile URL, ready for LLM.

    Usage:
        text = get_posts_for_profile(
            "https://www.linkedin.com/in/williamhgates",
            raw_engagement_data
        )
    """
    url = linkedin_url.rstrip("/")
    grouped = parse_apify_posts(raw_data)
    posts = grouped.get(url, [])
    return trim_for_summarization(posts, max_comments=max_comments)