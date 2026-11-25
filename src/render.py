#!/usr/bin/env python3
"""Render index.html for the iPad dashboard. Inputs: data/personal.jsonl, data/work.jsonl (from fetch_cal.sh),
Dinner Menu project's menu-history.md, Open-Meteo weather. Output: out/index.html"""
import json, re, os, html, datetime as dt, urllib.request
HERE=os.path.dirname(os.path.abspath(__file__))
IST=dt.timezone(dt.timedelta(hours=5,minutes=30))
MENU=os.path.join(HERE,'data','menu.md')  # latest week only, pushed weekly by Hark
now=dt.datetime.now(IST); today=now.date()
e=html.escape

def parse_dt(v):
    m=re.match(r'\w{3} (\d{4}-\d{2}-\d{2}) (\d{1,2}:\d{2} [AP]M)',v)
    if m: return dt.datetime.strptime(m.group(1)+' '+m.group(2),'%Y-%m-%d %I:%M %p')
    m=re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})',v)
    if m: return dt.datetime.strptime(m.group(1)+' '+m.group(2),'%Y-%m-%d %H:%M')
    return dt.datetime.strptime(v[:10],'%Y-%m-%d')

events=[]
for f in ('personal','work'):
    p=os.path.join(HERE,'data',f+'.jsonl')
    if not os.path.exists(p): continue
    for line in open(p):
        if not line.strip(): continue
        x=json.loads(line); st=parse_dt(x['st']); en=parse_dt(x['en'])
        if x['allday']:
            d=st.date(); last=en.date()-dt.timedelta(days=1)
            while d<=last:
                events.append(dict(tag=x['tag'],s=x['s'],d=d,t=None)); d+=dt.timedelta(days=1)
        else:
            events.append(dict(tag=x['tag'],s=x['s'],d=st.date(),t=st))
# dedupe
seen=set(); ev=[]
for x in sorted(events,key=lambda x:(x['d'],x['t'] is not None,x['t'] or dt.datetime.min,x['s'])):
    k=(x['d'],x['t'],x['s'])
    if k in seen: continue
    seen.add(k); ev.append(x)
week_end=today+dt.timedelta(days=7)
wk=[x for x in ev if today<=x['d']<week_end]
later=[x for x in ev if week_end<=x['d']<=today+dt.timedelta(days=30) and x['t'] is None]

def fmt_t(t):
    return t.strftime('%I:%M %p').lstrip('0')
blocks=[]; budget=14; used=0
days=sorted(set(x['d'] for x in wk))
for d in days:
    items=[x for x in wk if x['d']==d]
    if used+1>=budget: break
    lab=('Today &middot; ' if d==today else ('Tomorrow &middot; ' if d==today+dt.timedelta(days=1) else ''))+d.strftime('%a %d').replace(' 0',' ')
    rows=[]
    for x in items:
        if used+1+len(rows)+1>budget: break
        t='All day' if x['t'] is None else fmt_t(x['t'])
        rows.append('<div class="ev"><span class="dot %s"></span><span class="t">%s</span>%s</div>'%(x['tag'],t,e(x['s'])))
    used+=1+len(rows)
    blocks.append('<div class="dayblock%s"><div class="dlabel%s">%s</div>%s</div>'%(' today' if d==today else '',' today' if d==today else '',lab,''.join(rows)))
if not blocks: blocks.append('<div class="dayblock"><div class="ev">Nothing on the calendar this week</div></div>')
# coming up: unique names, first 3
cu=[]; names=set()
for x in later:
    n=re.sub(r'\s*\(.*?\)','',x['s'])
    if n in names: continue
    names.add(n); cu.append('%s %s'%(e(n),x['d'].strftime('%d %b').lstrip('0')))
    if len(cu)==2: break
keys='<div class="keys"><b>Coming up:</b> %s</div>'%' &middot; '.join(cu) if cu else ''

# menu
menu=[]; wk_label=''
if os.path.exists(MENU):
    txt=open(MENU).read()
    m=re.search(r'## Week of (\d{4}-\d{2}-\d{2}).*?\n(.*?)(?=\n## |\Z)',txt,re.S)
    if m:
        wk_label=m.group(1); body=m.group(2)
        fm=re.search(r'Final:\s*\n(.*?)(?:\n\(|\n\n|\Z)',body,re.S)
        part=fm.group(1) if fm else body
        for line in part.splitlines():
            mm=re.match(r'\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s*:\s*(.+)',line)
            if mm: menu.append((mm.group(1),' + '.join(p.strip()[:1].upper()+p.strip()[1:] for p in re.sub(r'\s*\(.*?\)\s*$','',mm.group(2)).split('+'))))
tdn=today.strftime('%a')
mrows=''.join('<div class="mrow%s"><div class="md">%s</div><div><div class="mdish">%s</div></div></div>'%(' today' if d==tdn else '',d,e(x)) for d,x in menu) or '<div class="mrow"><div class="mdish">Menu coming soon</div></div>'

# weather
WMO={0:'Sunny',1:'Mostly sunny',2:'Partly cloudy',3:'Cloudy',45:'Foggy',48:'Foggy',51:'Light drizzle',53:'Drizzle',55:'Drizzle',61:'Light rain',63:'Rain',65:'Heavy rain',80:'Showers',81:'Showers',82:'Heavy showers',95:'Thunderstorms',96:'Thunderstorms',99:'Thunderstorms'}
wx_now='';wx_days=''
try:
    u='https://api.open-meteo.com/v1/forecast?latitude=12.9716&longitude=77.5946&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset,uv_index_max&timezone=Asia%2FKolkata&forecast_days=6'
    wf=os.path.join(HERE,'data','weather.json')
    w=json.load(open(wf)) if os.path.exists(wf) and json.load(open(wf)).get('_fetched',0)>now.timestamp()-24*3600 else json.load(urllib.request.urlopen(u,timeout=20))
    dl=w['daily']
    # align daily arrays to today
    if dl['time'][0]!=today.isoformat() and today.isoformat() in dl['time']:
        i0=dl['time'].index(today.isoformat()); dl={k:v[i0:] for k,v in dl.items()}
    rain=' &middot; %d%% rain'%dl['precipitation_probability_max'][0] if dl['precipitation_probability_max'][0]>=40 else ''
    wx_now='<div class="wx-temp">%d&deg;</div><div class="wx-desc">Bengaluru &middot; %s &middot; %d&deg; / %d&deg;%s</div>'%(round(w['current']['temperature_2m']),WMO.get(w['current']['weather_code'],''),round(dl['temperature_2m_min'][0]),round(dl['temperature_2m_max'][0]),rain)
    for i in (1,2):
        dn=dt.date.fromisoformat(dl['time'][i]).strftime('%a')
        wx_days+='<div class="wx-d"><b>%s</b>%s %d&deg; / %d&deg;</div>'%(dn,WMO.get(dl['weather_code'][i],''),round(dl['temperature_2m_min'][i]),round(dl['temperature_2m_max'][i]))
except Exception as ex:
    wx_now='<div class="wx-desc">Weather unavailable</div>'


# ---------------- slideshow pages ----------------
def J(n):
    p=os.path.join(HERE,'data',n)
    try: return json.load(open(p))
    except Exception: return None
def ts(t): return dt.datetime.fromtimestamp(t,IST)
def card(cls,title,body,sub=''):
    return '<div class="panel full %s"><div class="ph">%s<span class="phs">%s</span></div><div class="pb">%s</div></div>'%(cls,title,sub,body)
slides=[]
top='''<div class="top"><div><div class="day">%s</div><div class="date">%s</div></div>
<div class="wx"><div class="wx-now">%s</div><div class="wx-days">%s</div></div></div>'''%(now.strftime('%A'),now.strftime('%d %B %Y').lstrip('0'),wx_now,wx_days)
home=top+'''<div class="row">
<div class="panel left menu"><div class="ph">Dinner Menu</div><div class="pb">%s</div></div>
<div class="panel right cal"><div class="ph">This Week</div><div class="pb">%s%s
<div class="legend"><span><span class="dot p"></span>Personal</span><span><span class="dot w"></span>Work</span><span><span class="dot h"></span>Holidays</span></div></div></div>
</div>'''%(mrows,''.join(blocks),keys)
slides.append(('Home',home))

# Quote (replaces Gita verse)
qz=J('quotes.json')
if qz:
    SL=today.toordinal()*2+(1 if now.hour>=12 else 0)
    q=qz[SL%len(qz)]
    b='<div class="qt-mk">&ldquo;</div><div class="qt-t">%s</div><div class="qt-by">&mdash; %s</div>'%(e(q[1]),e(q[0]))
    slides.append(('Quote',card('verse','Thought for the Day',b)))

# Headlines
nz=J('news.json')
if nz:
    b=''.join('<div class="nw"><div class="nn">%d</div><div><div class="nt">%s</div><div class="ns">%s</div></div></div>'%(k+1,e(x['t']),e(x['s'])) for k,x in enumerate(nz['items'][:5]))
    slides.append(('News',card('news','Top Headlines',b,'India &amp; world &middot; as of '+ts(nz['at']).strftime('%I:%M %p, %d %b').lstrip('0'))))

# Markets
def spark(v,up):
    if len(v)<2: return ''
    lo,hi=min(v),max(v); W,H=260,104; rng=(hi-lo) or 1
    pts=' '.join('%.1f,%.1f'%(i*W/(len(v)-1),H-3-(x-lo)/rng*(H-6)) for i,x in enumerate(v))
    return '<svg width="%d" height="%d" viewBox="0 0 %d %d"><polyline fill="none" stroke="%s" stroke-width="2.5" points="%s"/></svg>'%(W,H,W,H,'#2E9E62' if up else '#D2493B',pts)
mz=J('markets.json')
if mz:
    tl=[]
    for x in mz['items']:
        ch=x['price']-x['prev']; pc=ch/x['prev']*100; up=ch>=0
        dec=2 if x['price']<1000 else 2
        tl.append('<div class="mk"><div class="mkn">%s</div><div class="mkp">%s%s</div><div class="mkc %s">%s%s (%s%.2f%%)</div>%s<div class="mka">%s &middot; 1-month trend</div></div>'%(
            e(x['name']),'<span class="mku">%s</span>'%e(x['unit']) if x['unit'] else '','{:,.2f}'.format(x['price']),'up' if up else 'dn',
            '&#9650; ' if up else '&#9660; ','{:,.2f}'.format(abs(ch)),'+' if up else '-',abs(pc),spark(x['spark'],up),ts(x['at']).strftime('%d %b, %I:%M %p').lstrip('0').replace(', 0',', ')))
    slides.append(('Markets',card('mkts','Markets Close','<div class="mkw">%s</div>'%''.join(tl),'Last traded price vs previous close')))

# Air & weather
az=J('air.json')
try:
    WMOI={0:'&#9728;',1:'&#127780;',2:'&#9925;',3:'&#9729;',45:'&#127787;',48:'&#127787;',51:'&#127782;',53:'&#127782;',55:'&#127782;',61:'&#127783;',63:'&#127783;',65:'&#127783;',80:'&#127782;',81:'&#127783;',82:'&#127783;',95:'&#9928;',96:'&#9928;',99:'&#9928;'}
    a=az['current']['us_aqi']
    bands=[(50,'Good','#3FA36B','Air is clean. Great for outdoor tennis.'),(100,'Moderate','#E0A12B','Fine for most. Sensitive people take it easy outdoors.'),(150,'Unhealthy for sensitive','#E07A4C','Run the purifier; limit long outdoor exertion.'),(200,'Unhealthy','#D2493B','Keep windows shut and the purifier on.'),(300,'Very unhealthy','#8E3B9C','Stay indoors with the purifier on.'),(999,'Hazardous','#7A1F2B','Stay indoors.')]
    lab,col,tip=[(l,c,t) for m,l,c,t in bands if a<=m][0]
    cur=w['current']; d0=dl
    hm=lambda s:dt.datetime.strptime(s,'%Y-%m-%dT%H:%M').strftime('%I:%M %p').lstrip('0')
    aqi='<div class="aq" style="background:%s"><div class="aql">Air Quality &middot; US AQI</div><div class="aqn">%d</div><div class="aqb">%s</div><div class="aqp">PM2.5 %.0f &middot; PM10 %.0f &micro;g/m&sup3;</div><div class="aqt">%s</div></div>'%(col,a,lab,az['current']['pm2_5'],az['current']['pm10'],tip)
    stats=[('Feels like','%d&deg;'%round(cur['apparent_temperature'])),('Humidity','%d%%'%cur['relative_humidity_2m']),('Wind','%d km/h'%round(cur['wind_speed_10m'])),('UV today','%.0f'%d0['uv_index_max'][0]),('Sunrise',hm(d0['sunrise'][0])),('Sunset',hm(d0['sunset'][0]))]
    now_c='<div class="wn"><div class="wnt">%d&deg; <span>%s</span></div><div class="wst">%s</div></div>'%(round(cur['temperature_2m']),WMO.get(cur['weather_code'],''),''.join('<div class="st"><div class="stl">%s</div><div class="stv">%s</div></div>'%s for s in stats))
    fc=''.join('<div class="fd%s"><div class="fdn">%s</div><div class="fdw">%s</div><div class="fdt">%d&deg; <span>/ %d&deg;</span></div><div class="fdr">Rain %d%%</div></div>'%(
        ' today' if i==0 else '','Today' if i==0 else dt.date.fromisoformat(d0['time'][i]).strftime('%a'),WMO.get(d0['weather_code'][i],''),round(d0['temperature_2m_max'][i]),round(d0['temperature_2m_min'][i]),d0['precipitation_probability_max'][i]) for i in range(min(6,len(d0['time']))))
    slides.append(('Air',card('air','Bengaluru Air &amp; Weather','<div class="awtop">%s%s</div><div class="fc">%s</div>'%(aqi,now_c,fc))))
except Exception as ex:
    print('air slide skipped',ex)

# Kannada
kz=J('kannada.json')
if kz:
    SL=today.toordinal()*2+(1 if now.hour>=12 else 0)
    k=kz[SL%len(kz)]
    main='<div class="kn-w">%s</div><div class="kn-m">%s</div><div class="kn-ex"><div class="kn-el">Use it</div><div class="kn-et">%s</div><div class="kn-ee">%s</div></div>'%(e(k[1]),e(k[2]),e(k[4]),e(k[5]))
    past=''.join('<div class="kr"><div class="krw">%s</div><div class="krm">%s</div></div>'%(e(p[1]),e(p[2])) for p in [kz[(SL-i)%len(kz)] for i in (1,2,3,4,5)])
    b='<div class="kn-row"><div class="kn-main">%s</div><div class="kn-rev"><div class="kn-rh">Revise</div>%s</div></div>'%(main,past)
    slides.append(('Kannada',card('kan','Kannada Word of the Day',b)))


# Wedding countdown
wz=J('wedding.json')
if wz:
    try:
        import base64
        def b64(f,mt):
            import hashlib
            return 'wed/%s?v=%s'%(f,hashlib.md5(open(os.path.join(HERE,'..','wed',f),'rb').read()).hexdigest()[:8])  # images live in the repo's wed/ folder
        wd=dt.date.fromisoformat(wz['date']) if wz.get('date') else None
        days=(wd-today).days if wd else None
        logo='<img class="wd-logo" src="%s">'%b64(wz['logo'],'image/png') if wz.get('logo') else '<div class="wd-mono">%s</div>'%e(wz.get('monogram',''))
        big='%d'%days if days is not None and days>0 else ('Today!' if days is not None and days<=0 else '&mdash;')
        lbl='days to go' if days and days>1 else ('day to go' if days==1 else '')
        when=e(wz.get('date_label') or (wd.strftime('%A, %d %B %Y').replace(' 0',' ') if wd else 'Date to be announced'))
        wx=wz.get('weather') or {}
        wxv='%s<span>%s</span>'%(e(wx['hi_lo']),e(wx.get('desc',''))) if wx.get('hi_lo') else 'N/A'
        wxs=e(wx.get('basis','')) or 'Forecast opens 16 days out'
        rs=wz.get('rsvp') or {}
        rsv=('%s<span> / %s</span>'%(rs['yes'],rs['invited'])) if rs.get('yes') is not None else 'N/A'
        rss=('%s awaiting'%rs['pending']) if rs.get('pending') is not None else 'Not available yet'
        ven=e(wz.get('venue') or 'Venue to be announced'); vs=e(wz.get('venue_city',''))
        tiles=''.join('<div class="wt %s"><div class="wtl">%s</div><div class="wtv">%s</div><div class="wts">%s</div></div>'%t for t in [('wt-v','Venue',ven,vs),('wt-r','RSVP Guest Count',rsv,rss),('wt-w','Weather on the day',wxv,wxs)])
        bg=' style="background-image:url(%s)"'%b64(wz['background'],'image/jpeg') if wz.get('background') else ''
        b='<div class="wd"%s><div class="wd-top">%s</div><div class="wd-n">%s</div><div class="wd-l">%s</div><div class="wd-d">%s</div><div class="wd-tiles">%s</div></div>'%(bg,logo,big,lbl,when,tiles)
        slides.append(('Wedding',card('wed',e(wz.get('title','Wedding Countdown')),b)))
    except Exception as ex: print('wedding slide skipped',ex)

# vouchers / gift cards
vz=J('vouchers.json') or []
vz=[v for v in vz if dt.date.fromisoformat(v['expiry'])>=today]
vz.sort(key=lambda v:v['expiry'])
if vz:
    rows=''
    for v in vz[:7]:
        ex=dt.date.fromisoformat(v['expiry']); dl=(ex-today).days
        lv='red' if dl<=30 else ('amb' if dl<=90 else 'grn')
        nm=e(re.sub(r' (membership coupon|voucher|gift card)$','',v['name'],flags=re.I))
        tag=('<span class="vtag">%s\'s</span>'%e(v['owner'])) if v.get('owner') else ''
        rows+='<div class="vr"><div class="vn">%s%s</div><div class="vv">%s%s</div><div class="ve">%s</div><div class="vd %s"><b>%d</b> days left</div></div>'%(nm,tag,v.get('currency','₹'),'{:,}'.format(v['value']),ex.strftime('%d %b %Y').lstrip('0'),lv,dl)
    tot=sum(v['value'] for v in vz if v.get('currency','₹')=='₹')
    oth={}
    for v in vz:
        c=v.get('currency','₹')
        if c!='₹': oth[c]=oth.get(c,0)+v['value']
    totx=''.join(' + %s%s'%(c,'{:,}'.format(n)) for c,n in oth.items())
    slides.append(('Vouchers',card('vch','Active Vouchers & Gift Cards','<div class="vhd"><span class="vn">Voucher</span><span class="vv">Value</span><span class="ve">Expires</span><span class="vd">Days left</span></div>'+rows,'%d active · ₹%s%s total'%(len(vz),'{:,}'.format(tot),totx))))

# airline miles (balances exactly as in the Agent Context doc)
mz=J('miles.json') or []
BRAND=[('air india','#D71921'),('british','#075AAA'),('qatar','#5C0632'),('flying blue','#00A1DE'),('klm','#00A1DE'),('air france','#002157'),('virgin','#DA0530'),('united','#005DAA'),('singapore','#F99F1C'),('krisflyer','#F99F1C'),('jal','#C8102E'),('japan','#C8102E'),('emirates','#D71921'),('lufthansa','#05164D'),('indigo','#001B94'),('alaska','#01426A')]
if mz:
    rows=''
    for m in mz:
        col=next((c for k,c in BRAND if k in m['program'].lower()),'#22262E')
        rows+='<div class="vr mr"><div class="vn" style="color:%s">%s</div><div class="mb">%s</div><div class="me">%s</div></div>'%(col,e(m['program']),e(m['balance']),e(m.get('expiry_label') or '—'))
    slides.append(('Miles',card('mls','Airline Miles','<div class="vhd"><span class="vn">Programme</span><span class="mb">Balance</span><span class="me">Expiry</span></div>'+rows,'%d programmes'%len(mz))))

ACTIVE=int(os.environ.get('SLIDE','0'))
css=open(os.path.join(HERE,'style.css.part')).read()
sl=''.join('<div class="slide%s">%s</div>'%(' on' if k==ACTIVE else '',s) for k,(n,s) in enumerate(slides))
dots=''.join('<span class="sd%s"></span>'%(' on' if k==ACTIVE else '') for k in range(len(slides)))
JS='''<script>
(function(){var S=document.querySelectorAll('.slide'),D=document.querySelectorAll('.sd'),P=document.getElementById('pz'),i=%d,paused=false,last=new Date().getTime(),x0=null,y0=null;
function go(n){S[i].className='slide';D[i].className='sd';i=(n+S.length)%%S.length;S[i].className='slide on';D[i].className='sd on';last=new Date().getTime();}
setInterval(function(){if(!paused&&new Date().getTime()-last>=15000)go(i+1);},1000);
document.addEventListener('touchstart',function(ev){var t=ev.touches[0];x0=t.clientX;y0=t.clientY;},false);
document.addEventListener('touchmove',function(ev){ev.preventDefault();},false);
document.addEventListener('touchend',function(ev){if(x0===null)return;var t=ev.changedTouches[0],dx=t.clientX-x0,dy=t.clientY-y0;x0=null;
 if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)){go(dx<0?i+1:i-1);}else if(Math.abs(dx)<15&&Math.abs(dy)<15){paused=!paused;P.style.display=paused?'inline-block':'none';last=new Date().getTime();}},false);
document.addEventListener('click',function(){if(!('ontouchstart' in window)){paused=!paused;P.style.display=paused?'inline-block':'none';}},false);
setInterval(function(){if(!paused)location.reload(true);},1800000);
})();
</script>'''%ACTIVE
page='''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="robots" content="noindex, nofollow">
<title>Rao Home</title>
%s
</head><body><div class="wrap">
<div class="stage">%s</div>
<div class="foot"><span class="dots">%s</span><span id="pz" class="pz">&#10074;&#10074; Paused &middot; tap to resume</span><span class="upd">Updated %s</span></div></div>%s</body></html>'''%(css,sl,dots,now.strftime('%a %d %b, %I:%M %p').replace(' 0',' '),JS)
os.makedirs(os.path.join(HERE,'out'),exist_ok=True)
open(os.path.join(HERE,'out','index.html' if 'SLIDE' not in os.environ else 'slide-%d.html'%ACTIVE),'w').write(page)
print('ok', len(menu),'menu rows', len(wk),'week events', len(slides),'slides:',' '.join(n for n,_ in slides))
