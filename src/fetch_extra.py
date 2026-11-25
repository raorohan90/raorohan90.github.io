#!/usr/bin/env python3
"""Fetch slideshow data: top headlines, markets. Writes data/news.json, data/markets.json.
Each source fails soft (keeps the previous file). Weather + AQI: fetch_weather.py."""
import json, os, re, html, datetime as dt, urllib.request
HERE=os.path.dirname(os.path.abspath(__file__)); D=os.path.join(HERE,'data')
IST=dt.timezone(dt.timedelta(hours=5,minutes=30)); _now=dt.datetime.now(IST); today=_now.date()
SLOT=today.toordinal()*2+(1 if _now.hour>=12 else 0)  # new pick each morning/evening refresh
UA={'User-Agent':'Mozilla/5.0 (Macintosh) dashboard'}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=20).read().decode('utf-8')
def save(n,o): json.dump(o,open(os.path.join(D,n),'w'),ensure_ascii=False)

try:
    t=get('https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en')
    items=[]
    for it in re.findall(r'<item>(.*?)</item>',t,re.S):
        ti=html.unescape(re.search(r'<title>(.*?)</title>',it,re.S).group(1))
        src=re.search(r'<source[^>]*>(.*?)</source>',it,re.S)
        src=html.unescape(src.group(1)) if src else ''
        if src and ti.endswith(' - '+src): ti=ti[:-len(src)-3]
        items.append(dict(t=ti.strip(),s=src))
        if len(items)==5: break
    if len(items)>=3: save('news.json',dict(at=int(dt.datetime.now(IST).timestamp()),items=items)); print('news',len(items))
except Exception as ex: print('news FAIL',ex)

SYMS=[('^NSEI','Nifty 50',''),('^BSESN','Sensex',''),('^NSEBANK','Bank Nifty',''),('INR=X','USD / INR','₹'),('GBPINR=X','GBP / INR','₹'),('GC=F','Gold','$/oz ')]
out=[]
for s,name,unit in SYMS:
    try:
        r=json.loads(get('https://query1.finance.yahoo.com/v8/finance/chart/%s?range=1mo&interval=1d'%urllib.request.quote(s)))['chart']['result'][0]
        m=r['meta']; closes=[c for c in r['indicators']['quote'][0]['close'] if c is not None]
        price=m['regularMarketPrice']; prev=closes[-2] if len(closes)>1 else m.get('chartPreviousClose')
        out.append(dict(name=name,unit=unit,price=price,prev=prev,spark=closes[-22:],
            at=m['regularMarketTime']))
    except Exception as ex: print('mkt FAIL',s,ex)
if len(out)>=3: save('markets.json',dict(at=int(dt.datetime.now(IST).timestamp()),items=out)); print('markets',len(out))
