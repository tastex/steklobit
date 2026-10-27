import cv2, numpy as np, json, sys
K=int(sys.argv[1]) if len(sys.argv)>1 else 18
img=cv2.imread('t.jpg'); x0,y0,x1,y1=62,85,585,608
crop=img[y0:y1,x0:x1].copy(); H,W=crop.shape[:2]
sm=cv2.pyrMeanShiftFiltering(crop,6,22)
lab=cv2.cvtColor(sm,cv2.COLOR_BGR2LAB).reshape(-1,3).astype(np.float32)
crit=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,30,0.5)
_,lbl,cent=cv2.kmeans(lab,K,None,crit,4,cv2.KMEANS_PP_CENTERS); lbl=lbl.reshape(H,W)
lbl=cv2.medianBlur(lbl.astype(np.uint8),5)
# grout cluster = the one closest to the measured grout grey
gl=cv2.cvtColor(np.uint8([[[105,99,97]]]),cv2.COLOR_BGR2LAB)[0,0].astype(float)
d=[np.linalg.norm(c-gl) for c in cent]; g=int(np.argmin(d)); print('grout cluster',g,d[g])
polys=[]
for k in range(K):
    if k==g: continue
    m=(lbl==k).astype(np.uint8)
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
    # split shards of the same colour that touch through a thin neck
    core=cv2.erode(m,np.ones((3,3),np.uint8))
    n,cc,st,_=cv2.connectedComponentsWithStats(core)
    for i in range(1,n):
        if st[i,4]<12: continue
        mm=cv2.dilate((cc==i).astype(np.uint8),np.ones((5,5),np.uint8))&m
        cs,_=cv2.findContours(mm,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        c=max(cs,key=cv2.contourArea)
        hull=cv2.convexHull(c)
        sol=cv2.contourArea(c)/max(cv2.contourArea(hull),1)
        ap=cv2.approxPolyDP(hull if sol>0.86 else c,2.6,True).reshape(-1,2)
        if len(ap)<3: continue
        px=crop[mm>0].reshape(-1,1,3)
        hv=cv2.cvtColor(px,cv2.COLOR_BGR2HSV).reshape(-1,3).astype(float)
        h_,s_,v_=np.median(hv,axis=0); s_=min(255,s_*1.2); v_=min(255,v_*1.08+6)
        col=cv2.cvtColor(np.uint8([[[h_,s_,v_]]]),cv2.COLOR_HSV2BGR)[0,0].astype(int)[::-1]
        polys.append({'p':ap.tolist(),'c':'#%02x%02x%02x'%tuple(col),'a':int(mm.sum())})
polys.sort(key=lambda p:-p['a'])
print(len(polys))
json.dump({'w':W,'h':H,'polys':polys},open('tiger.json','w'))
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="#62646a"/>']
for p in polys: svg.append('<polygon points="%s" fill="%s"/>'%(' '.join(f'{x},{y}' for x,y in p['p']),p['c']))
svg.append('</svg>'); open('tiger.svg','w').write(''.join(svg))
