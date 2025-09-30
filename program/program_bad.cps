// Constante mal inicializada: integer ← string
const PI: integer = "no soy un número";

// Variable sin tipo explícito, pero asignación incorrecta
let saludo = 123;   // debería ser string si luego lo usamos como tal

// Variable usada sin declarar
resultado = 10;  // no existe resultado todavía

// Función con return mal tipado
function sumarTexto(a: integer, b: integer): integer {
  return "hola";  // error: string a integer
}

// Clase con asignación de tipo incorrecto
class Persona {
  let edad: integer;

  function constructor(edad: integer) {
    this.edad = "treinta"; // error: string a integer
  }

  function hablar(): string {
    return 123; // error: integer a string
  }
}

// Instancia de clase no definida
let x: Animal = new Animal(); // error: clase Animal no existe
