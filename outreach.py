#!/usr/bin/env python3
"""JKantic approved email queue -> Resend. Dry-run by default."""
import argparse, csv, datetime as dt, json, os, pathlib, re, sys, time
from zoneinfo import ZoneInfo
import requests

ROOT = pathlib.Path(__file__).resolve().parent
QUEUE = ROOT / 'queue.csv'
SENT = ROOT / 'scheduled_log.jsonl'
TZ = ZoneInfo('Africa/Johannesburg')
FROM = os.getenv('RESEND_FROM', 'JKantic <Business@jkantic.com>')
API = 'https://api.resend.com/emails'

def load_rows():
    with QUEUE.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def save_rows(rows):
    with QUEUE.open('w', newline='', encoding='utf-8') as f:
        writer=csv.DictWriter(f, fieldnames=['id','company','to','subject','body','status','scheduled_at','resend_id'])
        writer.writeheader();writer.writerows(rows)

def existing():
    if not SENT.exists(): return set()
    return {json.loads(line)['id'] for line in SENT.read_text().splitlines() if line.strip()}

def check(row):
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', row['to']): raise ValueError('Invalid email address')
    if not row['subject'].strip() or not row['body'].strip(): raise ValueError('Missing subject or body')
    if row['status'] != 'approved': raise ValueError('Not approved')

def next_slots(count, per_day, hour, minute):
    now=dt.datetime.now(TZ)
    d=now.date()
    slots=[]
    while len(slots)<count:
        if d.weekday()<5:
            start=dt.datetime.combine(d,dt.time(hour,minute),TZ)
            # Stagger individual emails 2 minutes apart; don't use slots already in the past.
            for i in range(per_day):
                slot=start+dt.timedelta(minutes=2*i)
                if slot>now+dt.timedelta(minutes=10):
                    slots.append(slot)
                    if len(slots)>=count:break
        d+=dt.timedelta(days=1)
    return slots

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--commit',action='store_true',help='Actually schedule approved emails (otherwise dry-run)')
    p.add_argument('--limit',type=int,default=1,help='Maximum emails to process this run')
    p.add_argument('--per-day',type=int,default=20)
    p.add_argument('--hour',type=int,default=11)
    p.add_argument('--minute',type=int,default=0)
    args=p.parse_args()
    if not 1<=args.limit<=100 or not 1<=args.per_day<=50: p.error('Invalid limit/per-day')
    rows=load_rows(); done=existing()
    pending=[]
    for r in rows:
        if r['status']=='approved' and r['id'] not in done and not r['resend_id']:
            check(r); pending.append(r)
    pending=pending[:args.limit]
    if not pending: print('No approved unscheduled messages.');return
    slots=next_slots(len(pending),args.per_day,args.hour,args.minute)
    for r,slot in zip(pending,slots):
        print(f"{'SCHEDULE' if args.commit else 'PREVIEW'}: {r['id']} -> {r['to']} at {slot.isoformat()}")
        if not args.commit:continue
        key=os.getenv('RESEND_API_KEY')
        if not key:sys.exit('RESEND_API_KEY missing. Nothing sent in this run.')
        # Record intent before API call; if response is ambiguous, stop to avoid duplicates.
        intent={'id':r['id'],'to':r['to'],'at':slot.isoformat(),'state':'attempted'}
        with SENT.open('a',encoding='utf-8') as f:f.write(json.dumps(intent)+'\n')
        try:
            response=requests.post(API,headers={'Authorization':f'Bearer {key}','Content-Type':'application/json','Idempotency-Key':'jkantic-'+r['id']},json={'from':FROM,'to':[r['to']],'subject':r['subject'],'text':r['body'],'scheduled_at':slot.isoformat()},timeout=30)
            response.raise_for_status()
        except Exception as e:
            print(f'STOP: request failed for {r["id"]}: {e}. Check Resend before retrying.');sys.exit(2)
        rid=response.json().get('id','')
        r['status']='scheduled';r['scheduled_at']=slot.isoformat();r['resend_id']=rid
        save_rows(rows)
        with SENT.open('a',encoding='utf-8') as f:f.write(json.dumps({'id':r['id'],'to':r['to'],'at':slot.isoformat(),'state':'scheduled','resend_id':rid})+'\n')
        print(f'Confirmed Resend ID: {rid}')
        time.sleep(.6)

if __name__=='__main__':main()
