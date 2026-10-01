"""Consola ejecutiva de trazabilidad del ciclo operativo AXIA."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from supabase_config import supabase
from services.levantamientos_schema import TABLA_LEVANTAMIENTOS, COLUMNAS_LEVANTAMIENTOS
from services.cotizaciones_schema import TABLA_COTIZACIONES, COLUMNAS_COTIZACIONES
from services.ordenes_trabajo_schema import TABLE as TABLA_OT, SELECT_COLUMNS as COLUMNAS_OT
from services.bitacoras_service import TABLA_BITACORAS, COLUMNAS_BITACORAS
from services.ordenes_servicio_service import TABLA_ORDENES, COLUMNAS_ORDENES
from services.query_compat import execute_select_compatible


def _dt(v):
    if not v: return None
    if isinstance(v, datetime): return v
    s=str(v).strip().replace('Z','+00:00')
    try:
        d=datetime.fromisoformat(s)
    except Exception:
        for fmt in ('%Y-%m-%d','%d/%m/%Y'):
            try: d=datetime.strptime(s,fmt); break
            except Exception: d=None
    if d and d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
    return d

def _hours(a,b):
    a,b=_dt(a),_dt(b)
    return round((b-a).total_seconds()/3600,1) if a and b and b>=a else None

def _days(a,b):
    h=_hours(a,b)
    return round(h/24,1) if h is not None else None

def _all(table, cols, limit=1000):
    r=execute_select_compatible(supabase, table, cols, lambda q:q.order('fecha_registro',desc=True).limit(limit))
    return list(r.data or [])

def obtener_panel_direccion(limite=500):
    levs=_all(TABLA_LEVANTAMIENTOS,COLUMNAS_LEVANTAMIENTOS,limite)
    cots=_all(TABLA_COTIZACIONES,COLUMNAS_COTIZACIONES,limite*3)
    ots=_all(TABLA_OT,COLUMNAS_OT,limite*2)
    bits=_all(TABLA_BITACORAS,COLUMNAS_BITACORAS,limite*4)
    oss=_all(TABLA_ORDENES,COLUMNAS_ORDENES,limite*2)
    now=datetime.now(timezone.utc)
    out=[]
    for lev in levs:
        lid=lev.get('id_levantamiento'); folio=str(lev.get('lev_folio') or '')
        lc=[c for c in cots if (lid and c.get('id_levantamiento')==lid) or str(c.get('lev_folio') or '')==folio]
        lc.sort(key=lambda x:str(x.get('fecha_registro') or ''))
        lo=[o for o in ots if (lid and o.get('id_levantamiento')==lid) or str(o.get('ot_folio_levantamiento') or '')==folio]
        lo.sort(key=lambda x:str(x.get('fecha_registro') or x.get('ot_fecha') or ''))
        ot=lo[-1] if lo else {}
        otfolio=str(ot.get('ot_folio') or '')
        lb=[b for b in bits if (ot.get('ot_id') and b.get('ot_id')==ot.get('ot_id')) or (otfolio and str(b.get('bit_ot_folio') or '')==otfolio)]
        los=[o for o in oss if (lid and o.get('id_levantamiento')==lid) or (ot.get('ot_id') and o.get('ot_id')==ot.get('ot_id')) or (otfolio and str(o.get('os_folio_ot') or '')==otfolio)]
        los.sort(key=lambda x:str(x.get('os_fecha_cierre') or x.get('fecha_registro') or ''))
        os=los[-1] if los else {}
        inicio=lev.get('fecha_registro') or lev.get('lev_fecha_realizacion')
        aut=lev.get('lev_fecha_validacion')
        cot0=lc[0] if lc else {}
        cot_fin=next((c for c in reversed(lc) if c.get('cot_fecha_finalizacion')), {})
        ot_inicio=ot.get('fecha_registro') or ot.get('ot_fecha')
        cierre=os.get('os_fecha_cierre') or (os.get('fecha_actualizacion') if str(os.get('os_estatus'))=='3' else None)
        dias=int(float(lev.get('lev_dias_trabajo') or lev.get('lev_duracion_proyecto') or 0)) if str(lev.get('lev_dias_trabajo') or lev.get('lev_duracion_proyecto') or '').strip() else 0
        deadline=(_dt(ot_inicio)+timedelta(days=dias)) if _dt(ot_inicio) and dias else None
        referencia=_dt(cierre) or now
        if not ot: estado='PENDIENTE OT'
        elif cierre: estado='FINALIZADO EN TIEMPO' if not deadline or referencia<=deadline else 'FINALIZADO FUERA DE TIEMPO'
        elif deadline and referencia>deadline: estado='VENCIDO'
        else: estado='EN TIEMPO'
        avance=max([int(float(b.get('bit_porcentaje_avance') or 0)) for b in lb] or [100 if cierre else 0])
        out.append({
            'folio':folio,'cliente':lev.get('lev_cliente') or '', 'tipo':lev.get('lev_tipo') or '',
            'tecnico':lev.get('lev_tecnico') or lev.get('creado_por') or '', 'inicio':inicio,
            'requerimiento':lev.get('lev_descripcion') or lev.get('lev_requerimientos') or '',
            'dias_planeados':dias, 'personas':lev.get('lev_personas_considerar') or '',
            'autorizado_por':lev.get('lev_validado_por') or '', 'fecha_autorizacion':aut,
            'horas_autorizacion':_hours(inicio,aut), 'cotizaciones':len(lc),
            'esi':cot0.get('cot_esi') or '', 'fecha_cotizacion':cot0.get('fecha_registro'),
            'horas_esi':_hours(aut,cot0.get('fecha_registro')), 'fecha_autorizacion_cliente':cot_fin.get('cot_fecha_finalizacion'),
            'horas_cliente':_hours(cot0.get('fecha_registro'),cot_fin.get('cot_fecha_finalizacion')),
            'ot_folio':otfolio,'ot_inicio':ot_inicio,'fecha_limite':deadline.isoformat() if deadline else None,
            'avance':avance,'os_folio':os.get('os_folio') or '', 'cierre':cierre,
            'dias_totales':_days(inicio,cierre or now), 'estado':estado,
            'faltante': ('Proceso concluido' if cierre else 'Orden de servicio final' if avance>=100 else 'Ejecución / bitácora' if ot else 'Generación de Orden de Trabajo'),
        })
    return out
