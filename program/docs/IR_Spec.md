

# Especificación del Lenguaje Intermedio (TAC)


---

## 1. Introducción

El **Lenguaje Intermedio (TAC)** sirve como representación intermedia entre el **árbol sintáctico** generado por el parser y el **código objeto o ensamblador**.
Este diseño busca un equilibrio entre **legibilidad, portabilidad y facilidad de optimización**.
Cada instrucción TAC contiene **a lo sumo tres operandos**: dos fuentes y un destino.

---

## 2. Tipos de Operandos

| Tipo                 | Descripción                                                  | Ejemplo                     |
| -------------------- | ------------------------------------------------------------ | --------------------------- |
| `Const(k)`           | Constante literal (entero, cadena o nulo)                    | `Const(3)`, `Const("Hola")` |
| `Var(name)`          | Variable declarada (global, local o parámetro)               | `Var("x")`                  |
| `Temp(tk)`           | Variable temporal generada automáticamente por el compilador | `Temp("t2")`                |
| `Addr(base, offset)` | Dirección simbólica relativa al registro de activación       | `Addr("fp", -2)`            |
| `Label(Li)`          | Etiqueta de control de flujo                                 | `Label("Lfor_cond0")`       |

---

## 3. Instrucciones del TAC

### 3.1 Asignación y Expresiones

| Forma              | Significado                                                                     |
| ------------------ | ------------------------------------------------------------------------------- |
| `dst := src`       | Asigna el valor `src` a `dst`.                                                  |
| `dst := op1 + op2` | Suma aritmética. Similar para `- * / %`.                                        |
| `dst := op1 < op2` | Devuelve 1 si es verdadero, 0 si es falso. Incluye `<=`, `>`, `>=`, `==`, `!=`. |

**Ejemplo:**

```
t0 := 3
t1 := 4
t2 := t0 + t1
x := t2
```

---

### 3.2 Control de Flujo

| Forma             | Descripción                                      |
| ----------------- | ------------------------------------------------ |
| `label Lx:`       | Define un punto de salto.                        |
| `goto Lx`         | Salta incondicionalmente a la etiqueta `Lx`.     |
| `if cond goto Lx` | Salta a `Lx` si la condición es verdadera (≠ 0). |

**Ejemplo (while loop):**

```
Lwhile_cond0:
< i, 10 -> t0
if t0 goto Lwhile_body1
goto Lwhile_end2
Lwhile_body1:
print i
+ i, 1 -> t1
i := t1
goto Lwhile_cond0
Lwhile_end2:
```

---

### 3.3 Funciones y Llamadas

| Instrucción          | Descripción                                                |
| -------------------- | ---------------------------------------------------------- |
| `func_name_entry:`   | Marca inicio de función.                                   |
| `func_name_end:`     | Marca fin de función.                                      |
| `param a`            | Pasa argumento `a` al stack de llamada.                    |
| `call f, nargs -> t` | Llama a `f` con `nargs` argumentos, guarda retorno en `t`. |
| `ret v`              | Devuelve `v` desde la función actual.                      |

**Ejemplo:**

```
func_cuadrado_entry:
* x, x -> t0
ret t0
func_cuadrado_end:

param 5
call "cuadrado", nargs=1 -> t1
print t1
```

---

### 3.4 Clases y Objetos

| Instrucción                         | Descripción                                           |
| ----------------------------------- | ----------------------------------------------------- |
| `alloc "Clase", None -> t0`         | Reserva espacio para un objeto de tipo `Clase`.       |
| `call "Clase.constructor", nargs=N` | Llama al constructor pasando `this` y los parámetros. |
| `param this`                        | Inserta el puntero `this` como primer argumento.      |
| `call "obj.metodo", nargs=N -> tK`  | Llama a un método sobre una instancia.                |

**Ejemplo:**

```
alloc "Persona", None -> t0
param t0
param "Oscar"
param 25
call "Persona.constructor", nargs=3 -> None
p := t0
param p
call "Persona.saludar", nargs=1 -> t1
```

---

### 3.5 Arreglos

| Instrucción                 | Descripción                                     |
| --------------------------- | ----------------------------------------------- |
| `alloc_array n, None -> t0` | Crea un arreglo de tamaño `n`.                  |
| `addr_index arr, i -> t1`   | Calcula dirección del elemento `i` del arreglo. |
| `load t1, None -> t2`       | Carga el valor en `t1`.                         |
| `store t1, t2`              | Escribe `t2` en la dirección `t1`.              |

**Ejemplo:**

```
alloc_array 3, None -> t0
t1 := 0
addr_index t0, t1 -> t2
store t2, 5
```

---

### 3.6 Entrada / Salida

| Instrucción | Descripción              |
| ----------- | ------------------------ |
| `print a`   | Imprime el valor de `a`. |

**Ejemplo:**

```
+ "Resultado: ", x -> t0
print t0
```

---

## 4. Convenciones Semánticas

### 4.1 Booleanos

* Representados como `0` (falso) y `1` (verdadero).
* Los operadores lógicos (`&&`, `||`, `!`) se implementan mediante `ifgoto/goto/label` (short-circuit).

### 4.2 Temporales

* Asignación secuencial (`t0`, `t1`, …) con **asignador LIFO**.
* (Opcional: soporte para reciclaje mediante `free(tN)` cuando un temporal deja de usarse).

### 4.3 Memoria

* Variables globales: nombres directos (`PI`, `mensaje`).
* Locales y parámetros: direccionados por **offsets** en un `ActivationRecord`.

  * `this`: offset +1
  * parámetros: positivos (+2, +3, …)
  * locales: negativos (-1, -2, …)

---

## 5. Ejemplo Completo (Simplificado)

### Código Fuente:

```c
function suma(a: integer, b: integer): integer {
  let c: integer = a + b;
  return c;
}
print("Resultado: " + suma(3, 4));
```

### TAC Generado:

```
func_suma_entry:
+ a, b -> t0
c := t0
ret c
func_suma_end:
t1 := 3
t2 := 4
param t1
param t2
call "suma", nargs=2 -> t3
+ "Resultado: ", t3 -> t4
print t4
```

---

## 6. Supuestos de Traducción

1. **Evaluación estricta**: los argumentos y subexpresiones se evalúan antes de usarse.
2. **Cada función** tiene su propio registro de activación, con offsets únicos.
3. **El retorno** se maneja con una instrucción `ret` única por bloque.
4. **Strings** son inmutables y tratados como constantes en TAC.
5. **No se modela el heap real**; `alloc` y `alloc_array` son operaciones simbólicas.

---



