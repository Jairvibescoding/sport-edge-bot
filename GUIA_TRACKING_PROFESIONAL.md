# GUÍA PROFESIONAL: HOJA DE TRACKING DE APUESTAS

## PASO 1: CREAR GOOGLE SHEETS

1. Ve a **sheets.google.com**
2. Click **"Crear hoja nueva"**
3. Nómbrala: **"Tracking Apuestas Profesional - 2026"**

---

## PASO 2: CONFIGURAR HEADERS (Fila 1)

Copia estos headers en la fila 1:

| A | B | C | D | E | F | G | H | I | J | K | L | M | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FECHA | DEPORTE | MERCADO | EVENTO | TIPO | CASA | CUOTA | LÍNEA CIERRE | UNIDADES | RESULTADO | GANANCIA/PÉRDIDA | CLV | EV | NOTAS |

---

## PASO 3: IMPORTAR TU PRIMERA APUESTA

### En la fila 2, escribe:

| Celda | Contenido |
|-------|-----------|
| A2 | 15/09/2026 |
| B2 | MLB |
| C2 | Player Props |
| D2 | Dodgers vs Reds |
| E2 | Over 7.5 Ks |
| F2 | micasino |
| G2 | 1.90 |
| H2 | (llenar después del partido) |
| I2 | 1.73 |
| J2 | (Win/Loss/Push) |
| K2 | (llenar después) |
| L2 | (llenar después) |
| M2 | +21.6% |
| N2 | Yamamoto K% rival 25.5% - forma reciente 8.8 Ks avg |

---

## PASO 4: FÓRMULAS PROFESIONALES

### Crear una hoja llamada "DASHBOARD" con estas fórmulas:

### CELDA B1: Bankroll Actual
```
=3065-SUMA(K:K)
```

### CELDA B2: Total Apostado
```
=SUMA(I:I)*30.65
```

### CELDA B3: Ganancia Neta
```
=SUMA(K:K)
```

### CELDA B4: ROI %
```
=(B3/B2)*100
```

### CELDA B5: Yield
```
=B3/SUMA(I:I)
```

### CELDA B6: Hit Rate %
```
=CONTAR.SI(J:J,"Win")/CONTAR.SI(J:J,"<>")*100
```

### CELDA B7: Total Apuestas
```
=CONTAR.SI(J:J,"<>")
```

### CELDA B8: Wins
```
=CONTAR.SI(J:J,"Win")
```

### CELDA B9: Losses
```
=CONTAR.SI(J:J,"Loss")
```

### CELDA B10: Push
```
=CONTAR.SI(J:J,"Push")
```

### CELDA B11: Unidades Apostadas
```
=SUMA(I:I)
```

### CELDA B12: Unidades Ganadas
```
=SUMA.SI(J:J,"Win",K:K)
```

### CELDA B13: Unidades Perdidas
```
=SUMA.SI(J:J,"Loss",K:K)*-1
```

### CELDA B14: Promedio Cuota
```
=PROMEDIO(G:G)
```

### CELDA B15: CLV Promedio
```
=PROMEDIO(L:L)
```

---

## PASO 5: FORMATEO PROFESIONAL

### Colores sugeridos:

| Elemento | Color |
|----------|-------|
| Headers | Azul oscuro (#1a73e8) |
| Win | Verde (#0f9d58) |
| Loss | Rojo (#db4437) |
| Push | Amarillo (#f4b400) |
| Bankroll | Dorado (#f9ab00) |

### Formato de números:

| Columna | Formato |
|---------|---------|
| Fecha | DD/MM/YYYY |
| Cuota | 0.00 |
| Unidades | 0.00 |
| Ganancia | 0.00 |
| EV | +0.0% |
| CLV | +0.0% |

---

## PASO 6: GRÁFICOS RECOMENDADOS

### Gráfico 1: Evolución del Bankroll
- Tipo: Línea
- X: Fecha
- Y: Bankroll

### Gráfico 2: Resultados por Deporte
- Tipo: Torta
- Datos: Count por deporte

### Gráfico 3: ROI por Mercado
- Tipo: Barras
- X: Mercado
- Y: ROI %

---

## PASO 7: VALIDACIÓN DE DATOS

### Crear listas desplegables:

**Columna B (Deporte):**
```
MLB,Tenis,Fútbol,NBA,NFL,Otros
```

**Columna J (Resultado):**
```
Win,Loss,Push,Esperando
```

**Columna F (Casa):**
```
micasino,1xBet,Bet365,Otros
```

---

## PASO 8: FÓRMULAS AVANZADAS

### ROI por Deporte (en Dashboard):
```
=SI.ERROR(SUMA.SI(B:B,"MLB",K:K)/SUMA.SI(B:B,"MLB",I:I)*100,0)
```

### ROI por Mercado:
```
=SI.ERROR(SUMA.SI(C:C,"Player Props",K:K)/SUMA.SI(C:C,"Player Props",I:I)*100,0)
```

### Mejor Casa:
```
=INDICE(F:F,COINCIDIR(MÁX(SUMA.SI.FILA(F:F,K:K)),SUMA.SI.FILA(F:F,K:K),0))
```

### Racha Actual:
```
=CONTAR.SI.INVERTIR(INDICE(J:J,0):J2,"Win")-1
```

---

## PASO 9: TABLA RESUMEN (DASHBOARD)

### Crear tabla en Dashboard:

| Métrica | Fórmula | Valor |
|---------|---------|-------|
| Bankroll Inicial | (manual) | 3,065 Bs |
| Bankroll Actual | =3065-SUMA(K:K) | |
| Total Apostado | =SUMA(I:I)*30.65 | |
| Ganancia Neta | =SUMA(K:K) | |
| ROI % | =(B3/B2)*100 | |
| Yield | =B3/SUMA(I:I) | |
| Hit Rate % | =CONTAR.SI(J:J,"Win")/CONTAR.SI(J:J,"<>")*100 | |
| Total Apuestas | =CONTAR.SI(J:J,"<>") | |
| Wins | =CONTAR.SI(J:J,"Win") | |
| Losses | =CONTAR.SI(J:J,"Loss") | |
| Promedio Cuota | =PROMEDIO(G:G) | |
| CLV Promedio | =PROMEDIO(L:L) | |

---

## PASO 10: PLANTILLA LISTA PARA USAR

### Copia esto en tu hoja principal:

```
FECHA,DEPORTE,MERCADO,EVENTO,TIPO,CASA,CUOTA,LINEA_CIERRE,UNIDADES,RESULTADO,GANANCIA,CLV,EV,NOTAS
15/09/2026,MLB,Player Props,Dodgers vs Reds,Over 7.5 Ks,micasino,1.90,,1.73,Esperando,,+21.6%,Yamamoto K% rival 25.5%
```

---

## CHECKLIST PROFESIONAL

- [ ] Crear Google Sheets
- [ ] Configurar headers
- [ ] Importar primera apuesta
- [ ] Agregar fórmulas del Dashboard
- [ ] Formatear colores
- [ ] Crear gráficos
- [ ] Agregar validación de datos
- [ ] Probar fórmulas
- [ ] Registrar apuesta de hoy

---

## CONSEJOS FINALES

1. **Actualiza CADA día** después de los partidos
2. **Revisa semanalmente** (domingos)
3. **Ajusta units** mensualmente si bankroll cambia > 20%
4. **No borres apuestas perdidas** (son parte del proceso)
5. **Confía en el proceso** (mínimo 500 apuestas)

---

**¿Necesitas ayuda con alguna fórmula específica?**
