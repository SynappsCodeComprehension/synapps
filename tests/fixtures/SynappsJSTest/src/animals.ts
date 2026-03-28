export interface IAnimal {
  speak(): string;
  getName(): string;
}

export abstract class Animal implements IAnimal {
  protected _name: string;

  constructor(name: string) {
    this._name = name;
  }

  getName(): string {
    return this._name;
  }

  abstract speak(): string;
}

export class Dog extends Animal {
  constructor() {
    super("Dog");
  }

  speak(): string {
    return "Woof";
  }

  fetch(item: string): string {
    return `Fetching ${item}`;
  }
}

export class Cat extends Animal {
  constructor() {
    super("Cat");
  }

  speak(): string {
    return "Meow";
  }
}
