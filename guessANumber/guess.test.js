const mocha = require("mocha");
const chai = require("chai");

const { compareArrays, getHiddenNumber } = require("./guess");

const expect = chai.expect;

describe("Comparing two arrays", () => {
  let arrayFirst = ["1", "3", "5", "7"];
  let arraySecond = ["2", "3", "5", "7"];
  let arrayThird = ["1", "3", "5", "7"];

  it("Check for identical arrays", () => {
    const resultFirst = compareArrays(arrayFirst, arrayThird);
    expect(resultFirst).to.equal(true);
  });
  it("Check different arrays", () => {
    const resultSecond = compareArrays(arrayFirst, arraySecond);
    expect(resultSecond).to.equal(false);
  });
});

describe("Check the hidden number", () => {
  it("Check the number of characters", () => {
    const charOfTheDigit = 4;
    const hiddenNumber = getHiddenNumber(charOfTheDigit);
    expect(hiddenNumber.length).to.equal(charOfTheDigit);
  });
});
