// === Variables globales ===
const PI: integer = 314;
let mensaje: string = "Hola Mundo";

// === Función simple ===
function cuadrado(x: integer): integer {
  return x * x;
}

// === Función anidada ===
function externo(a: integer): integer {
  function interno(b: integer): integer {
    return a + b;
  }
  return interno(5);
}

// === Clase con campos y método ===
class Persona {
  let nombre: string;
  let edad: integer;

  function constructor(n: string, e: integer): void {
    this.nombre = n;
    this.edad = e;
  }

  function saludar(): void {
    print("Hola, soy " + this.nombre);
  }
}

// === Arreglos y bucles ===
function promedio(valores: integer[]): integer {
  let suma: integer = 0;
  for (let i: integer = 0; i < 3; i = i + 1) {
    suma = suma + valores[i];
  }
  return suma / 3;
}

// === Programa principal ===
let resultado: integer = externo(10);
print("Resultado externo: " + resultado);

let p: Persona = new Persona("Oscar", 25);
p.saludar();

let nums: integer[] = [10, 20, 30];
print("Promedio: " + promedio(nums));
