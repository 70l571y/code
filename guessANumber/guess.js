//Правила игры:

// Компьютер загадывает 4-х значное число, цифры в числе могут повторяться,
// число может начинаться с 0 (00, 000, 0000). Задача игрока угадать это число.
// Если цифра присутствует в загаданном числе, и она стоит на том месте, то компьютер
// обозначает такую цифру буквой "В". Если цифра присутствует, но она стоит не на том
// месте, то компьютер обозначает ее буквой "K". Нужно угадать загаданное число за
// наименьшее число ходов.

var readline = require("readline");
const charOfTheDigit = 4;
const winningCombination = [];
const output = [];

const terminal = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const compareArrays = (ar1 = [], ar2 = []) =>
  ar1.length === ar2.length &&
  ar1.every((value, index) => value === ar2[index]);

const getHiddenNumber = chars => {
  const getRandomInt = (low, high) =>
    Math.floor(Math.random() * (high - low) + low);
  const getUpperLimit = () => +("1" + "0".repeat(chars));
  const numbers = [];
  const digit = getRandomInt(0, getUpperLimit()).toString();
  const offset = chars - digit.length;

  for (let i = 0; i < digit.length; i++) {
    numbers[i] = digit[i];
  }

  for (const i = 0; i < offset; i++) {
    numbers.unshift("0");
  }
  return numbers;
};

const hiddenNumber = getHiddenNumber(charOfTheDigit);

terminal.setPrompt("Guess a number: " + "*".repeat(charOfTheDigit) + "\n");
terminal.prompt();

terminal.on("line", answer => {
  if (charOfTheDigit >= answer.length && !isNaN(+answer)) {
    for (let i = 0; i < charOfTheDigit; i++) {
      winningCombination[i] = "B";

      if (typeof answer[i] == "undefined") answer += "*"; //Если ответ короче загаданного числа

      if (
        hiddenNumber.indexOf(answer[i], i) === i &&
        hiddenNumber.includes(answer[i], i)
      ) {
        output[i] = "B";
        continue;
      } else if (hiddenNumber.includes(answer[i])) {
        output[i] = "K";
        continue;
      } else output[i] = answer[i];
    }
    console.log(output);

    if (compareArrays(output, winningCombination)) {
      console.log("YOU WINNER!!!");
      process.exit(1);
    }
  } else console.log("The number must be " + charOfTheDigit + " digits!!!");
});

terminal.on("close", function() {
  console.log("YOU LOSE!!! Ha Ha Ha Ha!!!");
  process.exit(1);
});

module.exports = {
  compareArrays: compareArrays,
  getHiddenNumber: getHiddenNumber
};
