#!/usr/bin/env python3
"""Search all 69 references; scores assist the agent rather than decide aesthetics."""
import argparse
import json
from pathlib import Path
from collage_core import read_json

def search(catalog,mood):
    terms=[s.strip() for s in mood.replace('，',',').split(',') if s.strip()]
    rows=[]
    for item in catalog['items']:
        hay=' '.join(item['moods'])+' '+item.get('search_summary','')
        score=sum(term in hay for term in terms)
        rows.append({'id':item['id'],'reference_number':item['extraction']['reference_number'],
          'image':item['image'],'score':score,'moods':item['moods'],
          'summary':item.get('search_summary',''),'claimed_author':item['source_verification'].get('claimed_author'),
          'ready_for_composition':item.get('ready_for_composition',True),
          'review_flags':item['extraction']['review_flags'],'transcript_status':item['transcript_status']})
    return sorted(rows,key=lambda x:(-x['score'],x['reference_number']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mood',default='')
    p.add_argument('--limit',type=int,default=69)
    a=p.parse_args()
    c=read_json(Path(__file__).resolve().parents[1]/'assets/catalog.json')
    rows=search(c,a.mood)
    print(json.dumps({'searched':len(rows),'note':'Agent 须按画面情绪和文学含义判断；分数不证明适合或出处已核实。',
       'results':rows[:max(0,a.limit)]},ensure_ascii=False,indent=2))
