namespace SynappsTest.Endpoints;

using Microsoft.AspNetCore.Builder;

public static class MinimalApiEndpoints
{
    public static void MapEndpoints(WebApplication app)
    {
        app.MapGet("/minimal/items", GetAllItems);
        app.MapPost("/minimal/items", async (ctx) => { });
        app.MapDelete("/minimal/items/{id}", DeleteItem);
    }

    public static IResult GetAllItems()
    {
        return Results.Ok(new[] { "item1", "item2" });
    }

    public static IResult DeleteItem()
    {
        return Results.NoContent();
    }
}
