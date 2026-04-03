namespace SynappsTest.Services;

using SynappsTest.Models;

public interface IRepository<T> where T : BaseEntity
{
    Task<T?> GetByIdAsync(Guid id);
    Task<List<T>> ListAsync();
    Task AddAsync(T entity);
    Task DeleteAsync(Guid id);
}
