namespace SynappsTest.Endpoints;

public class TodoRequest
{
    public string Title { get; set; } = string.Empty;
}

public class TodoResponse
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
}

public class Req { }

public class Res { }

public class TodoEndpoint : Endpoint<TodoRequest, TodoResponse>
{
    public override void Configure()
    {
        Post("/api/todos");
    }

    public override async Task HandleAsync(TodoRequest req, CancellationToken ct)
    {
        await SendAsync(new TodoResponse { Id = 1, Title = req.Title }, cancellation: ct);
    }
}

public class HealthEndpoint : EndpointWithoutRequest
{
    public override void Configure()
    {
        Get("/api/health");
    }

    public override async Task HandleAsync(CancellationToken ct)
    {
        await SendOkAsync(ct);
    }
}

public class MultiEndpoint : Endpoint<Req, Res>
{
    public override void Configure()
    {
        Verbs(Http.POST, Http.PUT);
        Routes("/api/items", "/api/things");
    }

    public override async Task HandleAsync(Req req, CancellationToken ct)
    {
        await SendOkAsync(ct);
    }
}
