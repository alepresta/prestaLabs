#!/usr/bin/env python3
"""
Script para normalizar todos los dominios existentes en la base de datos
(preprocesamiento para consultas eficientes y sin duplicados lógicos).
"""
import os
import django


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestaLabs.settings")
    django.setup()
    from core.models import BusquedaDominio
    from core.views_app import normalizar_dominio

    total = 0
    actualizados = 0
    for b in BusquedaDominio.objects.all():
        dom_norm = normalizar_dominio(b.dominio)
        if b.dominio != dom_norm:
            b.dominio = dom_norm
            b.save(update_fields=["dominio"])
            actualizados += 1
        total += 1
    print(f"Total registros: {total}")
    print(f"Dominios normalizados/actualizados: {actualizados}")


if __name__ == "__main__":
    main()
