#!/usr/bin/env python3
"""Calendars from Google 'secret address in iCal format' URLs, kept as GitHub repo secrets (never in code).
ICAL_P = personal calendars, ICAL_W = work calendars, ICAL_H = holiday calendars; each may hold several URLs separated by spaces or newlines.
Writes data/personal.jsonl (tags p, h) and data/work.jsonl (tags w, h) in the same format Hark's fetch_cal.sh used.
With no secrets set it does nothing, and the files Hark pushes are used instead. A feed that fails keeps the old file."""
import os, sys, json, datetime as dt, urllib.request, subprocess
P=os.environ.get('ICAL_P','').split(); W=os.environ.get('ICAL_W','').split(); H=os.environ.get('ICAL_H','').split()
if not (P or W):
    print('ical: no secrets set, using pushed calendar files'); sys.exit(0)
subprocess.run([sys.executable,'-m','pip','install','-q','icalendar','recurring-ical-events'],check=True)
import icalendar, recurring_ical_events
IST=dt.timezone(dt.timedelta(hours=5,minutes=30))
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'data')
t0=dt.datetime.now(IST).replace(hour=0,minute=0,second=0,microsecond=0); t1=t0+dt.timedelta(days=30)
def rows(url,tag):
    cal=icalendar.Calendar.from_ical(urllib.request.urlopen(url,timeout=30).read())
    out=[]
    for ev in recurring_ical_events.of(cal).between(t0,t1):
        if str(ev.get('STATUS','')).upper()=='CANCELLED': continue
        s=ev.get('DTSTART').dt; e=ev.get('DTEND').dt if ev.get('DTEND') else s
        allday=not isinstance(s,dt.datetime)
        f=(lambda v:v.isoformat()) if allday else (lambda v:(v if v.tzinfo else v.replace(tzinfo=IST)).astimezone(IST).isoformat())
        out.append(dict(tag=tag,s=str(ev.get('SUMMARY','(busy)')),st=f(s),en=f(e),allday=allday))
    return out
for name,urls,tag in (('personal',P,'p'),('work',W,'w')):
    if not urls: continue
    try:
        r=[x for u in urls for x in rows(u,tag)]
        if name=='work': r+=[x for u in H for x in rows(u,'h')]
        r.sort(key=lambda x:x['st'])
        with open(os.path.join(D,name+'.jsonl'),'w') as fh:
            for x in r: fh.write(json.dumps(x,ensure_ascii=False)+'\n')
        print('ical',name,len(r))
    except Exception as ex: print('ical',name,'FAIL, kept old file:',ex)
