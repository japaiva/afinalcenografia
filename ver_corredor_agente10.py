#!/usr/bin/env python3
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente
a = Agente.objects.get(id=10)

# Encontrar linha com corredor
lines = a.task_instructions.split('\n')
for i, line in enumerate(lines):
    if 'corredor' in line.lower() and 'deposito' not in line.lower():
        print(f"Linha {i}: {line}")
        # Mostrar contexto (3 linhas antes e depois)
        for j in range(max(0, i-3), min(len(lines), i+8)):
            print(f"  {j}: {lines[j]}")
        print()
