#!/usr/bin/env python3
import re
p='analysis_snapshot.html'
with open(p, 'rb') as f:
    s=f.read().decode('utf-8', errors='ignore')
# DOCTYPE
if re.search(r'<!doctype\s+html', s, re.I):
    print('DOCTYPE: OK')
else:
    print('DOCTYPE: MISSING')
# find inputs/selects/textareas
inputs=[]
for m in re.finditer(r'<(input|select|textarea)\b([^>]*)>', s, re.I):
    tag=m.group(1).lower(); attrs=m.group(2)
    idm=re.search(r'id\s*=\s*"([^"]+)"', attrs, re.I)
    namem=re.search(r'name\s*=\s*"([^"]+)"', attrs, re.I)
    has_id=bool(idm)
    has_name=bool(namem)
    lineno=s.count('\n',0,m.start())+1
    snippet=s[max(0,m.start()-80):m.end()+80].replace('\n',' ')
    inputs.append({'tag':tag,'id': idm.group(1) if idm else None, 'name': namem.group(1) if namem else None,'lineno':lineno,'snippet':snippet})
# report inputs lacking id and name
no_ident=[x for x in inputs if not x['id'] and not x['name']]
print('\nInputs/selects/textareas missing id AND name: %d' % len(no_ident))
for x in no_ident[:200]:
    print('  line %d: <%s> snippet: %s' % (x['lineno'], x['tag'], x['snippet']))
# find labels
labels=[]
for m in re.finditer(r'<label\b([^>]*)>(.*?)</label>', s, re.I|re.S):
    attrs=m.group(1); inner=m.group(2)
    for_m=re.search(r'for\s*=\s*"([^"]+)"', attrs, re.I)
    lineno=s.count('\n',0,m.start())+1
    contains_input=bool(re.search(r'<(input|select|textarea)\b', inner, re.I))
    labels.append({'for': for_m.group(1) if for_m else None, 'contains_input':contains_input, 'lineno':lineno, 'inner_snippet': inner.strip()[:120]})
print('\nLabels total: %d' % len(labels))
# labels with for that don't match any input id
ids=set([x['id'] for x in inputs if x['id']])
bad_for=[L for L in labels if L['for'] and L['for'] not in ids]
print('Labels with for attr that do NOT match any input id: %d' % len(bad_for))
for L in bad_for[:200]:
    print('  line %d: for="%s", inner="%s"' % (L['lineno'], L['for'], L['inner_snippet'].replace('\n',' ')))
# labels without for and not containing an input
unassoc=[L for L in labels if not L['for'] and not L['contains_input']]
print('\nLabels without for and not wrapping an input: %d' % len(unassoc))
for L in unassoc[:200]:
    print('  line %d: inner="%s"' % (L['lineno'], L['inner_snippet'].replace('\n',' ')))
# summarize counts by tag
from collections import Counter
cnt=Counter([x['tag'] for x in inputs])
print('\nTag counts:')
for k,v in cnt.items(): print(' ',k,v)
