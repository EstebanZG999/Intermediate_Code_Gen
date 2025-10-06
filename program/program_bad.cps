// =========================
//  Pruebas de Acciones Semánticas TAC
// =========================

// --- Variables y constantes ---
let x = 5;
var y = 10;
const z = 3;

// --- Expresiones aritméticas ---
x = x + y * z - (y / 2);

// --- Expresiones lógicas y ternario ---
let cond = (x > 10) && (y < 20) || false;
let t = cond ? 100 : 0;
print(t);

// --- Ciclo while ---
while (x < 15) {
  print(x);
  x = x + 1;
}

// --- Ciclo do-while ---
do {
  print(x);
  x = x - 1;
} while (x > 10);

// --- Ciclo for ---
for (let i = 0; i < 5; i = i + 1) {
  if (i == 2) continue;
  if (i == 4) break;
  print(i);
}

// --- Arreglos y acceso ---
let nums = [1, 2, 3, 4];
nums[2] = 99;
print(nums[2]);

// --- Switch con default ---
switch (x) {
  case 8:
    print("case 8");
    break;
  case 10:
    print("case 10");
    break;
  default:
    print("default");
}

// --- Función simple ---
function suma(a, b) {
  let r = a + b;
  return r;
}

print(suma(3, 4));

// --- Clase con campo y método ---
class Persona {
  var nombre;
  function saludar() {
    print("Hola, soy " + this.nombre);
  }
}

let p = new Persona();
p.nombre = "Oscar";
p.saludar();

// --- Fin del programa ---
print("Fin de pruebas TAC");
