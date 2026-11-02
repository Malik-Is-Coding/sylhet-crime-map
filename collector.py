"""FREE collector: no AI, no API key. Reads public news RSS feeds, finds crime keywords
and one Sylhet Division upazila name in each headline, and writes reports.json.
Upload this over the old collector.py in your repository.
"""
import os, json, hashlib, datetime as dt
from urllib.parse import quote
import feedparser

EXTRA_FEEDS = []  # add a paper's own RSS URL here if it has one

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

# One search per upazila (English and Bangla), so headlines naming a specific upazila are found.
FEEDS = []
for en, bn in K.values():
    for q in (f"{en} police", f"{bn} পুলিশ"):
        FEEDS.append(f"https://news.google.com/rss/search?q={quote(q)}+when:3d&hl=bn&gl=BD&ceid=BD:bn")

# (category, severity, keywords). Highest severity found in the headline wins.
CRIMES = [("Murder",4,["হত্যা","খুন","murder"]),("Kidnapping",4,["অপহরণ","kidnap","abduct"]),
 ("Rape",3,["ধর্ষণ","rape"]),("Arson",3,["অগ্নিসংযোগ","arson"]),
 ("Robbery",2,["ডাকাতি","ছিনতাই","robbery","mugging"]),("Fraud",2,["প্রতারণা","জালিয়াতি","fraud"]),
 ("Assault",2,["মারধর","হামলা","সংঘর্ষ","assault"]),("Smuggling",2,["চোরাচালান","smuggling"]),
 ("Drugs",2,["ইয়াবা","গাঁজা","মাদক"]),("Theft",1,["চুরি","theft"])]

DB = "reports.json"
db = json.load(open(DB, encoding="utf-8")) if os.path.exists(DB) else []
seen = {r["id"] for r in db}
added = 0
checked = 0

for url in FEEDS + EXTRA_FEEDS:
    for e in feedparser.parse(url).entries:
        rid = hashlib.sha1(e.link.encode()).hexdigest()[:12]
        if rid in seen:
            continue
        seen.add(rid)
        checked += 1
        title, low = e.title, e.title.lower()
        places = [k for k, (en, bn) in K.items() if en.lower() in low or bn in title]
        crime = next(((c, s) for c, s, words in sorted(CRIMES, key=lambda x: -x[1])
                      if any(w in low or w in title for w in words)), None)
        if len(places) != 1 or not crime:   # unclear place or no crime word: skip
            continue
        d = dt.date(*e.published_parsed[:3]).isoformat() if e.get("published_parsed") else dt.date.today().isoformat()
        # The headline is generic on purpose, so names of victims or suspects are not republished.
        db.append({"id": rid, "u": places[0], "sev": crime[1], "cat": crime[0], "d": d,
                   "t": f"{crime[0]} reported in {K[places[0]][0]}",
                   "src": e.get("source", {}).get("title", "News portal"), "l": e.link, "status": "approved"})
        added += 1

db = sorted(db, key=lambda r: r["d"], reverse=True)[:2000]
json.dump(db, open(DB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{checked} new headlines checked, {added} added, {len(db)} stored")
