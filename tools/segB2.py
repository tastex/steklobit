import cv2, numpy as np, json, sys
im=cv2.imread('e.png'); H,W=im.shape[:2]; K=500/W
sm=cv2.bilateralFilter(im,9,30,9)
lab=cv2.cvtColor(sm,cv2.COLOR_BGR2LAB)
lo,hi=int(sys.argv[1]),int(sys.argv[2])
ed=cv2.Canny(cv2.GaussianBlur(lab[...,0],(3,3),0),lo,hi)
ed2=cv2.Canny(cv2.GaussianBlur(lab[...,1],(3,3),0),10,30)|cv2.Canny(cv2.GaussianBlur(lab[...,2],(3,3),0),10,30)
hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV); S,V=hsv[...,1].astype(int),hsv[...,2].astype(int)
grout=((S<70)&(V>150)).astype(np.uint8)*255
bar=cv2.dilate(ed|ed2,np.ones((3,3),np.uint8),iterations=1)|grout
free=(bar==0).astype(np.uint8)
n,cc,st,_=cv2.connectedComponentsWithStats(free,connectivity=4)
polys=[]
for i in range(1,n):
    if st[i,4]<120: continue
    m=(cc==i).astype(np.uint8)
    if cv2.erode(m,np.ones((7,7),np.uint8)).sum()<20: continue
    px=im[m>0]; hv=hsv[m>0]
    if np.median(hv[:,1])<80 and np.median(hv[:,2])>120: continue   # white background glass
    m=cv2.dilate(m,np.ones((5,5),np.uint8))
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    c=max(cs,key=cv2.contourArea)
    hull=cv2.convexHull(c); sol=cv2.contourArea(c)/max(cv2.contourArea(hull),1)
    ap=cv2.approxPolyDP(hull if sol>0.88 else c,3.5,True).reshape(-1,2)
    if len(ap)<3: continue
    col=np.median(px,axis=0).astype(int)[::-1]
    polys.append({'p':(ap*K).round(1).tolist(),'c':'#%02x%02x%02x'%tuple(col)})
print(len(polys))
json.dump(polys,open('figB.json','w'))
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="1000" height="1000"><rect width="500" height="500" fill="#ddd"/>']
for i,p in enumerate(polys):
    cx=np.mean([q[0] for q in p['p']]);cy=np.mean([q[1] for q in p['p']])
    svg.append('<polygon points="%s" fill="%s"/><text x="%.0f" y="%.0f" font-size="7" fill="#fff" text-anchor="middle">%d</text>'%(' '.join(f'{x},{y}' for x,y in p['p']),p['c'],cx,cy+2,i))
open('figB.svg','w').write(''.join(svg)+'</svg>')
cv2.imwrite('barB.png',bar)
