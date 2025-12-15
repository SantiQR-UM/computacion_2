# Diagramas del Proyecto

Este directorio contiene los diagramas de arquitectura del sistema en formato PlantUML.

## Archivos de Diagramas

### 1. `arquitectura_actual.puml`
**Diagrama de componentes** mostrando la arquitectura implementada:
- Cliente CLI con argparse
- Servidor asíncrono (asyncio)
- Redis como broker (NO result backend)
- Filesystem compartido para resultados
- 4 Workers de Celery procesando frames completos
- Preview HTTP con Flask y SSE (implementado)

### 2. `flujo_secuencial.puml`
**Diagrama de secuencia** mostrando el flujo completo de procesamiento:
- Fase 1: Conexión y Handshake
- Fase 2: Transmisión de Video
- Fase 3: Extracción de Frames
- Fase 4: Distribución a Workers
- Fase 5: Procesamiento en Workers (paralelo)
- Fase 6: Polling y Recolección
- Fase 7: Reensamblado de Video
- Fase 8: Envío de Resultados

### 3. `deployment_docker.puml`
**Diagrama de deployment** mostrando la arquitectura Docker:
- 6 contenedores (redis, server, preview, 4 workers)
- Red Docker con dual-stack IPv6/IPv4
- Volumen compartido para frames
- Mapeos de puertos (9090 TCP, 8080 HTTP)
- Recursos típicos (RAM, CPU)

### 4. `arquitectura_actual.svg`
SVG renderizado manualmente (alternativa a PlantUML).

## Generación de Diagramas

### Opción 1: Usar PlantUML CLI (Local)

#### Instalación

**Windows (con Chocolatey)**:
```bash
choco install plantuml
```

**Linux (Debian/Ubuntu)**:
```bash
sudo apt-get install plantuml
```

**macOS (Homebrew)**:
```bash
brew install plantuml
```

**Manual (cualquier OS con Java)**:
```bash
# Descargar plantuml.jar
wget https://sourceforge.net/projects/plantuml/files/plantuml.jar/download -O plantuml.jar

# Usar con:
java -jar plantuml.jar diagrama.puml
```

#### Generación

```bash
# Generar un diagrama específico
plantuml arquitectura_actual.puml

# Generar todos los diagramas
plantuml *.puml

# Generar en formato específico
plantuml -tsvg arquitectura_actual.puml   # SVG
plantuml -tpng arquitectura_actual.puml   # PNG
plantuml -tpdf arquitectura_actual.puml   # PDF
```

**Salida**: `arquitectura_actual.png` (o .svg, .pdf según formato)

### Opción 2: Usar PlantUML Online

1. Ir a http://www.plantuml.com/plantuml/uml/
2. Copiar contenido del archivo `.puml`
3. Pegar en el editor online
4. Click en "Submit"
5. Descargar imagen generada

### Opción 3: Usar VS Code (Recomendado para desarrollo)

#### Instalar extensión
1. Abrir VS Code
2. Ir a Extensions (Ctrl+Shift+X)
3. Buscar "PlantUML"
4. Instalar "PlantUML" by jebbs

#### Usar
1. Abrir archivo `.puml`
2. Presionar `Alt+D` para preview
3. Click derecho → "Export Current Diagram" para guardar

#### Configuración recomendada (.vscode/settings.json)
```json
{
  "plantuml.exportFormat": "svg",
  "plantuml.exportSubFolder": false,
  "plantuml.render": "PlantUMLServer"
}
```

### Opción 4: Docker (Sin instalar nada)

```bash
# Generar con Docker
docker run --rm -v $(pwd):/data plantuml/plantuml arquitectura_actual.puml

# Generar todos
docker run --rm -v $(pwd):/data plantuml/plantuml *.puml
```

## Visualización Rápida

### En GitHub
GitHub renderiza automáticamente archivos `.svg` en el navegador. Simplemente abre `arquitectura_actual.svg`.

### En navegador local
```bash
# Generar SVG
plantuml -tsvg arquitectura_actual.puml

# Abrir en navegador
start arquitectura_actual.svg          # Windows
xdg-open arquitectura_actual.svg       # Linux
open arquitectura_actual.svg           # macOS
```

## Modificación de Diagramas

Los archivos `.puml` son **texto plano**. Para modificar:

1. Abrir con cualquier editor de texto
2. Editar sintaxis PlantUML
3. Regenerar diagrama

**Ejemplo de edición**:
```plantuml
' Cambiar título
title Nuevo Título del Sistema

' Añadir componente
component "Nuevo Componente" as nuevo [
  **Nuevo Componente**
  ----
  Descripción
]

' Añadir conexión
nuevo -> servidor : nueva conexión
```

## Sintaxis PlantUML - Referencia Rápida

### Componentes básicos
```plantuml
component "Nombre" as alias
database "DB" as db
node "Server" as srv
cloud "Cloud" as c
storage "Storage" as st
```

### Conexiones
```plantuml
A -> B : mensaje
A --> B : mensaje async (dashed)
A -[#FF0000]-> B : rojo
A -[thickness=3]-> B : gruesa
```

### Secuencia
```plantuml
actor Usuario
participant Servidor
database DB

Usuario -> Servidor : request
activate Servidor
Servidor -> DB : query
DB --> Servidor : result
Servidor --> Usuario : response
deactivate Servidor
```

### Notas
```plantuml
note right of A
  Nota explicativa
end note

note as N1
  Nota flotante
end note
```

## Recursos

- **Documentación oficial**: https://plantuml.com/
- **Guía de componentes**: https://plantuml.com/component-diagram
- **Guía de secuencia**: https://plantuml.com/sequence-diagram
- **Guía de deployment**: https://plantuml.com/deployment-diagram
- **Galería de ejemplos**: https://real-world-plantuml.com/

## Integración en Presentación

### Para impresión (PDF)
```bash
# Generar PDF de alta calidad
plantuml -tpdf arquitectura_actual.puml
plantuml -tpdf flujo_secuencial.puml
plantuml -tpdf deployment_docker.puml
```

### Para presentación (PowerPoint/Google Slides)
```bash
# Generar PNG de alta resolución
plantuml -tpng arquitectura_actual.puml

# O SVG (vectorial, escala sin pérdida)
plantuml -tsvg arquitectura_actual.puml
```

### Para documentación (HTML)
```bash
# Generar SVG (mejor para web)
plantuml -tsvg *.puml
```

## Comparación: SVG Manual vs PlantUML

| Aspecto | SVG Manual | PlantUML |
|---------|------------|----------|
| **Mantenibilidad** | ❌ Difícil (código XML) | ✅ Fácil (texto plano) |
| **Legibilidad** | ❌ Código complejo | ✅ Sintaxis clara |
| **Control preciso** | ✅ Posición exacta | ⚠️ Layout automático |
| **Velocidad de edición** | ❌ Lento | ✅ Rápido |
| **Versionado (Git)** | ⚠️ Diffs ilegibles | ✅ Diffs claros |

**Recomendación**: Usar PlantUML para diagramas técnicos que cambien frecuentemente. SVG manual solo para diseños muy específicos que requieran control pixel-perfect.

## Troubleshooting

### "Command not found: plantuml"
**Solución**: Instalar PlantUML (ver sección Instalación) o usar Docker.

### "Error: GraphViz dot not found"
**Solución**: Instalar GraphViz:
```bash
# Windows
choco install graphviz

# Linux
sudo apt-get install graphviz

# macOS
brew install graphviz
```

### Diagramas muy grandes/ilegibles
**Solución**: Ajustar escala en el archivo .puml:
```plantuml
scale 1.5
' o
scale 2048 width
' o
scale 2048 height
```

### Layout automático no queda bien
**Solución**: Usar directivas de layout:
```plantuml
left to right direction
' o
top to bottom direction

' Forzar posiciones
A -down-> B
C -right-> D
```

---

**Última actualización**: 2025-11-18
