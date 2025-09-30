# Proyecto de Compiladores — Semantic Analysis (Compiscript)

## Descripción General

Este repositorio contiene la implementación de la fase de Análisis Semántico para un lenguaje académico llamado Compiscript (subset de TypeScript). 
El proyecto está preparado para ejecutarse en Ubuntu dentro de Docker, usando ANTLR 4 para el front-end y Python para el checker y las pruebas.

## Requisitos

- Ubuntu (local o WSL recomendado)
- Docker y GNU Make
- Java 17 (para ANTLR)
- Python 3.12+
- pytest (para correr los tests)

## Estructura del Proyecto

```
Semantic_Analysis/
├── Makefile
├── Dockerfile
├── requirements.txt
├── program/
│   ├── Compiscript.g4         # Gramática ANTLR
│   ├── Compiscript.bnf        # Gramática en BNF
│   ├── Driver.py              # Punto de entrada principal
│   ├── program.cps            # Programa de prueba
│   ├── semantic/
│   │   ├── __init__.py
│   │   ├── typesys.py         # Sistema de Tipos
│   │   ├── symbols.py         # Símbolos (variables, funciones, clases)
│   │   ├── scopes.py          # Ámbitos y resolución de nombres
│   │   ├── type_checker.py    # Infraestructura del Visitor
|   |   ├── error_reporter.py   # Reporter de errores (común)
│   |   ├── table.py            # Impresión de tabla de símbolos (utilidad)
│   |   └──app.py              # IDE Streamlit
├── tests/
│   ├── semantic/
│   |   ├── symbols_test.py
│   │   ├── test_scopes.py
│   |   ├── test_scopes_stack.py
│   |   ├── test_smoke.py
│   |   ├── test_tc_arrays.
│   |   ├── test_tc_assign_and_consts.py
│   │   ├── test_tc_classes.py
│   │   ├── test_tc_closures.py
│   │   ├── test_tc_control_flow.py
│   │   ├── test_tc_functions.py
│   │   ├── typesys_test.py
│   |   ├── util.py
│   │   └── ... otros tests iniciales
└── .gitignore
```

## Flujo de Trabajo

### Núcleo de Tipos & Símbolos
- Archivos: `typesys.py`, `symbols.py`
- Implementaciones:
  - Sistema de tipos: `Type`, `ArrayType`, `FunctionType`, `ClassType`, `NullType`.
  - Reglas: `can_assign`, `arithmetic_type`, `logical_type`, `comparison_type`.
  - Símbolos: `VarSymbol`, `ParamSymbol`, `FuncSymbol`, `ClassSymbol`.
- Tests: compatibilidad de tipos, operaciones válidas/ inválidas, creación de símbolos.

### Ámbitos & Resolución de Nombres
- Archivos: `scopes.py`, integración mínima en `type_checker.py`.
- Implementaciones:
  - Clase `Scope` (define/resolve, shadowing y prohibición de redeclaración).
  - Subclases: `GlobalScope`, `BlockScope`, `FunctionScope`, `ClassScope`.
  - Clase `ScopeStack` (manejo de pila de scopes, push/pop).
- Tests:
  - `test_scopes.py`: definición/resolución, shadowing, cascada hacia padre.
  - `test_scopes_func_class.py`: FunctionScope y ClassScope.
  - `test_scopes_stack.py`: pruebas de la pila de scopes.
- Resultado: listo para que se consuma el API en el Visitor.

### TypeChecker (Visitor) & Reglas Semánticas
- Archivo: `type_checker.py`
- Tareas:
  - Conectar con `CompiscriptVisitor` generado por ANTLR.
  - Implementar reglas de variables, expresiones, control de flujo, funciones, clases y arreglos.
  - Usar `ScopeStack` y reportar errores con `ErrorReporter`.

## Instrucciones de Configuración
> Todo corre en Docker, no necesitas Java ni Python locales.

### 1. Construir el contenedor Docker
```bash
make docker-build
```

### 2. Generar Lexer/Parser/Visitor de ANTLR
```bash
make gen
```
Esto ejecuta ANTLR dentro del contenedor y deja los archivos Compiscript*.py listos en program/.
> Si se cambia la gramática `.g4`, se vuelve a correr make gen.

## Comandos principales (Makefile)

| Comando           | Qué hace |
|-------------------|----------|
| `make docker-build` | Construye la imagen Docker (`csp-image`) |
| `make gen`          | Genera Lexer/Parser/Visitor con ANTLR (Python3) |
| `make run`          | Ejecuta el compilador sobre `program/program.cps` |
| `make test`         | Corre todas las pruebas con `pytest` |
| `make test-scopes`  | Corre sólo `tests/semantic/test_scopes.py` |
| `make cov-scopes`   | Muestra cobertura centrada en `semantic/scopes.py` |
| `make shell`        | Abre una shell dentro del contenedor para depurar |
| `make clean`        | Elimina artefactos generados por ANTLR en `program/` |

> Los targets de test exportan automáticamente `PYTHONPATH=/workspace:/workspace/program` dentro del contenedor para que Python encuentre el paquete `program/semantic`. 

## Ejemplo de Ejecución

1. Asegúrate de haber corrido `make gen` .
2. Modificar el archivo `program/program.cps`:
   
    ```cps
    let a: integer = 10;
    let b: integer = 20;
    let c = a + b;
    ```
3. Ejecuta el driver:
   
    ```bash
    make run
    ```
    El Driver.py
   - Lee el archivo `program/program.cps`.
   - Construye el árbol usando ANTLR.
   - Invoca el TypeChecker (cuando esté completo) y reporta errores.
   - Puede imprimir una tabla de símbolos (según configuración/flags en `Driver.py` y `table.py`).

4. Salida esperada:
   
    Si no hay errores sintácticos/semánticos, no se imprime nada.  
    Si hay errores, se reportan en consola.

## Cómo funcionan los Tests?

Todos los tests están bajo `tests/semantic/`.
Se corre con `pytest` dentro del contenedor Docker.
- Correr todos los tests
  
  ```bash
  make test
  ```
- Correr solo los tests de scopes
  
  ```bash
  make test-scopes
  ```
- Revisar cobertura de scopes
  
  ```bash
  make cov-scopes
  ```

- Manual (dentro del contenedor)
  ```bash
  make shell
  export PYTHONPATH=/workspace:/workspace/program
  pytest -q
  ```

## Componentes semánticos (qué hace cada archivo)
`program/semantic/typesys.py`

- Tipos base: `INTEGER`, `STRING`, `BOOLEAN`, `NULL`, `VOID`.
- Tipos compuestos: `ArrayType`, `FunctionType`.
- Compatibilidad:
  - `can_assign(dst, src)` — asignación (ej. NULL a referencias).
  - `arithmetic_type(a, op, b)` — + - * / sólo numéricos, coerciones si aplica.
  - `logical_type(a, op, b)` — `&& || !` sólo booleanos.
  - `comparison_type(a, op, b)` — reglas para `== != < <= > >=`.
- Helpers: `make_array(elem, dims)`, `make_fn(params, ret)`.

`program/semantic/symbols.py`

- Symbol: base (nombre, tipo, clase).
- VarSymbol: variables/const; flags `is_const`, `is_initialized`.
- ParamSymbol: parámetros de función; posición `index`.
- FuncSymbol: firma `FunctionType`, lista de `ParamSymbol`, opcional `closure_scope`.
- ClassSymbol: campos (`fields`) y métodos (`methods`), herencia (`base`).

`program/semantic/scopes.py`

- Scope (base):
  - `define(sym) -> bool`: prohíbe redeclaración en el mismo scope.
  - `resolve(name) -> Symbol|None`: búsqueda en cascada (hijo → padres).
  - Rule: shadowing permitido en scopes internos.
- Subclases:
  - `GlobalScope`, `BlockScope`, `FunctionScope(return_type, name)`, `ClassScope(class_name)`.
  - `FunctionScope.has_return` para validar retornos.
- ScopeStack:
  - `current`, `push(kind)`, `push_function`, `push_class`, `push_child(child)`, `pop(), depth()`.
  - Pensado para que el visitor abra/cierre ámbitos en `visitProgram`, `visitBlock`, `visitFunctionDecl`, `visitClassDecl`, bucles, etc.
 

`program/semantic/error_reporter.py`

- `SemanticError(code, msg, line, col)` y `ErrorReporter` con `report()`, `has_errors()`, iteración, etc.
- El visitor registra aquí los errores con códigos consistentes (útil para tests).

`program/semantic/type_checker.py`

- Visitor para el AST de ANTLR (`CompiscriptVisitor`).
- Hooks listos para usar `ScopeStack`: abrir/cerrar scopes en program, blocks, funciones, clases, bucles; marcar `has_return`; verificar contexto de `break/continue/return`.
- Reglas semánticas (sistema de tipos, asignaciones, llamadas, acceso a miembros, arreglos, control de flujo) consumiendo `typesys`, `symbols`, `scopes` y `error_reporter`.

`program/semantic/table.py`

- Impresión legible de la tabla de símbolos agrupada por scopes (útil para debugging y para demo).

`program/semantic/app.py`

- Mini IDE con Streamlit para probar código, ver errores y tabla.

## Lenguaje Compiscript 

- Tipos: `integer`, `string`, `boolean`, `null`, `void`, arreglos `T[]`, `T[][]`, funciones.
- Variables/const:
  
  ```bash
  let x: integer = 10;
  const PI: integer = 314; // debe inicializarse
  ```
- Expresiones: aritméticas/lógicas/comparaciones con verificación de tipos.
  ```bash
  let x = 5 + 3 * 2;
  let ok = !(x < 10 || x > 20);
  ```
- Funciones:
  
  ```bash
  function suma(a: integer, b: integer): integer {
  return a + b;
  }
  let r = suma(2, 3);
  ```
- Clases:

  ```bash
  class Animal {
  let nombre: string;
  function constructor(nombre: string) { this.nombre = nombre; }
  function hablar(): string { return this.nombre + " hace ruido."; }
  }
  class Perro : Animal { function hablar(): string { return this.nombre + " ladra."; } }
  let p: Perro = new Perro("Toby");
  ```
- Control de flujo: `if/else`, `while`, `do-while`, `for`, `foreach`, `switch`, `break/continue`, `return` (sólo en funciones).
- Arreglos: literales `[1,2,3]`, indexing `a[i]`, matrices `integer[][]`.
> La gramática está en `program/Compiscript.g4`. Genera el parser con `make gen`.

## IDE
Para lanzar el IDE (Streamlit):
```bash
docker run --rm -ti -p 8501:8501 \
  -v "$(pwd)":/workspace -w /workspace csp-image \
  bash -lc 'export PYTHONPATH=/workspace:/workspace/program && \
            streamlit run program/semantic/app.py --server.port=8501 --server.address=0.0.0.0'
```
Abrir en el navegador: `http://localhost:8501`.
