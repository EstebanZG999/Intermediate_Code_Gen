// Constantes y variables
const PI: integer = 314;
let saludo: string = "Hola mundo!";
let activo: boolean = true;
let numeros: integer[] = [1, 2, 3, 4, 5];

// Función que multiplica dos enteros
function multiplicar(a: integer, b: integer): integer {
  return a * b;
}

let resultado: integer = multiplicar(6, 7);
print("El resultado es: " + resultado);

// Control de flujo simple
if (resultado > 10) {
  print("Mayor que 10");
} else {
  print("Menor o igual a 10");
}

// Clase sencilla
class Persona {
  let nombre: string;

  function constructor(nombre: string) {
    this.nombre = nombre;
  }

  function saludar(): string {
    return "Hola, soy " + this.nombre;
  }
}

// Crear instancia y usar método
let p: Persona = new Persona("Carlos");
print(p.saludar());
