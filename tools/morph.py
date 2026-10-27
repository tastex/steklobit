"""Matches the glass pieces of the two dragon photos (dragon_shards.json: looking right, figB.json from segB2.py: looking left)
and writes dragon_morph.json for scene_gen.py. Run next to those files."""
import json, numpy as np, cv2, colorsys
A=json.load(open('dragon_shards.json'))
B=json.load(open('figB.json'))
N=10
def hx(c): return np.array([int(c[i:i+2],16) for i in (1,3,5)],float)
def sat(c):
    r,g,b=hx(c)/255; return colorsys.rgb_to_hsv(r,g,b)
def red(c): r,g,b=hx(c); return r>g+30
def cen(p): p=np.array(p,float); return p.mean(0)
def area(p):
    p=np.array(p,float); x,y=p[:,0],p[:,1]; return abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))/2
# ---- clean B: drop frame bits and unsaturated pieces
Bf=[]
for p in B:
    q=np.array(p['p']); h,s,v=sat(p['c'])
    if q.min()<6 or q.max()>494: continue
    if s<0.25: continue
    r_,g_,b_=hx(p['c'])
    if not (g_>r_ or r_>g_+30) or (r_>g_ and g_>b_+20 and r_<g_+60): continue   # only green and red glass
    if area(p['p'])<25: continue
    Bf.append(p)
def partB(p):
    x,y=cen(p['p'])
    if y<180: return 'head'
    if x>300 and 200<y<315: return 'wing'
    if y>380 and x<290 and not red(p['c']) and area(p['p'])<2500 and (x<200 or y>420): return 'legs'
    if x>240 and y>330: return 'tail'
    return 'body'
for p in Bf: p['part']=partB(p)
figA=[p for p in A['polys'] if p['part']!='bg' and cen(p['p'])[0]>20]
bgA=[p for p in A['polys'] if p['part']=='bg']
# B colours: keep hue, match A's brightness
vA=np.median([sat(p['c'])[2] for p in figA if not red(p['c'])]); vB=np.median([sat(p['c'])[2] for p in Bf if not red(p['c'])])
def fixc(c):
    h,s,v=sat(c); r,g,b=colorsys.hsv_to_rgb(h,s,min(1,v*vA/vB)); return '#%02x%02x%02x'%(int(r*255),int(g*255),int(b*255))
def resample(p):
    p=np.array(p,float)
    if area_signed(p)<0: p=p[::-1]
    seg=np.r_[np.linalg.norm(np.diff(np.r_[p,p[:1]],axis=0),axis=1)]
    t=np.r_[0,np.cumsum(seg)]; L=t[-1]; out=[]
    for s in np.arange(N)*L/N:
        i=np.searchsorted(t,s,side='right')-1; i=min(i,len(p)-1); u=(s-t[i])/max(seg[i],1e-9)
        out.append(p[i]+(p[(i+1)%len(p)]-p[i])*u)
    return np.array(out)
def area_signed(p):
    x,y=p[:,0],p[:,1]; return (np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))/2
def align(a,b):
    ca,cb=a.mean(0),b.mean(0); best=None
    for k in range(N):
        bb=np.roll(b,k,axis=0); d=((a-ca-(bb-cb))**2).sum()
        if best is None or d<best[0]: best=(d,bb)
    return best[1]
def shrink(p,k): c=p.mean(0); return c+(p-c)*k
shards=[]
for part in ['head','body','wing','tail','legs']:
    pa=[p for p in figA if p['part']==part]; pb=[p for p in Bf if p['part']==part]
    print(part,len(pa),len(pb))
    def cost(a,b):
        return np.linalg.norm(cen(a['p'])-cen(b['p']))+300*(red(a['c'])!=red(b['c']))+0.6*abs(np.sqrt(area(a['p']))-np.sqrt(area(b['p'])))
    C=np.array([[cost(a,b) for b in pb] for a in pa])
    pairs=[]; ua=set(); ub=set()
    for i,j in sorted(np.ndindex(C.shape),key=lambda ij:C[ij]):
        if i in ua or j in ub: continue
        pairs.append((i,j)); ua.add(i); ub.add(j)
    for i,j in pairs:
        ra=resample(pa[i]['p']); rb=align(ra,resample(pb[j]['p']))
        shards.append({'c':pa[i]['c'],'a':ra,'b':rb,'z':1,'part':part})
    for i in set(range(len(pa)))-ua:   # extra A pieces tuck under their nearest partner
        j=int(np.argmin(C[i])); ra=resample(pa[i]['p']); rb=align(ra,shrink(resample(pb[j]['p']),.5))
        shards.append({'c':pa[i]['c'],'a':ra,'b':rb,'z':0,'part':part})
    for j in set(range(len(pb)))-ub:   # extra B pieces come out from under the nearest A piece
        i=int(np.argmin(C[:,j])); rb=resample(pb[j]['p']); ra=align(rb,shrink(resample(pa[i]['p']),.5))
        shards.append({'c':pa[i]['c'] if red(pa[i]['c'])==red(pb[j]['c']) else fixc(pb[j]['c']),'a':ra,'b':rb,'z':0,'part':part})
shards.sort(key=lambda s:s['z'])
# ---- fill the window behind both figures with light filler glass, so neither pose leaves a hole
S=2; W=500*S
cov=np.zeros((W,W),np.uint8)
for p in bgA: cv2.fillPoly(cov,[(np.array(p['p'])*S).astype(np.int32)],1)
holes=(1-cov).astype(np.uint8); holes=cv2.morphologyEx(holes,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
rng=np.random.default_rng(3); light=[p['c'] for p in bgA]
ys,xs=np.nonzero(holes); idx=rng.choice(len(xs),size=min(len(xs),140),replace=False)
seeds=np.c_[xs[idx],ys[idx]]
# keep seeds spread out
keep=[]
for s in seeds:
    if all(np.hypot(*(s-k))>48*S/2 for k in keep): keep.append(s)
gx,gy=np.meshgrid(np.arange(W),np.arange(W))
lab=np.full((W,W),-1); best=np.full((W,W),1e18)
for k,(sx,sy) in enumerate(keep):
    d=(gx-sx)**2+(gy-sy)**2; m=d<best; best[m]=d[m]; lab[m]=k
fill=[]
for k in range(len(keep)):
    m=((lab==k)&(holes>0)).astype(np.uint8)
    m=cv2.erode(m,np.ones((5,5),np.uint8))
    if m.sum()<80: continue
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for c in cs:
        if cv2.contourArea(c)<60: continue
        ap=cv2.approxPolyDP(c,3,True).reshape(-1,2)/S
        if len(ap)>=3: fill.append({'p':ap.round(1).tolist(),'c':light[rng.integers(len(light))]})
print('shards',len(shards),'filler',len(fill))
out={'grout':A['grout'],'bg':[{'p':p['p'],'c':p['c']} for p in bgA]+fill,
     'shards':[{'part':s['part'],'c':s['c'],'a':np.round(s['a'],1).tolist(),'b':np.round(s['b'],1).tolist()} for s in shards]}
json.dump(out,open('dragon_morph.json','w'),separators=(',',':'))
