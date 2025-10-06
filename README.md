
---

#  Proyecto de Compiladores — Intermediate Code Generation (Compiscript)

##  Descripción General

Este repositorio implementa las **fases de análisis semántico y generación de código intermedio (TAC)** para el lenguaje académico **Compiscript** (subset de TypeScript).
El sistema usa **ANTLR 4** para generar el *front-end* (lexer y parser), y **Python 3** para las fases de análisis semántico, gestión de ámbitos, tabla de símbolos, y traducción a código intermedio tipo *Three Address Code (TAC)*.

El entorno de desarrollo está completamente **contenedorizado en Docker**, por lo que puede ejecutarse en Ubuntu o WSL sin dependencias locales adicionales.

---

##  Requisitos

* Ubuntu (local o WSL)
* Docker y GNU Make
* Java 17+ (para ANTLR)
* Python 3.12+
* pytest (para pruebas)

---

##  Estructura del Proyecto

```
Intermediate_Code_Gen/
├── Makefile
├── Dockerfile
├── requirements.txt
├── program/
│   ├── Compiscript.g4              # Gramática ANTLR (lexer + parser)
│   ├── Compiscript.bnf             # Versión en BNF
│   ├── Driver.py                   # Punto de entrada del compilador
│   ├── program.cps                 # Ejemplo de entrada válida
│   ├── program_bad.cps             # Ejemplo con errores
│   ├── program_ok.cps              # Ejemplo correcto
│   ├── semantic/                   # Fase semántica
│   │   ├── typesys.py              # Sistema de tipos
│   │   ├── symbols.py              # Representación de símbolos
│   │   ├── scopes.py               # Ámbitos y pila de entornos
│   │   ├── type_checker.py         # Visitor semántico
│   │   ├── error_reporter.py       # Reporte de errores
│   │   ├── table.py                # Impresión de tabla de símbolos
│   │   └── __init__.py
│   ├── ir/                         # Fase de código intermedio (TAC)
│   │   ├── tac_ir.py               # Definición de instrucciones TAC
│   │   ├── tac_builder.py          # Construcción del IR desde el AST
│   │   ├── tac_gen.py              # Generador de TAC desde nodos
│   │   ├── label_mgr.py            # Gestión de etiquetas
│   │   ├── temp_alloc.py           # Asignador y reciclaje de temporales
│   │   └── __init__.py
│   ├── runtime/activation_record.py # Soporte para registros de activación
│   ├── ide/app.py                  # Interfaz Streamlit para probar el compilador
│   └── docs/IR_Spec.md             # Especificación del TAC
├── tests/
│   ├── semantic/                   # Tests de la fase semántica
│   ├── ir/                         # Tests de generación de código intermedio
│   └── conftest.py
└── .gitignore
```

---

##  Flujo de Trabajo

1. **Análisis Léxico / Sintáctico:**
   Generados automáticamente desde `Compiscript.g4` con ANTLR.

2. **Análisis Semántico:**
   Implementado con visitantes en Python (`type_checker.py`), conectando las estructuras `ScopeStack`, `SymbolTable`, `TypeSystem` y `ErrorReporter`.

3. **Generación de Código Intermedio (TAC):**
   Traduce el árbol sintáctico en instrucciones tipo *Three Address Code* manejando expresiones, control de flujo, funciones, clases y arreglos.

---

##  Componentes Principales

###  Tipos y Símbolos (`semantic/typesys.py`, `semantic/symbols.py`)

* Define los tipos primitivos (`integer`, `string`, `boolean`, `void`, `null`) y compuestos (`ArrayType`, `FunctionType`, `ClassType`).
* Implementa las reglas de compatibilidad de tipos y asignación (`can_assign`, `arithmetic_type`, `comparison_type`).
* Gestiona símbolos de variables, parámetros, funciones y clases.

###  Ámbitos (`semantic/scopes.py`)

* `Scope` base con reglas de definición/resolución.
* Subclases: `GlobalScope`, `BlockScope`, `FunctionScope`, `ClassScope`.
* `ScopeStack` maneja la pila de entornos activos.
* Permite detectar shadowing y errores de redeclaración.

###  Analizador Semántico (`semantic/type_checker.py`)

* Visitor basado en ANTLR: abre y cierra scopes según nodos.
* Verifica tipos en expresiones, asignaciones, control de flujo, clases y arreglos.
* Integra el `ErrorReporter` para registrar errores semánticos.

###  Generación TAC (`ir/`)

* `tac_ir.py`: define clases `Instruction`, `Temp`, `Label`, `Operand`.
* `tac_builder.py`: traduce expresiones y sentencias en instrucciones TAC.
* `tac_gen.py`: gestiona etiquetas, saltos y flujo de control.
* `temp_alloc.py`: asignador con **reciclaje** de temporales reutilizables.
* `label_mgr.py`: genera etiquetas únicas (`Lif_cond0`, `Lfor_end1`, etc.).
* Documentación completa en `docs/IR_Spec.md`.

---

##  Tests

Los tests están en `tests/semantic/` y `tests/ir/`, e incluyen:

* **Semántica:** Tipos, funciones, scopes, clases, control de flujo.
* **Intermedio (TAC):** Generación de expresiones, bucles, llamadas, arreglos.
* Ejemplos esperados (`*.tac`) bajo `tests/ir/snapshots/`.

Ejecutar todo con:

```bash
make test
```

---

##  Instrucciones de Uso con Docker

### 1. Construir el contenedor

```bash
make docker-build
```

### 2. Generar lexer/parser/visitor con ANTLR

```bash
make gen
```

### 3. Ejecutar el compilador sobre un programa de ejemplo

```bash
make run
```

### 4. Correr pruebas unitarias

```bash
make test
```

### 5. Limpiar artefactos

```bash
make clean
```

> Todos los comandos ejecutan internamente Python con:
> `export PYTHONPATH=/workspace:/workspace/program`

---

##  IDE Streamlit

Para lanzar el entorno interactivo:

```bash
docker run --rm -ti -p 8501:8501 \
  -v "$(pwd)":/workspace -w /workspace csp-image \
  bash -lc 'export PYTHONPATH=/workspace:/workspace/program && \
            streamlit run program/ide/app.py --server.port=8501 --server.address=0.0.0.0'
```

Abrir en el navegador: **[http://localhost:8501](http://localhost:8501)**

Permite:

* Escribir código Compiscript.
* Visualizar el árbol sintáctico.
* Ver tabla de símbolos y errores semánticos.
* Generar el TAC paso a paso.

---

##  Lenguaje Compiscript (Subset)

Ejemplo:

```cps
class Persona {
  let nombre: string;
  function constructor(nombre: string) { this.nombre = nombre; }
  function saludar(): void { print("Hola, soy " + this.nombre); }
}

function main(): void {
  let p = new Persona("Oscar");
  p.saludar();
}
```

---

