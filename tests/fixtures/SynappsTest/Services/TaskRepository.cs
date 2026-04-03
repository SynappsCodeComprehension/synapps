namespace SynappsTest.Services;

using SynappsTest.Models;

public class TaskRepository : IRepository<TaskItem>
{
    public Task<TaskItem?> GetByIdAsync(Guid id)
    {
        return Task.FromResult<TaskItem?>(new TaskItem { Id = id });
    }

    public Task<List<TaskItem>> ListAsync()
    {
        return Task.FromResult(new List<TaskItem>());
    }

    public Task AddAsync(TaskItem entity)
    {
        return Task.CompletedTask;
    }

    public Task DeleteAsync(Guid id)
    {
        return Task.CompletedTask;
    }
}
