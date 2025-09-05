import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Dict, List
import re
import html as htmllib
import feedparser
from dateutil import parser as dtparser
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse


from models import Preferences, DealItem, DealEnvelope
from rss_sources import FEEDS


app = FastAPI(title="Deal Feed")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_ORIGINS = None  # e.g., {"https://your-frontend.vercel.app"}
ALLOWED_SUFFIXES = (".vercel.app",)


# --- In-memory state (MVP) ---
USER_PREFS: Dict[str, Preferences] = {"demo": Preferences()} 
SEEN: Dict[str, DealItem] = {}
CLIENTS: List[WebSocket] = []


RELN = {
    "KKR": "Co-invested with KKR",
    "Blackstone": "LP relationship: Blackstone fund",
    "Apollo": "Former portfolio CFO now at target",
    "BlackRock":"",
    "Bain":"",
    "Carlyle":"",
    "Morgan Stanley":""
}


EVENT_KEYWORDS = {
    "M&A": ["acquire", "acquisition", "merger", "buy", "take-private", "LBO"],
    "Financing": ["financing", "credit", "debt", "unitranche", "term loan", "capex"],
    "Exit": ["divest", "sell", "spin-off", "sale", "exit"],
    "Partnership": ["partnership", "joint venture", "JV", "strategic alliance"],
}


FIRM_CANON = {"KKR", "Blackstone", "Apollo", "Carlyle", "TPG", "Bain Capital", "BlackRock", "Morgan Stanley"}

# --- NEW: relevance patterns (near top, after EVENT_KEYWORDS) ---
PRIVATE_CONTEXT = [
    "private company", "portfolio company", "private equity", "growth equity",
    "pe-backed", "sponsor-backed", "financial sponsor", "buyout", "lbo",
    "take-private", "minority investment", "majority investment", "bolt-on",
    "add-on acquisition", "capex", "capital expenditure", "unitranche",
    "term loan", "senior secured", "mezzanine", "bridge financing"
]

# Things that likely indicate public-market only chatter (let through if take-private)
PUBLIC_MARKET_NOISE = [
    "sec filing", "8-k", "10-k", "10-q", "earnings call", "dividend",
    "nasdaq:", "nyse:", "ticker:", "ipo filing", "ipo priced"
]

RELEVANT_ACTIONS = [
    "acquire", "acquisition", "merger", "buy", "take-private", "lbo",
    "divest", "sell", "spin-off", "sale", "exit",
    "financing", "credit", "debt", "unitranche", "term loan", "capex",
    "partnership", "joint venture", "strategic alliance"
] + [kw for kws in EVENT_KEYWORDS.values() for kw in kws]

def is_relevant_private_deal(text: str) -> bool:
    t = text.lower()

    # Must mention at least one relevant action
    # if not any(k in t for k in RELEVANT_ACTIONS):
    #     return False

    # If it looks like public-market noise, require take-private context to pass
    # if any(k in t for k in PUBLIC_MARKET_NOISE) and "take-private" not in t and "lbo" not in t:
    #     return False

    # Prefer explicit private-deal context (but don't strictly require it when a clear action exists)
    # if any(k in t for k in PRIVATE_CONTEXT):
    #     return True

    # Fallback: allow classic M&A verbs if not clearly public-only
    return True


def classify(text: str) -> str:
    lo = text.lower()
    for etype, kws in EVENT_KEYWORDS.items():
        if any(k in lo for k in kws):
            return etype
    return "Other"

TAG_RE = re.compile(r"<[^>]+>")
def clean_text(s: str) -> str:
    if not s:
        return ""
    # drop script/style blocks just in case
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", s)
    # strip all tags
    s = TAG_RE.sub(" ", s)
    # unescape entities (&nbsp;, &amp;, etc.)
    s = htmllib.unescape(s)
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_entities(text: str):
    # Allow &, Capital, Partners, Management, etc.
    candidates = re.findall(r"(?:[A-Z][A-Za-z&.-]+(?:\s+(?:&|[A-Z][A-Za-z&.-]+|Capital|Partners|Management|Advisors))*)", text)
    firms = sorted({c for c in candidates if c in FIRM_CANON})
    entities = sorted(set(candidates))[:10]
    return entities, firms

# cap at 40
def recency_score(published: datetime) -> float:
    if not published:
        return 40.0
    now = datetime.now(timezone.utc)
    hours = max(1, (now - published).total_seconds() / 3600)
    # 0–40, decays with time; ~40 if <1h, ~20 if ~1 day
    return max(0.0, 40.0 * (1.0 / (1.0 + hours / 24)))

# cap at 40
def keyword_score(text: str, prefs: Preferences) -> float:
    text_lower = text.lower()
    score = 0
    for kw in prefs.keywords:
        if kw.lower() in text_lower:
            score += 10
    for sector in prefs.sectors:
        if sector.lower() in text_lower:
            score += 6
    for geo in prefs.geos:
        if geo.lower() in text_lower:
            score += 6
    return min(score, 40)


# boost by 20, no double dip
# def relationship_score(firms: List[str]) -> float:
#     # boost if any firm hits the mocked relationship graph
#     return 20.0 if any(f in RELN for f in firms) else 0.0
# def relationship_score(text: str, firms: List[str]) -> float:
#     # boost if any firm hits the mocked relationship graph
#     text_lower = text.lower()

#     for f in firms:
#         if f.lower() in text_lower:
#             return 50.0
#     return 0.0

def relationship_score(item: DealItem, prefs: Preferences) -> float:
    """
    Up to 40 pts total:
      - 20 pts for overlap of extracted firms with user-preferred firms (10 per match, max 20)
      - 10 pts if text mentions any preferred firm name (fuzzy contains) even if extraction missed it
      - 10 pts if any extracted firm appears in RELN (known internal relationship)
    """
    text_lower = f"{item.title} {item.summary}".lower()
    preferred = {f.strip().lower() for f in (prefs.firms or []) if f.strip()}
    extracted = {f.strip().lower() for f in (item.firms or []) if f.strip()}

    # Overlap based on extraction (more robust than substring)
    overlap = len(preferred & extracted)
    overlap_score = min(20.0, 10.0 * overlap)

    # Fuzzy bonus if text mentions a preferred firm not captured by extraction
    contains_bonus = 0.0
    if preferred and not (preferred & extracted):
        if any(f in text_lower for f in preferred):
            contains_bonus = 10.0

    # Known relationship graph badge bonus
    reln_bonus = 10.0 if any(f.title() in RELN for f in item.firms or []) else 0.0

    return min(40.0, overlap_score + contains_bonus + reln_bonus)


def score_item(item: DealItem, prefs: Preferences) -> DealItem:
    base_text = f"{item.title} {item.summary}"

    # HARD GATE: suppress non-relevant items early
    if not is_relevant_private_deal(base_text):
        item.score = 0
        item.relationship_badges = []
        return item

    r = recency_score(item.published)        # 0–40
    k = keyword_score(base_text, prefs)      # 0–40
    rel = relationship_score(item, prefs)    # 0–40 (reworked below)
    total = min(int(r + k + rel), 100)

    badges = [RELN[f] for f in item.firms if f in RELN]
    item.score = total
    item.relationship_badges = badges
    return item


async def fetch_and_process_once():
    global SEEN
    for url in FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries[:20]: 
            eid = hashlib.md5((e.get("id") or e.get("link") or e.get("title")).encode()).hexdigest()
            if eid in SEEN:
                continue
            published = None
            try:
                if e.get("published"):
                    published = dtparser.parse(e.published)
                    if not published.tzinfo:
                        published = published.replace(tzinfo=timezone.utc)
            except Exception:
                published = None

            # title = e.get("title", "")
            # summary = e.get("summary", "")
            # prefer the richest available body, then normalize to plain text
            raw_title = e.get("title", "") or ""
            # summary can be HTML depending on the feed
            raw_summary = (
                (getattr(e, "summary_detail", {}) or {}).get("value")
                if getattr(e, "summary_detail", None)
                else e.get("summary", "")
            ) or e.get("summary", "") or ""
            # some feeds put body under content[0].value
            if not raw_summary and getattr(e, "content", None):
                try:
                    raw_summary = (e.content[0] or {}).get("value") or ""
                except Exception:
                    pass

            title = clean_text(raw_title)
            summary = clean_text(raw_summary)
            event_type = classify(f"{title} {summary}")
            entities, firms = extract_entities(f"{title} {summary}")
            item = DealItem(
                id=eid,
                title=title,
                link=e.get("link", ""),
                summary=summary,
                published=published,
                event_type=event_type,
                entities=entities,
                firms=firms,
            )
            item = score_item(item, USER_PREFS.get("demo", Preferences()))
            SEEN[eid] = item
            # await broadcast(item)
            # Only push to clients if it's relevant per prefs
            if item.score > 0:
                await broadcast(item)


async def poller():
    while True:
        try:
            await fetch_and_process_once()
        except Exception as ex:
            print("poller error", ex)
        await asyncio.sleep(60)  


@app.on_event("startup")
async def on_start():
    asyncio.create_task(poller())


@app.get("/health")
async def health():
    # print(SEEN)
    return {"ok": True, "items": len(SEEN)}


@app.get("/feed")
async def feed(limit: int = 50):
    # items = list(SEEN.values())
    items = [i for i in SEEN.values() if getattr(i, "score", 0) > 0]
    items.sort(key=lambda x: x.score, reverse=True)
    return items[:limit]


# @app.post("/preferences")
# async def set_prefs(p: Preferences):
#     USER_PREFS[p.user_id] = p
#     # rescore existing items for instant effect
#     for k, v in SEEN.items():
#         SEEN[k] = score_item(v, p)
#     return {"ok": True}
# @app.post("/preferences")
# async def set_prefs(p: Preferences):
#     USER_PREFS[p.user_id] = p
#     for k, v in SEEN.items():
#         SEEN[k] = score_item(v, p)
#     return {"ok": True, "applied_at": datetime.now(timezone.utc).isoformat()}
@app.post("/preferences")
async def set_prefs(p: Preferences):
    print(f"Received preferences request: {p}")  # Add logging
    USER_PREFS[p.user_id] = p
    for k, v in SEEN.items():
        SEEN[k] = score_item(v, p)
    print(f"Preferences applied for user {p.user_id}")  # Add logging
    return {"ok": True, "applied_at": datetime.now(timezone.utc).isoformat()}

# ---- WebSocket ----
async def broadcast(item: DealItem):
    stale = []
    for ws in CLIENTS:
        try:
            # await ws.send_json(DealEnvelope(data=item).model_dump())
            await ws.send_text(DealEnvelope(data=item).model_dump_json())
        except Exception:
            stale.append(ws)
    for s in stale:
        try:
            CLIENTS.remove(s)
        except ValueError:
            pass


# @app.websocket("/ws")
# async def ws_endpoint(ws: WebSocket):
#     await ws.accept()
#     CLIENTS.append(ws)
#     # # send current top items on connect
#     # for itm in list(SEEN.values())[:30]:
#     # send current top relevant items on connect
#     top = [i for i in SEEN.values() if getattr(i, "score", 0) > 0]
#     top.sort(key=lambda x: x.score, reverse=True)
#     for itm in top[:20]:
#         # await ws.send_json(DealEnvelope(data=itm).model_dump())
#         await ws.send_text(DealEnvelope(data=itm).model_dump_json()) 
#     try:
#         while True:
#             await ws.receive_text() # keep alive; ignore content
#     except WebSocketDisconnect:
#         try:
#             CLIENTS.remove(ws)
#         except ValueError:
#             pass
@app.get("/")
async def root():
    return {"ok": True, "service": "deal-feed"}

# @app.websocket("/ws")
# async def ws_endpoint(ws: WebSocket):
#     await ws.accept()
#     CLIENTS.append(ws)
#     try:
#         top = [i for i in SEEN.values() if getattr(i, "score", 0) > 0]
#         # top.sort(by=lambda x: x.score, reverse=True)  # or key=
#         top.sort(key=lambda x: getattr(x, "score", 0), reverse=True)
#         for itm in top[:20]:
#             await ws.send_text(DealEnvelope(data=itm).model_dump_json())
#     except Exception as e:
#         print("initial send error:", repr(e))
#     try:
#         while True:
#             await ws.receive_text()  # keepalive
#     except WebSocketDisconnect:
#         try:
#             CLIENTS.remove(ws)
#         except ValueError:
#             pass
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    # ---- (Optional) origin check BEFORE accept ----
    if ALLOWED_ORIGINS is not None:
        origin = ws.headers.get("origin")
        ok = False
        if origin:
            host = urlparse(origin).hostname or ""
            ok = origin in ALLOWED_ORIGINS or any(host.endswith(sfx) for sfx in ALLOWED_SUFFIXES)
        if not ok:
            # IMPORTANT: close AND RETURN so we never hit receive_text()
            await ws.close(code=1008)  # policy violation
            return

    # ---- Accept FIRST, then everything else ----
    await ws.accept()
    CLIENTS.append(ws)

    # ---- Initial send guarded so one bad item doesn't kill the socket ----
    try:
        top = [i for i in SEEN.values() if getattr(i, "score", 0) > 0]
        top.sort(key=lambda x: getattr(x, "score", 0), reverse=True)  # key=, not by=
        for itm in top[:20]:
            # Use JSON string to avoid datetime serialization issues
            await ws.send_text(DealEnvelope(data=itm).model_dump_json())
    except Exception as e:
        print("initial send error:", repr(e))  # keep the connection alive

    # ---- Receive loop ----
    try:
        while True:
            try:
                _ = await ws.receive_text()  # keepalive; ignore payload
            except WebSocketDisconnect:
                break
    finally:
        # Always remove the client once we're done
        try:
            CLIENTS.remove(ws)
        except ValueError:
            pass