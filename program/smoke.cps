// Param + local
function inc(x: integer): integer {
  let y: integer = x + 1;
  return y;
}

// Clase con this
class Box {
  let v: integer;

  function constructor(a: integer): void {
    this.v = a;
  }

  function get(): integer {
    return this.v;
  }
}

// Arreglo + for
function headPlus(arr: integer[]): integer {
  let i: integer = 0;
  let z: integer = arr[i] + 5;
  return z;
}

// main “manual” en el toplevel:
const C: integer = 7;
let r1: integer = inc(10);
let b: Box = new Box(C);
let r2: integer = b.get();
let xs: integer[] = [1,2,3];
let r3: integer = headPlus(xs);
print("r1=" + r1);
print("r2=" + r2);
print("r3=" + r3);
