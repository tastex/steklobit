"""Finds the gaps the turning head opens at the dragon's neck and writes dragon_patches.json for scene_gen.py.
Needs playwright (node) and OpenCV: renders the figure on magenta for every frame of each pose,
closes the silhouette and keeps the open spots around the neck."""
import json, os, subprocess, sys, tempfile
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEQ_LEN, DUR = 18, 2.4
left = [i < 8 or i > 14 for i in range(SEQ_LEN)]
work = tempfile.mkdtemp()
subprocess.run([sys.executable, os.path.join(HERE, "scene_gen.py")], cwd=work, check=True,
               env=dict(os.environ, DRAGON_MASK="1"), stdout=subprocess.DEVNULL)
js = os.path.join(work, "shot.js")
open(js, "w").write("""const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();
const p=await b.newPage({viewport:{width:1620,height:1080},deviceScaleFactor:2});
await p.goto('file://'+process.argv[2]+'/scene.svg');await p.waitForTimeout(300);
for(let i=0;i<%d;i++){await p.evaluate(t=>{const d=document.documentElement;d.pauseAnimations();d.setCurrentTime(t)},(i+.5)*%f/%d);
await p.screenshot({path:process.argv[2]+'/f'+i+'.png',clip:{x:785,y:280,width:250,height:250}});}await b.close();})();""" % (SEQ_LEN, DUR, SEQ_LEN))
subprocess.run(["node", js, work], check=True)
data = json.load(open(os.path.join(HERE, "dragon_shards.json")))
out = {"colors": sorted({p["c"] for p in data["polys"] if p["part"] == "body"})}
k = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
for pose, want in (("left", True), ("right", False)):
    acc = np.zeros((500, 500), np.uint8)
    for i in range(SEQ_LEN):
        if left[i] != want:
            continue
        im = cv2.imread(os.path.join(work, f"f{i}.png")).astype(int)
        bg = (im[..., 2] > 200) & (im[..., 0] > 200) & (im[..., 1] < 80)
        fig = (~bg).astype(np.uint8)
        holes = cv2.morphologyEx(fig, cv2.MORPH_CLOSE, k(16)) & (1 - fig)
        holes = cv2.morphologyEx(holes, cv2.MORPH_OPEN, k(3))   # thin seams are grout, not holes
        acc |= holes
    zone = np.zeros_like(acc); zone[90:270, 90:340] = 1             # only around the neck, where the head turns
    acc = cv2.dilate(acc & zone, k(3))
    polys = []
    for c in cv2.findContours(acc, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        if cv2.contourArea(c) < 40:
            continue
        ap = cv2.approxPolyDP(c, 2.5, True).reshape(-1, 2)
        if len(ap) >= 3:
            polys.append(ap.astype(float).tolist())
    out[pose] = polys
    print(pose, len(polys), [int(cv2.contourArea(np.int32(p))) for p in polys])
json.dump(out, open(os.path.join(HERE, "dragon_patches.json"), "w"), separators=(",", ":"))
