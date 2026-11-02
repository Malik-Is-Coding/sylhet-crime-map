"""Collects Sylhet Division crime news from public RSS feeds, sorts each item with
Claude, and writes reports.json for the map page.
Run:  pip install feedparser anthropic ; set ANTHROPIC_API_KEY ; python collector.py
"""
import os, json, re, hashlib, time, datetime as dt
from urllib.parse import quote
import feedparser, anthropic

# Public RSS feeds. Google News RSS gathers many Bangladeshi papers and portals.
# Add any paper's own RSS URL here too (check each site's terms of use first).
QUERIES = ["Sylhet police", "Moulvibazar police", "Habiganj police", "Sunamganj police",
           "সিলেট হত্যা", "সিলেট ডাকাতি", "মৌলভীবাজার হত্যা", "হবিগঞ্জ হত্যা", "সুনামগঞ্জ হত্যা"]
FEEDS = [f"https://news.google.com/rss/search?q={quote(q)}+when:2d&hl=bn&gl=BD&ceid=BD:bn" for q in QUERIES]
EXTRA_FEEDS = []  # e.g. ["https://example-paper.com/rss"]

# key -> (English, Bangla). Keys match the map page.
K = {"sadar":("Sylhet Sadar","সিলেট সদর"),"jaintiapur":("Jaintiapur","জৈন্তাপুর"),"gowainghat":("Gowainghat","গোয়াইনঘাট"),
"companiganj":("Companiganj","কোম্পানীগঞ্জ"),"kanaighat":("Kanaighat","কানাইঘাট"),"zakiganj":("Zakiganj","জকিগঞ্জ"),
"beanibazar":("Beanibazar","বিয়ানীবাজার"),"golapganj":("Golapganj","গোলাপগঞ্জ"),"fenchuganj":("Fenchuganj","ফেঞ্চুগঞ্জ"),
"balaganj":("Balaganj","বালাগঞ্জ"),"dsurma":("Dakshin Surma","দক্ষিণ সুরমা"),"osmani":("Osmani Nagar","ওসমানী নগর"),
"bishwanath":("Bishwanath","বিশ্বনাথ"),
"su_dharmapasha":("Dharmapasha","ধর্মপাশা"),"su_tahirpur":("Tahirpur","তাহিরপুর"),"su_bishwamvarpur":("Bishwamvarpur","বিশ্বম্ভরপুর"),
"su_dowarabazar":("Dowarabazar","দোয়ারাবাজার"),"su_jamalganj":("Jamalganj","জামালগঞ্জ"),"su_sullah":("Sullah","শাল্লা"),
"su_sunamganjsadar":("Sunamganj Sadar","সুনামগঞ্জ সদর"),"su_chhatak":("Chhatak","ছাতক"),"su_derai":("Derai","দিরাই"),
"su_shantiganj":("Shantiganj","শান্তিগঞ্জ"),"su_dakshinsunamganj":("Dakshin Sunamganj","দক্ষিণ সুনামগঞ্জ"),"su_jagannathpur":("Jagannathpur","জগন্নাথপুর"),
"ha_ajmiriganj":("Ajmiriganj","আজমিরীগঞ্জ"),"ha_baniachong":("Baniachong","বানিয়াচং"),"ha_nabiganj":("Nabiganj","নবীগঞ্জ"),
"ha_lakhai":("Lakhai","লাখাই"),"ha_habiganjsadar":("Habiganj Sadar","হবিগঞ্জ সদর"),"ha_bahubal":("Bahubal","বাহুবল"),
"ha_madhabpur":("Madhabpur","মাধবপুর"),"ha_shaistaganj":("Shaistaganj","শায়েস্তাগঞ্জ"),"ha_chunarughat":("Chunarughat","চুনারুঘাট"),
"mo_rajnagar":("Rajnagar","রাজনগর"),"mo_kulaura":("Kulaura","কুলাউড়া"),"mo_barlekha":("Barlekha","বড়লেখা"),
"mo_moulvibazarsadar":("Moulvibazar Sadar","মৌলভীবাজার সদর"),"mo_juri":("Juri","জুড়ী"),"mo_sreemangal":("Sreemangal","শ্রীমঙ্গল"),
"mo_kamalganj":("Kamalganj","কমলগঞ্জ")}
DISTRICTS = ["sylhet","moulvibazar","habiganj","sunamganj","সিলেট","মৌলভীবাজার","হবিগঞ্জ","সুনামগঞ্জ"]

SYSTEM = ("You read a news item from Bangladesh and extract ONE crime incident in Sylhet Division. Reply with JSON only: "
 '{"is_crime":bool,"upazila":key or null,"severity":1-4,"category":"short English","headline":"neutral English headline, max 100 chars, '
 'never include names of victims or suspects","confidence":0-1}. Severity: 1 minor theft; 2 robbery, fraud, assault, smuggling; '
 "3 rape, arson, grievous harm; 4 murder, kidnapping. upazila must be exactly one of: " + ", ".join(K) +
 ". Use null if the upazila is not clear. is_crime=false for opinion pieces, politics, sports, accidents without crime, "
 "old-case court verdicts, and anything outside Sylhet Division.")

DB, MAX_CALLS = "reports.json", 60
db = json.load(open(DB, encoding="utf-8")) if os.path.exists(DB) else []
seen = {r["id"] for r in db}
client, calls = anthropic.Anthropic(), 0

def relevant(t):
    tl = t.lower()
    return any(e.lower() in tl or b in t for e, b in K.values()) or any(d in tl or d in t for d in DISTRICTS)

for url in FEEDS + EXTRA_FEEDS:
    for e in feedparser.parse(url).entries:
        rid = hashlib.sha1(e.link.encode()).hexdigest()[:12]
        text = (e.title + "\n" + re.sub("<[^>]+>", " ", e.get("summary", ""))).strip()
        if rid in seen or not relevant(text) or calls >= MAX_CALLS:
            continue
        seen.add(rid); calls += 1
        try:
            m = client.messages.create(model="claude-sonnet-5-5", max_tokens=300, system=SYSTEM,
                                       messages=[{"role": "user", "content": text}])
            j = json.loads(re.sub(r"^```json|```$", "", m.content[0].text.strip()).strip())
        except Exception as ex:
            print("skip", rid, ex); continue
        if not j.get("is_crime") or j.get("upazila") not in K:
            continue
        d = dt.date(*e.published_parsed[:3]).isoformat() if e.get("published_parsed") else dt.date.today().isoformat()
        db.append({"id": rid, "u": j["upazila"], "sev": int(j["severity"]), "cat": j["category"], "d": d,
                   "t": j["headline"], "src": e.get("source", {}).get("title", "News portal"), "l": e.link,
                   # only high-confidence items go live; the rest wait for a human to change "pending" to "approved"
                   "status": "approved" if j.get("confidence", 0) >= 0.8 else "pending"})
        time.sleep(0.5)

db = sorted(db, key=lambda r: r["d"], reverse=True)[:2000]
json.dump(db, open(DB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{calls} items checked, {len(db)} stored")
