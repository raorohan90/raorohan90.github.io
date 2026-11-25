#!/usr/bin/env python3
"""Open-Meteo forecast + air quality for Bengaluru -> data/weather.json, data/air.json. Fails soft (keeps the old file)."""
import json, os, time, urllib.request
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'data')
SRC={'weather.json':'https://api.open-meteo.com/v1/forecast?latitude=12.9716&longitude=77.5946&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset,uv_index_max&timezone=Asia%2FKolkata&forecast_days=6',
     'air.json':'https://air-quality-api.open-meteo.com/v1/air-quality?latitude=12.9716&longitude=77.5946&current=us_aqi,pm2_5,pm10&timezone=Asia%2FKolkata'}
for f,u in SRC.items():
    for attempt in range(3):
        try:
            x=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'raorohan90-dashboard'}),timeout=20))
            x['_fetched']=int(time.time()); json.dump(x,open(os.path.join(D,f),'w')); print(f,'ok'); break
        except Exception as ex:
            print(f,'FAIL',ex); time.sleep(5)
