"""Photo or mesh -> head.bin + head.json for the twin page.
  build.py --photo me.jpg --out DIR     (cuts the person out, sends the cut-out to fal once, about $0.38, needs FAL_KEY)
  build.py --glb model.glb --out DIR    (no network)
Needs numpy, pillow, trimesh, opencv, rembg (photo only). Finds the face on the mesh itself, so regions and the jaw fit any head."""
import argparse,base64,json,os,sys,time,urllib.request
import numpy as np, trimesh, cv2
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__))
ap=argparse.ArgumentParser(); ap.add_argument('--photo'); ap.add_argument('--glb'); ap.add_argument('--consent',action='store_true',help='you confirm this is your own photo, or you have written consent from the person in it');ap.add_argument('--body',action='store_true',help='a full-length photo: keep the whole figure');ap.add_argument('--left-front');ap.add_argument('--right-front');ap.add_argument('--ref',help='the cut-out photo the mesh was built from');ap.add_argument('--check',help='look at a photo and say what to fix; prints JSON');ap.add_argument('--out'); ap.add_argument('--points',type=int,default=270000); a=ap.parse_args()
YUNET=os.path.join(HERE,'yunet.onnx'); YUNET_URL='https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
def yunet():
    if not os.path.exists(YUNET): urllib.request.urlretrieve(YUNET_URL,YUNET)   # a small face finder, fetched once
    return YUNET
if a.check:
    im=cv2.imread(a.check); issues=[]; good=[]
    if im is None: print(json.dumps({'ok':False,'issues':['That file is not an image'],'good':[]})); sys.exit()
    h,w=im.shape[:2]; s=900/max(h,w); sm=cv2.resize(im,(int(w*s),int(h*s))); d=cv2.FaceDetectorYN.create(yunet(),'',(sm.shape[1],sm.shape[0]),.6); fs=d.detect(sm)[1]
    if min(h,w)<700: issues.append('Small photo. Use one at least 1000 pixels wide')
    if fs is None: issues.append('No face found')
    elif len(fs)>1: issues.append('More than one face. Use a photo of you alone')
    else:
        f=fs[0]; x,y,fw,fh=[int(v) for v in f[:4]]; iod=abs(f[6]-f[4])+1e-6; crop=cv2.cvtColor(sm[max(0,y):y+fh,max(0,x):x+fw],cv2.COLOR_BGR2GRAY)
        if fw/sm.shape[1]<.16: issues.append('The face is small. Use a head and shoulders photo')
        if fw/sm.shape[1]>.62: issues.append('Too close. Show the shoulders')
        if abs(f[8]-(f[4]+f[6])/2)/iod>.2: issues.append('Turn to face the camera')
        if abs(np.degrees(np.arctan2(f[7]-f[5],f[6]-f[4])))>9: issues.append('Hold the head level')
        if crop.size and cv2.Laplacian(cv2.resize(crop,(200,200)),cv2.CV_64F).var()<35: issues.append('Looks soft. Use a sharper photo')
        if crop.size and crop.mean()<55: issues.append('Too dark. Use even light on the face')
        if crop.size and crop.mean()>222: issues.append('Too bright. The face is washed out')
        if crop.size and abs(float(crop[:,:crop.shape[1]//2].mean())-float(crop[:,crop.shape[1]//2:].mean()))>60: issues.append('One side of the face is in shadow. Even light gives a better head')
        if not issues: good.append('Good photo. One face, front on, sharp, even light.')
    print(json.dumps({'ok':not issues,'issues':issues,'good':good})); sys.exit()
if not a.out: ap.error('--out is required')
os.makedirs(a.out,exist_ok=True)
def say(s): print(s,flush=True); open(os.path.join(a.out,'status.txt'),'w').write(s)
if a.photo and not a.consent: sys.exit('Add --consent to confirm this is your own photo, or that you have written consent from the person in it.')
if a.photo:
    say('Cutting you out of the photo')
    from rembg import remove,new_session
    sess=new_session('birefnet-portrait')
    def cutout(path,name):
        im=Image.open(path); im=__import__('PIL.ImageOps',fromlist=['x']).exif_transpose(im).convert('RGB'); im.thumbnail((2400,2400)); cut=remove(im,session=sess); arr=np.asarray(cut).astype(float)
        al=arr[...,3:]/255; ys,xs=np.nonzero(al[...,0]>.5)
        if len(ys)<2000: say('ERROR No person found in that photo'); sys.exit(1)
        rgb=np.clip(arr[...,:3]/255,0,1)**.6; flat=Image.fromarray(((rgb*al+.93*(1-al))*255).astype('uint8'))
        x0,x1,y0=xs.min(),xs.max(),ys.min(); w=x1-x0; side=int((max(w,ys.max()-y0) if a.body else w)*1.04); cx=(x0+x1)//2; top=max(0,y0-int(side*.02))
        c=flat.crop((cx-side//2,top,cx+side//2,top+side)); sq=Image.new('RGB',(side,side),(237,237,237)); sq.paste(c,(0,0)) if not a.body else sq.paste(flat.crop((max(0,cx-side//2),top,min(flat.size[0],cx+side//2),min(flat.size[1],top+side))),(max(0,side//2-cx),0)); sq=sq.resize((1536,1536),3); out=os.path.join(a.out,name); sq.save(out,quality=94); return out
    src=cutout(a.photo,'input.jpg'); a.ref=src
    b64=lambda f:'data:image/jpeg;base64,'+base64.b64encode(open(f,'rb').read()).decode()
    body={'input_image_url':b64(src)}
    if a.left_front: body['left_front_image_url']=b64(cutout(a.left_front,'left.jpg'))
    if a.right_front: body['right_front_image_url']=b64(cutout(a.right_front,'right.jpg'))
    key=os.environ.get('FAL_KEY')
    if not key: say('ERROR No FAL_KEY set'); sys.exit(1)
    say('Building the 3D head. About two minutes')
    H={'Authorization':'Key '+key,'Content-Type':'application/json'}
    def call(u,b=None): return json.load(urllib.request.urlopen(urllib.request.Request(u,data=json.dumps(b).encode() if b else None,headers=H),timeout=180))
    s=call('https://queue.fal.run/fal-ai/hunyuan-3d/v3.1/pro/image-to-3d',body)
    open(os.path.join(a.out,'request.txt'),'w').write(s['request_id']); t=time.time()
    while call(s['status_url'])['status']!='COMPLETED':
        if time.time()-t>900: say('ERROR The 3D build timed out'); sys.exit(1)
        time.sleep(6)
    a.glb=os.path.join(a.out,'model.glb'); urllib.request.urlretrieve(call(s['response_url'])['model_glb']['url'],a.glb)
say('Placing the dots')
sc=trimesh.load(a.glb); m=sc.to_geometry() if hasattr(sc,'to_geometry') else sc
rng=np.random.default_rng(7); tri=m.triangles; area=m.area_faces
def sample(n,w):
    f=rng.choice(len(tri),n,p=w/w.sum()); u,v=rng.random((2,n)); fl=u+v>1; u[fl]=1-u[fl]; v[fl]=1-v[fl]; bc=np.stack([1-u-v,u,v],1)
    p=(tri[f]*bc[...,None]).sum(1); n_=(m.vertex_normals[m.faces[f]]*bc[...,None]).sum(1); n_/=np.linalg.norm(n_,axis=1,keepdims=True)+1e-9
    uv=(m.visual.uv[m.faces[f]]*bc[...,None]).sum(1); return p,n_,uv
mat=m.visual.material; img=getattr(mat,'baseColorTexture',None) or mat.image; T=np.asarray(img.convert('L')).astype(float)/255
lum=lambda uv:T[np.clip(((1-uv[:,1])*T.shape[0]).astype(int),0,T.shape[0]-1),np.clip((uv[:,0]*T.shape[1]).astype(int),0,T.shape[1]-1)]
# 1. find the face: draw the mesh from the front, run a face detector on the drawing
p,n,uv=sample(900000,area); l=lum(uv); lo,hi=p.min(0),p.max(0); S=900; k=S*.94/max(hi[0]-lo[0],hi[1]-lo[1]); c0=(lo+hi)/2
X=((p[:,0]-c0[0])*k+S/2).astype(int); Y=(S/2-(p[:,1]-c0[1])*k).astype(int); o=np.argsort(p[:,2]); im=np.full((S,S),.93); zb=np.full((S,S),-9.)
for dx in(0,1):
    for dy in(0,1): im[np.clip(Y[o]+dy,0,S-1),np.clip(X[o]+dx,0,S-1)]=l[o]; zb[np.clip(Y[o]+dy,0,S-1),np.clip(X[o]+dx,0,S-1)]=p[o,2]
def detect(img,thr):
    d=cv2.FaceDetectorYN.create(yunet(),'',(img.shape[1],img.shape[0]),thr); return d.detect(img)[1]
zat=lambda mx,my:float(np.max(zb[max(0,int(S/2-(my-c0[1])*k)-4):int(S/2-(my-c0[1])*k)+5,max(0,int((mx-c0[0])*k+S/2)-4):int((mx-c0[0])*k+S/2)+5]))
faces=None; photo=None
if a.ref:   # the clean photo finds the face; the outline of the person lines it up with the mesh
    g=cv2.imread(a.ref); faces=detect(g,.6); bg=g[4,4].astype(int); mk=(np.abs(g.astype(int)-bg).max(2)>7); mk=cv2.morphologyEx(mk.astype('uint8'),cv2.MORPH_OPEN,np.ones((9,9),'uint8'))
    cols=np.flatnonzero(mk.sum(0)>12); rws=np.flatnonzero(mk.sum(1)>12); px0,px1,pyt=cols[0],cols[-1],rws[0]; kk=(hi[0]-lo[0])/(px1-px0); toM=lambda x,y:np.array([lo[0]+(x-px0)*kk,hi[1]-(y-pyt)*kk]); PM=mk; KK=kk; photo=cv2.GaussianBlur(cv2.cvtColor(g,cv2.COLOR_BGR2GRAY),(0,0),1.1).astype(float)/255
if faces is None:
    g0=cv2.medianBlur((np.clip(im,0,1)*255).astype('uint8'),5)
    for gain in (1.6,1.0,2.4):
        g=cv2.cvtColor(np.clip(g0.astype(float)*gain,0,255).astype('uint8'),cv2.COLOR_GRAY2BGR); faces=detect(g,.5)
        if faces is not None: break
    toM=lambda x,y:np.array([(x-S/2)/k+c0[0],(S/2-y)/k+c0[1]])
if faces is None: say('ERROR No face found. Try a front-facing photo with even light'); sys.exit(1)
f=max(faces,key=lambda r:r[2]*r[3]*r[14])
eR,eL,nose,mR,mL=[toM(f[4+2*i],f[5+2*i]) for i in range(5)]; i0=abs(eL[0]-eR[0])
# the outline lines up scale well and position loosely, so pin the landmarks to the nose tip of the mesh: the point nearest the camera
nb=(np.abs(p[:,0]-nose[0])<i0*.6)&(np.abs(p[:,1]-nose[1])<i0*.9); tip=p[nb][np.argsort(p[nb,2])[-40:]].mean(0)[:2]; sh_=tip-nose; SH=sh_; eR,eL,nose,mR,mL=[v+sh_ for v in (eR,eL,nose,mR,mL)]
mc=(mR+mL)/2; ec=(eR+eL)/2; mouth=np.array([mc[0],mc[1],zat(mc[0],mc[1])]); iod=abs(eL[0]-eR[0]); mw=abs(mL[0]-mR[0])/2
if not .07<iod/(hi[0]-lo[0])<.45: say('ERROR The face did not line up with the 3D head. Try a head-and-shoulders photo'); sys.exit(1)
chin=float(mc[1]-.68*iod); top=float(toM(0,f[1])[1]); 
for (x,y) in [(f[4+2*i],f[5+2*i]) for i in range(5)]: cv2.circle(g,(int(x),int(y)),4,(40,80,230),-1)
cv2.rectangle(g,(int(f[0]),int(f[1])),(int(f[0]+f[2]),int(f[1]+f[3])),(40,80,230),1); cv2.imwrite(os.path.join(a.out,'face-check.jpg'),g)
# shoulders: first row below the chin where the body is much wider than the head
rows=[(y,np.ptp(p[(np.abs(p[:,1]-y)<.006),0])) for y in np.arange(chin-.3*iod,lo[1],-.008)]; headw=np.ptp(p[np.abs(p[:,1]-ec[1])<.01,0]); sh=next((y for y,w in rows if w>headw*1.45),chin-iod*1.6)
# 2. dense on the face, even spacing
ss=lambda a_,b_,x:(lambda t:t*t*(3-2*t))(np.clip((x-a_)/(b_-a_),0,1))
fc=np.array([mc[0],(ec[1]*.55+mc[1]*.45)]); rx,ry=iod*1.35,(top-chin)*.62
cen=tri.mean(1); dF=np.sqrt(((cen[:,0]-fc[0])/rx)**2+((cen[:,1]-fc[1])/ry)**2); front=cen[:,2]>mouth[2]-iod*1.6
w=area*np.where((dF<1.15)&front,22,np.where(cen[:,1]>sh,3.,1.2)); p,n,uv=sample(2400000,w); l=lum(uv)
d=np.sqrt(((p[:,0]-fc[0])/rx)**2+((p[:,1]-fc[1])/ry)**2)+ss(mouth[2]-iod*.9,mouth[2]-iod*2.,p[:,2])*2
rad=(.00135+ss(.8,1.35,d)*.0015+(1-ss(sh-.1,sh+.12,p[:,1]))*.0012)*(1+.25*(rng.random(len(p))-.5)); keep=np.zeros(len(p),bool)
for a0,b0 in((0,.0016),(.0016,.0023),(.0023,.0031),(.0031,.01)):
    mk=(rad>=a0)&(rad<b0); r=float(np.mean(rad[mk])) if mk.any() else 0; gcell={}; r2=r*r
    for i in np.flatnonzero(mk):
        x,y,z=p[i]; kk=(int(x//r),int(y//r),int(z//r)); ok=True
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                for dz in(-1,0,1):
                    j=gcell.get((kk[0]+dx,kk[1]+dy,kk[2]+dz))
                    if j is not None:
                        q=p[j]-p[i]
                        if q[0]*q[0]+q[1]*q[1]+q[2]*q[2]<r2: ok=False;break
                if not ok:break
            if not ok:break
        if ok: gcell[kk]=i; keep[i]=True
if photo is not None:   # the real photo carries eyes, brows and hair that the mesh texture smears; lay it over what faces the camera
    PX=np.clip((px0+(p[:,0]-SH[0]-lo[0])/KK).astype(int),0,photo.shape[1]-1); PY=np.clip((pyt+(hi[1]-(p[:,1]-SH[1]))/KK).astype(int),0,photo.shape[0]-1)
    ph=photo[PY,PX]; inside=PM[PY,PX]>0; wt=ss(.5,.88,n[:,2])*ss(1.5,1.0,d)*float(os.environ.get('TWIN_PHOTO','0.85'))*inside*(p[:,2]>mouth[2]-iod*1.5)
    ph=np.clip((ph-.06)/.80,0,1)**float(os.environ.get('TWIN_GAMMA','1.9'))   # undo the lift used for the 3D build
    l=l*(1-wt)+ph*wt
p,n,l,d=p[keep],n[keep],l[keep],d[keep]
if len(p)>a.points: s_=rng.permutation(len(p))[:a.points]; p,n,l,d=p[s_],n[s_],l[s_],d[s_]
# 3. areas: 0 decisions (top and back of head), 1 taste (eyes), 2 voice (mouth, jaw), 3 work (body), 4 limits (neck, collar)
y=p[:,1]; face=d<1.1; reg=np.zeros(len(p),'uint8'); reg[y<sh]=3; reg[face&(y>nose[1])&(y<top+.0*iod)]=1; reg[face&(y<=nose[1])]=2
reg[(~face)&(y>=sh)&(y<chin+iod*.25)]=4; reg[(y<sh)&(y>sh-iod*.55)&(np.abs(p[:,0]-mc[0])<iod*1.7)]=4
# 4. one rig for every head: mouth sits at a fixed place, eyes a fixed distance apart
sc_=.1240/iod; org=np.array([mouth[0],mouth[1]+.0370/sc_,0])
if a.body: sc_=.86/(hi[1]-lo[1]); org=np.array([mouth[0],(hi[1]+lo[1])/2,(hi[2]+lo[2])/2])
q=(p-org)*sc_; o=rng.permutation(len(q)); q,n,l,reg=q[o],n[o],l[o],reg[o]
rec=np.zeros(len(q),dtype=[('p','<i2',3),('n','i1',3),('l','u1'),('r','u1'),('x','u1')]); rec['p']=np.clip(q/.5*32767,-32767,32767); rec['n']=n*127; rec['l']=np.clip(l,0,1)*255; rec['r']=reg; rec.tofile(os.path.join(a.out,'head.bin'))
# the landmark sits on the lower lip; the line between the lips is the sharpest step in depth just above it
ys=np.arange(-.06,.03,.0025); zs=np.array([(lambda k_:q[k_,2].max() if k_.any() else np.nan)((np.abs(q[:,0])<.03)&(np.abs(q[:,1]-yy)<.00125)&(q[:,2]>0)) for yy in ys])
dz=np.where((ys[:-1]>-.049)&(ys[:-1]<-.027),np.diff(zs),np.nan); li=int(np.nanargmax(dz)) if np.isfinite(dz).any() else None
T_=lambda v:[round(float(x),4) for x in ((np.array(v)-org[:len(v)])*sc_)]
meta={'points':len(q),'mouth':T_(mouth),'mouthW':round(float(mw*sc_),4),'chin':T_([0,chin])[1],'eyes':T_([0,ec[1]])[1],'shoulders':T_([0,sh])[1],'bounds':[T_(p.min(0)),T_(p.max(0))],'areas':np.bincount(reg,minlength=5).tolist(),'body':bool(a.body)}
if li is not None and dz[li]>.002: meta['mouth']=[0.0,round(float(ys[li]+.00125),4),round(float(zs[li]),4)]
json.dump(meta,open(os.path.join(a.out,'head.json'),'w')); print(json.dumps(meta)); say('DONE')
