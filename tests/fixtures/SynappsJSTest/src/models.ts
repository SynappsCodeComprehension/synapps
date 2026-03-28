export class BaseModel {
  id: number = 0;
  createdAt: Date = new Date();
}

export class TaskModel extends BaseModel {
  title: string = "";
  completed: boolean = false;
}
