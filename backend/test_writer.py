import sys
sys.path.insert(0, 'backend')
from ai_writer import generate_all_content

stories = [
    {'title': 'New Study on Creatine Benefits', 'summary': 'Research shows creatine improves performance', 'source': 'PubMed'},
    {'title': 'Rest Periods Between Sets Matter', 'summary': 'Study on rest interval effects', 'source': 'NSCA'},
    {'title': 'Common Gym Mistakes Report', 'summary': 'Survey of 10000 gym goers shows biggest mistakes', 'source': 'Fitness Journal'},
    {'title': 'Protein Timing Myth Debunked', 'summary': 'Anabolic window research update', 'source': 'ISSN'},
    {'title': 'Monday Chest Day Culture', 'summary': 'Survey on gym habits and patterns', 'source': 'Gym Culture Report'},
]

results = generate_all_content(stories)
for r in results:
    rank   = r['rank']
    ctype  = r['content_type']
    fmt    = r['post_format']
    hl     = r['headline']
    cta    = r['cta']
    print(f"Post {rank} [{ctype}] -> {fmt}")
    print(f"  Headline: {hl}")
    print(f"  CTA: {cta}")
    print()
