"""GUI worker: validates inputs, runs the proven core, packages only installable output."""
from pathlib import Path
import argparse,runpy,sys,json,zipfile,hashlib,traceback
from collections import Counter
p=argparse.ArgumentParser();p.add_argument('--donor',required=True);p.add_argument('--doors');p.add_argument('--containers');p.add_argument('--output',required=True);a=p.parse_args()
output=Path(a.output)
try:
 donor=Path(a.donor).resolve()
 if donor.name.lower()!='meshes' and (donor/'meshes').is_dir():donor=donor/'meshes'
 if not donor.is_dir():raise ValueError('Graphics meshes folder does not exist.')
 profiles=json.loads((Path(__file__).parent/'profiles.json').read_text())
 if not any((donor/item['original'].replace('\\','/')).is_file() for item in profiles):raise ValueError('No supported original-path meshes found. Select your graphics/PGPatcher output meshes folder, not the SVR patch folder.')
 chosen={}
 for name in ('doors','containers'):
  value=getattr(a,name)
  if not value:continue
  folder=Path(value).resolve();dll='SVRPhysicalDoors.dll' if name=='doors' else 'SVRPhysicalContainers.dll'
  if not (folder/'SKSE/Plugins'/dll).is_file():raise ValueError('Selected '+name+' folder does not contain SKSE/Plugins/'+dll)
  if not (folder/'meshes').is_dir():raise ValueError('Selected '+name+' folder has no meshes directory.')
  chosen[name]=folder
 if not chosen:raise ValueError('Choose at least one SVR base mod folder.')
 destination=output.resolve()
 for input_path in [donor,*chosen.values()]:
  if destination==input_path or destination.is_relative_to(input_path) or input_path.is_relative_to(destination):raise ValueError('Output must be separate from all input folders.')
 if output.exists():raise ValueError('Output folder already exists. Choose a new destination.')
 args=['generate.py','--donor-meshes',str(donor),'--output',str(output)]
 for name,folder in chosen.items():args += ['--'+name,str(folder)]
 sys.argv=args;runpy.run_path(str(Path(__file__).parent/'generate.py'),run_name='__main__')
 rows=json.loads((output/'reports/manifest.json').read_text());counts=Counter(row['status'] for row in rows)
 patched=counts['render_geometry_grafted']+counts['materials_only']
 if not patched:raise ValueError('No models were patched. Check the base mod folders and graphics meshes. See reports/manifest.json.')
 archive=output.with_suffix('.zip')
 if archive.exists():raise ValueError('ZIP destination already exists; it was not overwritten.')
 (output/'README.txt').write_text('SVR Visual Compatibility Patch\n\nInstall this ZIP in MO2 after both the SVR base mod(s) and graphics/PGPatcher output. It must win mesh conflicts. Keep the same graphics mods and textures installed. No ESP is included.\nRegenerate after changing base meshes or replacers. See reports/manifest.json for skipped/unsupported models.\n')
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
  for file in (output/'meshes').rglob('*.nif'):z.write(file,file.relative_to(output))
  for rel in ('README.txt','reports/manifest.json'):z.write(output/rel,rel)
 with zipfile.ZipFile(archive) as z:
  if z.testzip() is not None:raise ValueError('ZIP integrity validation failed.')
 summary={'ok':True,'patched':patched,'unsupported':counts['unsupported_geometry'],'missing_donor':counts['no_donor'],'not_installed':counts['no_physical_input'],'archive':str(archive),'report':str(output/'reports/manifest.json'),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
 (output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
except Exception as error:
 print(str(error),file=sys.stderr);traceback.print_exc();sys.exit(1)
