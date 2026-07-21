"""Benchmark sintético y reproducible; no sustituye una prueba física."""
from __future__ import annotations
import json, platform, statistics, time
from pathlib import Path


def medir(fn, rep=20):
    valores=[]
    for _ in range(rep):
        ini=time.perf_counter(); fn(); valores.append((time.perf_counter()-ini)*1000)
    return {"promedio_ms": round(statistics.mean(valores),3), "p95_ms": round(sorted(valores)[int(len(valores)*.95)-1],3)}


def main():
    datos=[{"id":i,"nombre":f"Usuario {i}","tipo":i%6+1} for i in range(5000)]
    resultado={
      "nota":"Prueba sintética local. La validación final debe ejecutarse en hardware objetivo y con Supabase real.",
      "equipo":platform.platform(),
      "filtrar_5000":medir(lambda:[x for x in datos if x["tipo"] in (2,3)]),
      "serializar_5000":medir(lambda:json.dumps(datos,ensure_ascii=False)),
    }
    salida=Path("benchmark_rendimiento.json"); salida.write_text(json.dumps(resultado,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(resultado,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
