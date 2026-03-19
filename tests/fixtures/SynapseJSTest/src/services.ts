import { IAnimal } from './animals';

export class AnimalService {
  private _animal: IAnimal;

  constructor(animal: IAnimal) {
    this._animal = animal;
  }

  getGreeting(): string {
    return `${this._animal.getName()} says ${this._animal.speak()}`;
  }

  static version(): string {
    return "1.0.0";
  }

  async getGreetingAsync(): Promise<string> {
    return this.getGreeting();
  }
}

export class Greeter {
  private _service: AnimalService;

  constructor(service: AnimalService) {
    this._service = service;
  }

  greet(): string {
    return `Hello! ${this._service.getGreeting()}`;
  }
}
