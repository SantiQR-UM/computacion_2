# Rúbrica Evaluativa - TP2 Sistema de Scraping Distribuido

## Información General

**Trabajo Práctico**: TP2 - Sistema de Scraping y Análisis Web Distribuido
**Fecha de evaluación**: N/A
**Puntaje máximo**: 110 puntos (95 base + 15 bonus)

---

## 1. Funcionalidad Completa (30 puntos)

### 1.1 Parte A: Servidor de Scraping Asíncrono (10 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Servidor HTTP asíncrono | 2 | Servidor implementado con aiohttp correctamente | ☐ |
| Scraping asíncrono | 2 | Requests HTTP no bloqueantes con asyncio | ☐ |
| Extracción de datos | 3 | Extrae título, links, meta tags, estructura, imágenes | ☐ |
| Comunicación con Servidor B | 2 | Se comunica correctamente via sockets | ☐ |
| Respuesta consolidada | 1 | Devuelve JSON con formato correcto | ☐ |

**Subtotal Parte A**: ____/10

### 1.2 Parte B: Servidor de Procesamiento (10 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Servidor con sockets | 2 | SocketServer implementado correctamente | ☐ |
| Pool de procesos | 2 | Usa multiprocessing.Pool apropiadamente | ☐ |
| Screenshots | 2 | Genera screenshots con Selenium/Playwright | ☐ |
| Análisis de rendimiento | 2 | Calcula métricas de performance | ☐ |
| Procesamiento de imágenes | 2 | Descarga y genera thumbnails | ☐ |

**Subtotal Parte B**: ____/10

### 1.3 Parte C: Transparencia (5 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Interfaz única | 2 | Cliente solo interactúa con Servidor A | ☐ |
| Coordinación automática | 2 | Servidor A coordina con B automáticamente | ☐ |
| Manejo de errores | 1 | Errores manejados transparentemente | ☐ |

**Subtotal Parte C**: ____/5

### 1.4 Funciones Principales (5 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Scraping de HTML | 1.25 | Función de scraping implementada | ☐ |
| Extracción de metadatos | 1.25 | Función de extracción implementada | ☐ |
| Generación de screenshot | 1.25 | Función de screenshot implementada | ☐ |
| Análisis de rendimiento | 1.25 | Función de análisis implementada | ☐ |

**Subtotal Funciones**: ____/5

---

## 2. Uso Correcto de Asyncio (20 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Event loop no bloqueante | 5 | No hay operaciones bloqueantes en el event loop | ☐ |
| Cliente HTTP asíncrono | 4 | Usa aiohttp correctamente (no requests) | ☐ |
| Operaciones I/O asíncronas | 4 | await en operaciones I/O, no bloquea | ☐ |
| Comunicación asíncrona | 4 | Sockets asíncronos con asyncio.open_connection | ☐ |
| Manejo de concurrencia | 3 | Múltiples clientes manejados concurrentemente | ☐ |

**Subtotal Asyncio**: ____/20

---

## 3. Uso Correcto de Multiprocessing (20 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Pool de procesos | 5 | Pool implementado y usado correctamente | ☐ |
| Procesamiento paralelo | 5 | Tareas CPU-bound ejecutadas en paralelo | ☐ |
| IPC (comunicación inter-proceso) | 4 | Comunicación entre procesos funcional | ☐ |
| Sincronización | 3 | Manejo apropiado de recursos compartidos | ☐ |
| Gestión de recursos | 3 | Pool se cierra correctamente, no hay leaks | ☐ |

**Subtotal Multiprocessing**: ____/20

---

## 4. Manejo de Errores (10 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| URLs inválidas | 2 | Valida y rechaza URLs inválidas | ☐ |
| Timeouts | 2 | Implementa timeouts apropiados (30s scraping) | ☐ |
| Errores de comunicación | 2 | Maneja errores entre servidores gracefully | ☐ |
| Recursos no disponibles | 2 | Maneja imágenes/recursos faltantes | ☐ |
| Logging de errores | 2 | Errores registrados con logging apropiado | ☐ |

**Subtotal Manejo de Errores**: ____/10

---

## 5. Calidad de Código (10 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Código limpio | 3 | Código legible, sin code smells | ☐ |
| Modularidad | 3 | Separación clara de responsabilidades | ☐ |
| Documentación | 2 | Docstrings completos en funciones/clases | ☐ |
| Convenciones Python | 1 | Sigue PEP 8, convenciones de nombres | ☐ |
| Reutilización | 1 | DRY, evita duplicación de código | ☐ |

**Subtotal Calidad**: ____/10

---

## 6. Interfaz CLI (5 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Argparse implementado | 2 | Usa argparse (o getopt) correctamente | ☐ |
| Ayuda clara | 1 | Mensaje de ayuda (-h) informativo | ☐ |
| Argumentos requeridos | 1 | -i, -p requeridos y validados | ☐ |
| Opciones adicionales | 1 | Workers, processes, debug implementados | ☐ |

**Subtotal CLI**: ____/5

---

## 7. Networking (Adicional)

### Evaluación de requisitos de networking

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Soporte IPv4/IPv6 | Parte del 30 | Servidor A soporta ambos protocolos | ☐ |
| Protocolo binario eficiente | Parte del 20 | Protocolo con header + payload implementado | ☐ |
| Serialización apropiada | Parte del 20 | JSON para mensajes inter-servidor | ☐ |

**Nota**: Estos puntos están incluidos en las secciones anteriores.

---

## 8. BONUS TRACK (15 puntos máximo)

### Opción 1: Sistema de Cola con Task IDs (5 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Task ID retornado | 2 | Servidor retorna task_id inmediatamente | ☐ |
| Endpoint /status | 2 | Consulta estado de tarea por ID | ☐ |
| Endpoint /result | 1 | Descarga resultado cuando completa | ☐ |

**Subtotal Opción 1**: ____/5

### Opción 2: Rate Limiting y Caché (5 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Rate limiting | 2 | Límite de requests por dominio | ☐ |
| Sistema de caché | 2 | Cache con TTL (< 1 hora) | ☐ |
| Implementación (Redis/dict) | 1 | Backend de caché funcional | ☐ |

**Subtotal Opción 2**: ____/5

### Opción 3: Análisis Avanzado (5 puntos)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Detección de tecnologías | 2 | Detecta frameworks, CMS, etc. | ☐ |
| Análisis de SEO | 2 | Score de optimización SEO | ☐ |
| Análisis de accesibilidad | 1 | Contraste, alt tags, etc. | ☐ |

**Subtotal Opción 3**: ____/5

**Subtotal BONUS**: ____/15

---

## 9. Criterios Adicionales de Evaluación

### Testing (hasta +10 puntos adicionales)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| Tests unitarios | 5 | Tests para módulos individuales | ☐ |
| Tests de integración | 3 | Tests end-to-end del sistema | ☐ |
| Cobertura | 2 | Cobertura > 70% de código crítico | ☐ |

**Subtotal Testing**: ____/10

### Documentación (hasta +10 puntos adicionales)

| Criterio | Puntos | Descripción | Evaluación |
|----------|--------|-------------|------------|
| README completo | 4 | Instalación, uso, ejemplos claros | ☐ |
| Docstrings | 3 | Documentación inline completa | ☐ |
| Diagramas | 2 | Diagramas de arquitectura/flujo | ☐ |
| Comentarios | 1 | Comentarios explicativos en código complejo | ☐ |

**Subtotal Documentación**: ____/10

---

## Resumen de Evaluación

| Sección | Puntaje Obtenido | Puntaje Máximo |
|---------|------------------|----------------|
| 1. Funcionalidad Completa | ____ | 30 |
| 2. Uso Correcto de Asyncio | ____ | 20 |
| 3. Uso Correcto de Multiprocessing | ____ | 20 |
| 4. Manejo de Errores | ____ | 10 |
| 5. Calidad de Código | ____ | 10 |
| 6. Interfaz CLI | ____ | 5 |
| **SUBTOTAL BASE** | **____** | **95** |
| 8. BONUS TRACK | ____ | 15 |
| 9a. Testing (adicional) | ____ | 10 |
| 9b. Documentación (adicional) | ____ | 10 |
| **TOTAL** | **____** | **130** |

---

## Escala de Calificación

| Puntaje | Calificación | Descripción |
|---------|--------------|-------------|
| 95-130 | Excelente (10) | Cumple todos los requisitos + bonus/extras |
| 85-94 | Muy Bueno (9) | Cumple casi todos los requisitos con calidad |
| 75-84 | Bueno (8) | Cumple requisitos principales con algunas falencias menores |
| 65-74 | Aprobado (7) | Cumple requisitos mínimos |
| 57-64 | Aprobado (6) | Cumple requisitos mínimos con falencias |
| 48-56 | Aprobado (5) | Funcionalidad básica implementada |
| < 48 | Desaprobado (< 5) | No cumple requisitos mínimos |

---

## Observaciones Generales

**Fortalezas identificadas**:
-
-
-

**Áreas de mejora**:
-
-
-

**Comentarios adicionales**:




---

## Evaluador

**Nombre**: ___________________________
**Fecha**: ___________________________
**Firma**: ___________________________

---

## Criterios de Penalización

| Infracción | Penalización |
|------------|--------------|
| Código no ejecuta | -50 puntos |
| Dependencias no documentadas | -10 puntos |
| No sigue estructura sugerida | -5 puntos |
| Plagio / Código copiado | 0 puntos (desaprobación automática) |
| Entrega tardía (por día) | -10 puntos |
| Falta README | -10 puntos |
| No usa librerías requeridas | -15 puntos |

---

**Notas**:
1. El puntaje base máximo es 95 puntos
2. Se pueden obtener hasta 35 puntos adicionales (15 bonus + 10 testing + 10 docs)
3. El puntaje final se normaliza a escala 0-10
4. Es necesario obtener al menos 48 puntos (50% del base) para aprobar
5. La implementación de bonus es opcional pero altamente recomendada
