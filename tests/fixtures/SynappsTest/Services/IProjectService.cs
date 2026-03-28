namespace SynappsTest.Services;

using SynappsTest.Models;

public interface IProjectService
{
    Task<Project> GetProjectAsync(Guid id);
    Task ValidateProjectAsync(Guid id);
}
