var readline = require('readline');
const charOfTheDigit = 4;
const winningCombination = [];
let output = [];
const diff = (ar1, ar2) => ar1.length === ar2.length && ar1.every((value, index) => value === ar2[index])

const terminal = readline.createInterface(
{
  input : process.stdin,
  output : process.stdout
});


const getRandomInt = (low, high) => Math.floor(Math.random() * (high - low) + low)

const getHiddenNumber = () => {
  const numbers = new Array();
  digit = getRandomInt(0, 10000).toString();
  offset = charOfTheDigit - digit.length

  for (let i = 0; i < digit.length; i++) {
    numbers[i] = digit[i];
  }
  for (const i = 0; i < offset; i++) {
    numbers.unshift("0")
  }

  return numbers;
}

const hiddenNumber = getHiddenNumber();

terminal.setPrompt('Guess a number: ' + "*".repeat(charOfTheDigit) + "\n");
terminal.prompt();
terminal.on('line', (answer) => {
  if ((charOfTheDigit >= answer.length) && !isNaN(+answer)) {
    for (let i = 0; i < charOfTheDigit; i++) {
      winningCombination[i] = "B";
      if (typeof answer[i] == 'undefined') answer += "*";

      if ((hiddenNumber.indexOf(answer[i], i) === i) && (hiddenNumber.includes(answer[i], i))) {
        output[i] = "B";
        continue;
      } else if (hiddenNumber.includes(answer[i])) {
        output[i] = "K";
        continue;
      } else output[i] = answer[i];
    }
    console.log(output);
  if (diff(output, winningCombination)){
    console.log("YOU WINNER");
    process.exit(1);
  }
  } else {

  console.log("The number must be " + charOfTheDigit + " digits!!!");
}
})

terminal.on('close', function()
{
  console.log('YOU LOSE!!! Ha Ha Ha Ha!!!')
  process.exit(1);
});
