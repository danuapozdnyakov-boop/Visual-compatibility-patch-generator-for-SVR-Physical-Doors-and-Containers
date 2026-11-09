"""Generate local visual compatibility overlays; inputs remain untouched."""
from pathlib import Path
import argparse,json,re,subprocess,sys,hashlib,struct
here=Path(__file__).resolve().parent
from nif_io import Nif,node_offsets,children
p=argparse.ArgumentParser();p.add_argument('--donor-meshes',type=Path,required=True);p.add_argument('--doors',type=Path);p.add_argument('--containers',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert not (a.output/'meshes').exists(), 'Use a fresh output directory (meshes already exists)'
a.output.mkdir(parents=True,exist_ok=True);work=a.output/'reports';work.mkdir(exist_ok=True)
rows=[]
for profile in json.loads((here/'profiles.json').read_text()):
  kind=profile['kind'];folder=a.doors if kind=='doors' else a.containers
  if folder is None:continue
  original=profile['original'];physical=profile['physical']
  target=folder/'meshes'/physical.replace('\\','/');donor=a.donor_meshes/original.replace('\\','/');out=a.output/'meshes'/physical.replace('\\','/')
  row={'kind':kind,'original':original,'physical':physical}
  if not target.exists() or not donor.exists():row['status']='no_donor' if not donor.exists() else 'no_physical_input';rows.append(row);continue
  assert target.resolve()!=out.resolve() and donor.resolve()!=out.resolve()
  row['donor_path'] = str(donor)
  native_output = work / 'native-output.nif'
  converted_donor = work / 'converted-donor.nif'
  try:
   stage = 'read_donor'
   donor_data = donor.read_bytes()
   row['original_donor_sha256'] = hashlib.sha256(donor_data).hexdigest()
   header_end = donor_data.index(b'\n') + 1
   version, endian, user, _, stream = struct.unpack_from('<IBIII', donor_data, header_end)
   if (version, endian, user, stream) == (0x14020007, 1, 12, 83):
    stage = 'convert_le_donor'
    conversion = subprocess.run(
     [str(here / 'SVRVisualPatch.exe'), '--convert-le', str(donor), str(converted_donor)],
     capture_output=True, text=True, errors='replace', timeout=60,
     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if conversion.returncode:
     raise ValueError((conversion.stdout + conversion.stderr).strip()
                      or f'LE conversion exited with code {conversion.returncode}')
    donor = converted_donor
    donor_data = donor.read_bytes()
    row['donor_conversion'] = 'skyrim_le_to_se'

   # Known SMIM furniture aliases: exact node rename only, no substring-based guessing.
   stage = 'parse_donor'
   donorNif = Nif(donor_data)
   stage = 'prepare_donor'
   prepared = False
   aliases={'clutter\\upperclass\\upperdresser01.nif':{'Dresser01Drawer':'Dresser01Drawer01'},'clutter\\upperclass\\upperendtable01.nif':{'EndTable01Drawer':'EndTable01Drawer01'},'clutter\\upperclass\\upperwardrobe01.nif':{'Wardrobe01DoorL':'Wardrobe01DoorL01','Wardrobe01DoorR':'Wardrobe01DoorR02'}}
   if original in aliases:
    donorNif.strings=[aliases[original].get(v,v) for v in donorNif.strings];prepared=True
   if original in ('clutter\\barrel01.nif','clutter\\tgbarrel01.nif','clutter\\sovngarde\\sovbarrel01.nif'):
    from split_barrel import split_barrel
    from barrel_cap import prepare_cap
    if not prepare_cap(donorNif):split_barrel(donorNif)
    prepared=True
   if prepared:
    donor=work/('donor-'+hashlib.sha256(physical.encode()).hexdigest()[:16]+'.nif');donor.write_bytes(donorNif.encode())
   pairs=profile['pairs']
   stage = 'read_physical_input'
   targetNif=Nif(target.read_bytes())
   pairs=[(leaf.replace('SVR_GrabOnly_','SVR_Physical_') if leaf not in targetNif.strings and leaf.replace('SVR_GrabOnly_','SVR_Physical_') in targetNif.strings else leaf,shadow) for leaf,shadow in pairs]
   mapping=work/(hashlib.sha256(physical.encode()).hexdigest()[:16]+'.tsv');mapping.write_text(''.join(shadow+'\t'+leaf+'\n' for leaf,shadow in pairs))
   stage = 'native_graft'
   cmd=[str(here/'SVRVisualPatch.exe'),str(target),str(donor),str(native_output),str(mapping)]
   materialOnly=original=='architecture\\skyhaventemple\\skyhavenheaddoor01.nif'
   if materialOnly:cmd.append('--materials')
   c=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=60,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
   row.update(result=c.stdout+c.stderr,returncode=c.returncode)
   if c.returncode:
    row.update(status='unsupported_geometry', stage=stage)
    if not row['result'].strip():row['result'] = f'Native helper exited with code {c.returncode}'
    rows.append(row)
    continue
   stage = 'validate_graft'
   old = targetNif
   new = Nif(native_output.read_bytes())
   for shader,raw in new.blocks:
    if shader=='BSLightingShaderProperty':
     flags=20+4*struct.unpack_from('<I',raw,8)[0];struct.pack_into('<I',raw,flags,struct.unpack_from('<I',raw,flags)[0]|16)
   def reachable_shapes(n):
    seen=set();shapes=set()
    def walk(index):
     if index in seen:return
     seen.add(index);kind,raw=n.blocks[index]
     if kind in ('NiNode','BSFadeNode','BSOrderedNode'):
      for child in children(raw):
       if child>=0:walk(child)
     elif kind in ('BSTriShape','NiTriShape','NiTriStrips','BSSubIndexTriShape','BSDynamicTriShape'):shapes.add(index)
    walk(0);return shapes
   visible=reachable_shapes(new)
   if not materialOnly:
    oldVisible=reachable_shapes(old)
    kept={i for i in oldVisible if old.strings[struct.unpack_from('<i',old.blocks[i][1])[0]].startswith(('SVC_DarkFill_','SVC_BarrelInterior'))}
    assert not ((oldVisible-kept)&visible),(original,'old surfaces still reachable')
    assert len(visible-kept)==len(reachable_shapes(donorNif)),(original,'donor surface count mismatch')
   row['reachable_surfaces']=len(visible);row['old_surfaces_removed']=not materialOnly
   before=[(i,t,bytes(b)) for i,(t,b) in enumerate(old.blocks) if t.startswith('bhk')]
   assert before==[(i,t,bytes(b)) for i,(t,b) in enumerate(new.blocks) if t.startswith('bhk')],(original,'physics was modified')
   assert {v for v in old.strings if v.startswith(('SVR_','SVC_'))}.issubset(set(new.strings)),original
   stage = 'encode_graft'
   encoded = new.encode()
   row['source_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
   row['donor_sha256'] = hashlib.sha256(donor.read_bytes()).hexdigest()
  except (ValueError, AssertionError, IndexError, struct.error, RecursionError, subprocess.TimeoutExpired, FileNotFoundError) as error:
   row.update(status='unsupported_geometry', stage=stage,
              result=f'{type(error).__name__}: {error or "NIF structure validation failed"}')
   rows.append(row)
   continue
  finally:
   native_output.unlink(missing_ok=True)
   converted_donor.unlink(missing_ok=True)

  # Only verified output becomes visible to MO2 and the ZIP packager.
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_bytes(encoded)
  row['status'] = 'materials_only' if materialOnly else 'render_geometry_grafted'
  row['physics_bytes_identical'] = True
  rows.append(row)
(work/'manifest.json').write_text(json.dumps(rows,indent=2))
from collections import Counter
print(json.dumps(dict(Counter(row['status'] for row in rows)),indent=2))

