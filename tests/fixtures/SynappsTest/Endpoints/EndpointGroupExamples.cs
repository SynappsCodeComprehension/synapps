namespace SynappsTest.Endpoints;

using Microsoft.AspNetCore.Routing;

public class TodoItems : IEndpointGroup
{
    public void Map(RouteGroupBuilder app)
    {
        app.MapGet("/", GetAllTodos);
        app.MapPost("/", CreateTodo);
    }

    public static IResult GetAllTodos()
    {
        return Results.Ok(new[] { "todo1", "todo2" });
    }

    public static IResult CreateTodo()
    {
        return Results.Created("/", null);
    }
}

public class ItemGroup : EndpointGroupBase
{
    public void Map(RouteGroupBuilder app)
    {
        app.MapDelete("/items/{id}", DeleteItem);
    }

    public static IResult DeleteItem()
    {
        return Results.NoContent();
    }
}
