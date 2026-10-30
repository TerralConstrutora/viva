"""Atualiza o site estático do Residencial Vivá a partir do banco do sistema no Claude.

Uso (dentro de um clone deste repositório):
  python3 _ferramentas/atualizar.py --db PASTA_DB --html INDEX_DO_ARTIFACT [--assets MAPA.json]

PASTA_DB: saída do ArtifactData (obra/viva.json e rdos/*.json).
INDEX_DO_ARTIFACT: index.html do sistema no Claude (lido com Artifact read).
MAPA.json: {asset_id: caminho_local_da_foto} das fotos novas enviadas como assets.
Fotos já existentes em fotos/ e mini/ não são refeitas.
"""
import json,glob,os,argparse
from PIL import Image, ImageOps
ap=argparse.ArgumentParser();ap.add_argument('--db',required=True);ap.add_argument('--html',required=True);ap.add_argument('--assets',default=None)
A=ap.parse_args(); OUT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
amap=json.load(open(A.assets)) if A.assets else {}
for d in ('dados','fotos','mini'): os.makedirs(os.path.join(OUT,d),exist_ok=True)
obra=json.load(open(os.path.join(A.db,'obra','viva.json')))
rdos=[]
for f in sorted(glob.glob(os.path.join(A.db,'rdos','*.json'))):
  d=json.load(open(f)); d['id']=os.path.basename(f)[:-5]; rdos.append(d)
falt=[]
def img_out(src,name):
  fo,mo=os.path.join(OUT,'fotos',name),os.path.join(OUT,'mini',name)
  if not os.path.exists(fo):
    im=ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    if max(im.size)>1600: im.thumbnail((1600,1600),Image.LANCZOS)
    im.save(fo,quality=80,optimize=True,progressive=True)
  if not os.path.exists(mo):
    im=Image.open(fo); im.thumbnail((420,420),Image.LANCZOS); im.save(mo,quality=72,optimize=True)
def conv(f):
  if f.get('asset'):
    src=amap.get(f['asset'])
    if not src: falt.append(f['asset']); return f
    name=os.path.basename(src); img_out(src,name); f=dict(f); f.pop('asset'); f['arquivo']=name
  elif f.get('arquivo') and not os.path.exists(os.path.join(OUT,'fotos',f['arquivo'])): falt.append(f['arquivo'])
  return f
for r in rdos: r['fotos']=[conv(f) for f in r.get('fotos',[])]
for e in obra.get('avanco',{}).get('etapas',[]): e['ev']=[conv(f) for f in e.get('ev',[])]
json.dump(rdos,open(os.path.join(OUT,'dados','rdos.json'),'w'),ensure_ascii=False,separators=(',',':'))
json.dump(obra,open(os.path.join(OUT,'dados','obra.json'),'w'),ensure_ascii=False,separators=(',',':'))
s=open(A.html).read()
def R(a,b):
  global s
  if a in s: s=s.replace(a,b,1)
  else: print('aviso: trecho não encontrado:',a[:50])
R("async function fotoSrc(f,full){if(f.asset)return '/_blob/'+f.asset;if(!f.arquivo)return '';const m=await pacote(full?'fotos':'mini',f.rid);return m[f.arquivo]||'';}",
  "async function fotoSrc(f,full){if(!f.arquivo)return '';return (full?'fotos/':'mini/')+encodeURIComponent(f.arquivo);}")
R("function imgTag(f,extra=''){if(f.asset)return `<img src=\"/_blob/${esc(f.asset)}\" ${extra}>`;return `<img data-arq=\"${esc(f.arquivo||'')}\" data-rid=\"${esc(f.rid||'')}\" ${extra}>`;}",
  "function imgTag(f,extra=''){return `<img src=\"mini/${esc(encodeURIComponent(f.arquivo||''))}\" loading=\"lazy\" ${extra}>`;}")
i=s.index('/* ---------- dados ---------- */'); j=s.index('</script>',i)
s=s[:i]+'''/* ---------- dados (versão do site: somente consulta) ---------- */
(async()=>{
  lerHash();
  try{
    const v='?v='+Date.now().toString(36).slice(0,-3);
    const [o,r]=await Promise.all([fetch('dados/obra.json'+v).then(x=>x.json()),fetch('dados/rdos.json'+v).then(x=>x.json())]);
    S.obra=o;S.rdos=r;S.canEdit=false;S.ok=true;render();
  }catch(e){$('#app').innerHTML=`<div class="vazio panel"><b>Não foi possível carregar o diário</b>Verifique a conexão e recarregue a página.</div>`;}
})();
'''+s[j:]
if not s.lstrip().startswith('<!doctype'):
  s='''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#152737">
<link rel="icon" href="icone.png">
'''+s.replace('<header class="top">','</head><body>\n<header class="top">',1)+'\n</body></html>'
open(os.path.join(OUT,'index.html'),'w').write(s)
print('diários',len(rdos),'| fotos faltando:',falt or 'nenhuma')
