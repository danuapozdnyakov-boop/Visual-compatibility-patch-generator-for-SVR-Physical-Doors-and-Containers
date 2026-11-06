"""Choose a filled cap, not the top annulus of a barrel's metal hoops."""
import struct
from nif_io import node_offsets,children,clean_node,set_children

def filled_center(points,triangles):
 lo=[min(p[j] for p in points) for j in range(3)];hi=[max(p[j] for p in points) for j in range(3)]
 def covered(x,y):
  for tri in triangles:
   a,b,c=(points[i] for i in tri)
   den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
   if abs(den)<1e-7:continue
   u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
   v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
   if u>=-1e-5 and v>=-1e-5 and u+v<=1.00001:return True
  return False
 return sum(covered((lo[0]+hi[0])/2+dx*(hi[0]-lo[0]),(lo[1]+hi[1])/2+dy*(hi[1]-lo[1])) for dx in (-.18,0,.18) for dy in (-.18,0,.18))>=7

def prepare_cap(n):
 meshes=[];parents={}
 for i,(kind,raw) in enumerate(n.blocks):
  if kind in ('NiNode','BSFadeNode','BSOrderedNode'):
   for child in children(raw):parents[child]=i
  if kind!='BSTriShape':continue
  o=node_offsets(raw);e=o['collision']+4;desc,nt,nv,_=struct.unpack_from('<QHHI',raw,e+28);stride=(desc&15)*4
  if stride<12 or not nv:continue
  points=[struct.unpack_from('<3f',raw,e+44+j*stride) for j in range(nv)]
  triangles=[struct.unpack_from('<3H',raw,e+44+nv*stride+j*6) for j in range(nt)]
  meshes.append((i,points,triangles))
 height=max(p[2] for _,ps,_ in meshes for p in ps)-min(p[2] for _,ps,_ in meshes for p in ps)
 top=max(p[2] for _,ps,_ in meshes for p in ps)
 candidates=[]
 for i,points,triangles in meshes:
  lo=min(p[2] for p in points);hi=max(p[2] for p in points)
  if hi-lo<height*.15 and lo>top-height*.15 and filled_center(points,triangles):candidates.append(i)
 if len(candidates)!=1:return False
 shape=candidates[0];parent=parents[shape]
 if parent!=0 and children(n.blocks[parent][1])==[shape]:
  struct.pack_into('<i',n.blocks[parent][1],0,n.string('SVC_BarrelLid'));return True
 # A root-level cap can receive an identity node without changing its transform.
 if parent==0:
  blank=clean_node(n.blocks[0][1],n.string('SVC_BarrelLid'),-1,[shape]);o=node_offsets(blank)
  struct.pack_into('<3f',blank,o['translation'],0,0,0);struct.pack_into('<9f',blank,o['rotation'],1,0,0,0,1,0,0,0,1);struct.pack_into('<f',blank,o['scale'],1)
  node=n.add('NiNode',blank);set_children(n.blocks[0][1],[v for v in children(n.blocks[0][1]) if v!=shape]+[node]);return True
 raise ValueError('Cap found under a nontrivial shared parent; dedicated mapping required')
