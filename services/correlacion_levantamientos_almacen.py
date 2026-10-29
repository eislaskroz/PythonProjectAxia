"""Correlación no invasiva entre los catálogos históricos de LEV y Almacén.

No altera categorías, tipos, especificaciones, unidades ni cantidades del técnico.
Solo añade la identidad AXIA cuando hay coincidencia suficientemente inequívoca.
Nunca realiza escrituras ni movimientos de inventario.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache
import re
import unicodedata

from services.levantamiento_catalogo_axia import referencia_axia

_STOP = frozenset('DE DEL LA EL LOS LAS PARA POR CON SIN TIPO MCA MARCA COLOR UN UNA UNO EN Y O A AL CONDUIT'.split())
_EQ = {'ABRAZADERO':'ABRAZADERA','ABRAZERA':'ABRAZADERA','ABRAZDERA':'ABRAZADERA',
       'TUVO':'TUBO','CANAL':'CANALETA','METROS':'METRO','MTS':'METRO',
       'GRUESA':'GRUESA','GRUESO':'GRUESA','EMT':'DELGADA', 'PATCHCORD':'PATCH CORD',
       'PLUG':'PLUG','REDES':'RED','UTP':'UTP'}


def normalizar(s: object) -> str:
    valor = unicodedata.normalize('NFKD', str(s or '').upper())
    valor = ''.join(c for c in valor if not unicodedata.combining(c))
    valor = valor.replace('PATCHCORD','PATCH CORD')
    valor = re.sub(r'(?<=\d)\s+(?=\d+/\d+)', ' ', valor)
    return ' '.join(re.findall(r'\d+\s+\d+/\d+|\d+/\d+|[A-Z0-9]+', valor))


def familia_producto(nombre: str) -> str:
    n=normalizar(nombre)
    # La clasificación interna del XLSX no siempre es exacta: el texto manda.
    if re.search(r'\b(ABRAZADERA|ABRAZDERA|ABRAZERA|ABRAZADERO)\b', n): return 'ABRAZADERA'
    if re.search(r'\b(COPLE|COPLES)\b', n) and not n.startswith('TUBO '): return 'COPLE'
    if re.search(r'\b(CONECTOR|CONECTORES)\b', n):
        if 'PLUG RJ45' in n: return 'PLUG RJ45'
        return 'CONECTORES'
    if re.search(r'\b(CODO|CODOS)\b',n): return 'CODOS'
    if re.search(r'\b(CANALETA|CANALETAS)\b',n) and not re.search(r'\b(DERIVACION|TAPA|ACCESORIO)\b',n): return 'CANALETA'
    if re.search(r'\b(FACEPLATE|PLACA DE RED)\b',n): return 'FACEPLATE'
    if re.search(r'\b(PATCH CORD|PATCHCORD)\b',n): return 'PATCH CORD'
    if re.search(r'\b(PATCH PANEL)\b',n): return 'PATCH PANEL'
    if re.search(r'\b(JACK RJ45)\b',n): return 'JACK RJ45'
    if re.search(r'\b(PLUG RJ45)\b',n): return 'PLUG RJ45'
    if re.search(r'\b(REGISTRO|REGISTROS)\b',n): return 'REGISTRO'
    if re.search(r'\b(CAJA|CAJAS)\b',n): return 'CAJAS'
    if re.search(r'\b(TAPA|TAPAS)\b',n): return 'TAPAS'
    if re.search(r'\bTUBO\b', n): return 'TUBO'
    if re.search(r'\bCABLE\b', n): return 'CABLE'
    return ''


def _medidas(s: str) -> frozenset[str]:
    n=normalizar(s)
    medidas=set()
    # Convertir medidas comerciales de conduit de pulgadas a mm nominales.
    fracciones={'1/4':'6','3/8':'10','1/2':'13','3/4':'19','1':'25',
                 '1 1/4':'32','1 1/2':'38','2':'51','2 1/2':'63','3':'76','4':'101'}
    for x in re.findall(r'(?<!\d)(?:\d+\s+)?\d+/\d+(?!\d)',n):
        medidas.add(f'P{x.replace(" ", "")}' if x not in fracciones else f'M{fracciones[x]}')
    for mm in re.findall(r'(?<!\d)(\d+(?:[.,]\d+)?)\s*MM\b',n):
        medidas.add('M'+mm.replace(',','.'))
    # Para pulgadas enteras solo cuando el valor se escribió explícitamente
    # como dimensión, nunca números de modelo/cantidad.
    for inches in re.findall(r'(?<![\d/])(\d+)\s*(?:PULGADAS?|PULG|\")',str(s or '').upper()):
        if inches in fracciones: medidas.add('M'+fracciones[inches])
    return frozenset(medidas)


def _tokens(s: str) -> frozenset[str]:
    n=normalizar(s)
    toks=[]
    for x in n.split():
        y=_EQ.get(x,x)
        toks.extend(y.split())
    return frozenset(x for x in toks if len(x)>1 and x not in _STOP and not x.isdecimal() and '/' not in x)


def _coincidencia_unica(candidatos: list[tuple[float,dict]], umbral: float, margen: float = .07) -> dict:
    if not candidatos: return {}
    candidatos.sort(key=lambda t:(-t[0],str(t[1].get('codigo_axia') or '')))
    mejor, producto=candidatos[0]
    if mejor < umbral: return {}
    if len(candidatos)>1 and mejor-candidatos[1][0] < margen: return {}
    return referencia_axia(producto)


class CorrelacionadorAxia:
    def __init__(self, productos: list[dict] | None = None):
        self.productos=[]
        self.actualizar(productos or [])

    def actualizar(self, productos: list[dict]) -> None:
        self.productos=[p for p in productos if isinstance(p,dict) and p.get('codigo_axia') and p.get('producto') and
                        str(p.get('activo',True)).lower() not in ('false','0')]
        self._preparados=[(p, normalizar(p['producto']), _tokens(p['producto']), _medidas(p['producto']), familia_producto(p['producto'])) for p in self.productos]
        self._canal.cache_clear()
        self._equipo.cache_clear()
        self._material.cache_clear()

    def canalizacion(self, categoria: str, tipo: str, especificacion: str) -> dict:
        return self._canal(str(categoria),str(tipo),str(especificacion))

    @lru_cache(maxsize=1024)
    def _canal(self, categoria: str, tipo: str, especificacion: str) -> dict:
        cat=normalizar(categoria)
        if cat == 'CONECTORES': cat='CONECTORES'
        if cat not in ('ABRAZADERA','CABLE','CAJAS','CANALETA','CODOS','COPLE','FACEPLATE',
                       'JACK RJ45','PATCH CORD','PATCH PANEL','PLUG RJ45','REGISTRO','TAPAS','TUBO'): return {}
        t=_tokens(tipo)
        if not t or normalizar(tipo) in ('OTRO','NO APLICA','POR DEFINIR'): return {}
        medidas=_medidas(especificacion)
        allquery=_tokens(tipo+' '+especificacion)
        calibre=re.findall(r'(?<!\d)\d+\s*AWG\b', normalizar(especificacion))
        tipo_categoria={'ABRAZADERA':'ABR','TUBO':'TUB','COPLE':'REG',
                        'CANALETA':'CNL','CABLE':'CAB','PATCH CORD':'CAB'}
        candidatos=[]
        for p,normal,tokens,prod_medidas,pcat in self._preparados:
            if pcat != cat: continue
            if medidas and not prod_medidas.intersection(medidas): continue
            if not medidas and prod_medidas and normalizar(especificacion) not in ('NO APLICA','POR DEFINIR',''):
                continue
            if calibre and not all(x.replace(' ','') in normal.replace(' ','') for x in calibre): continue
            # No puede atribuirse un calibre/categoría de cable distinto.
            tipos_cat={x for x in allquery if re.fullmatch(r'CAT(?:5E|6A|6|5|8)',x)}
            if tipos_cat and not tipos_cat.issubset(tokens): continue
            tipo_faltante=t-tokens
            if len(tipo_faltante) > (0 if len(t)<=2 else 1): continue
            base = .65*(len(t & tokens)/len(t)) + .20*(len(allquery&tokens)/max(len(allquery),1))
            base += .15 * SequenceMatcher(None,normalizar(tipo), normal).ratio()
            # Evitar mapear una abrazadera al SKU mal clasificado de TUBO.
            prefijo=tipo_categoria.get(cat)
            if prefijo and str(p.get('codigo_axia') or '').startswith(prefijo+'-'):
                base += .065
            # La descripción corta/exacta es preferible a accesorios con
            # calificadores adicionales que no fueron solicitados.
            base -= min(.13, max(0, len(tokens) - len(t) - 1)*.035)
            candidatos.append((base,p))
        return _coincidencia_unica(candidatos,.71,.035)

    def equipo(self, familia: str, subfamilia: str, marca: str = '', modelo: str = '') -> dict:
        return self._equipo(str(familia),str(subfamilia),str(marca),str(modelo))

    @lru_cache(maxsize=1024)
    def _equipo(self, familia: str, subfamilia: str, marca: str, modelo: str) -> dict:
        sub=normalizar(subfamilia)
        if sub in ('','OTRO','OTROS','POR DEFINIR','NO APLICA'): return {}
        q=_tokens(subfamilia+' '+marca+' '+modelo)
        if not q: return {}
        candidatos=[]
        for p,normal,tokens,_,_ in self._preparados:
            if sub==normal:
                score=1.0
            else:
                cubiertos=q & tokens
                if len(cubiertos)<min(len(q),2) or len(cubiertos)/len(q)<.75: continue
                score=.60*len(cubiertos)/len(q) + .40*SequenceMatcher(None,sub,normal).ratio()
            if marca and normalizar(marca) not in ('OTRO','GENERICO') and not _tokens(marca).issubset(tokens): continue
            if modelo and not _tokens(modelo).issubset(tokens): continue
            candidatos.append((score,p))
        return _coincidencia_unica(candidatos,.82,.08)

    def material(self, nombre: str, especificacion: str = '') -> dict:
        return self._material(str(nombre), str(especificacion))

    @lru_cache(maxsize=1024)
    def _material(self, nombre: str, especificacion: str) -> dict:
        q=normalizar(nombre)
        if not q: return {}
        extra=_medidas(especificacion)
        candidatos=[]
        for p,normal,tokens,medidas,_ in self._preparados:
            if extra and not extra.issubset(medidas): continue
            if q==normal: score=1.0
            else:
                score=SequenceMatcher(None,q,normal).ratio()
                if score<.94 or len(_tokens(q)&tokens)<2: continue
            candidatos.append((score,p))
        return _coincidencia_unica(candidatos,.94,.025)
