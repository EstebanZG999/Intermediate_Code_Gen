# Especificación TAC – Núcleo (Persona A)

## Operandos
- `Const(k)`, `Var(name)`, `Temp(tk)`, `Addr(base, offset)`, `Label(Li)`

## Instrucciones
- Asignación: `dst := a`
- Aritmética: `+ - * / %`
- Relacionales: `< <= > >= == !=` → 0/1
- Control: `label Lx:`, `goto Lx`, `if cond goto Lx`
- Llamadas: `param`, `call f, nargs -> t`, `ret v` (definido por C)
- E/S: `print a`

## Convenciones
- Booleanos: 0/1; short-circuit con `ifgoto/goto/label`; reciclaje LIFO de temporales.