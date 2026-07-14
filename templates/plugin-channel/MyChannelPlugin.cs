using Sophon.Plugin.Abstractions;
using Sophon.Plugin.Abstractions.Grpc;
using Sophon.Plugin.Sdk;

/// <summary>
/// Example channel adapter plugin for Sophon.
/// Implements the channel adapter gRPC methods to bridge a custom messaging platform.
///
/// To use this template:
/// 1. Rename the class and update the Manifest
/// 2. Implement the channel-specific logic in each method
/// 3. Build and publish: dotnet publish -c Release
/// 4. Copy the publish output to ~/.sophon/skills/installed/my-channel-plugin/
/// </summary>
public sealed class MyChannelPlugin : PluginBase
{
    private bool _connected;

    public override PluginManifest Manifest => new()
    {
        Name = "my-channel-plugin",
        Version = "1.0.0",
        Description = "A custom channel adapter plugin for Sophon.",
        Author = "Your Name",
        PluginInterface = PluginInterfaceType.ChannelAdapter,
        ChannelType = "my-channel",
        RecipientMetadataKey = "chatId"
    };

    public override Task<InitializeResponse> OnInitializeAsync(InitializeRequest request, CancellationToken ct = default)
    {
        Logger.LogInformation("MyChannelPlugin initializing with config: {Config}",
            string.Join(", ", request.Configuration.Select(kv => $"{kv.Key}={kv.Value}")));

        return base.OnInitializeAsync(request, ct);
    }

    public override Task<ConnectChannelResponse> OnConnectChannelAsync(ConnectChannelRequest request, CancellationToken ct = default)
    {
        Logger.LogInformation("Connecting to channel with config ID: {Id}", request.ConfigId);

        // TODO: Connect to your messaging platform here
        // Use request.Settings to get credentials/configuration
        _connected = true;

        return Task.FromResult(new ConnectChannelResponse { Success = true });
    }

    public override Task<DisconnectChannelResponse> OnDisconnectChannelAsync(DisconnectChannelRequest request, CancellationToken ct = default)
    {
        Logger.LogInformation("Disconnecting from channel.");
        _connected = false;
        return Task.FromResult(new DisconnectChannelResponse { Success = true });
    }

    public override Task<SendChannelMessageResponse> OnSendChannelMessageAsync(SendChannelMessageRequest request, CancellationToken ct = default)
    {
        var msg = request.Message;
        Logger.LogInformation("Sending message to {Recipient}: {Text}", msg.SenderId, msg.Content.Text);

        // TODO: Send the message via your messaging platform
        // Use msg.Content.Type to determine message type (text, image, file, etc.)
        // Use msg.Metadata to get recipient-specific info

        return Task.FromResult(new SendChannelMessageResponse { Success = true });
    }

    public override Task<ChannelMessageResponse> OnHandleChannelMessageAsync(ChannelMessageRequest request, CancellationToken ct = default)
    {
        var msg = request.Message;
        Logger.LogInformation("Received message from {Sender}: {Text}", msg.SenderId, msg.Content.Text);

        // TODO: Process the inbound message
        // Return a reply if needed, or just acknowledge

        return Task.FromResult(new ChannelMessageResponse { Success = true });
    }

    public override Task<TestChannelConnectionResponse> OnTestChannelConnectionAsync(TestChannelConnectionRequest request, CancellationToken ct = default)
    {
        // TODO: Verify the connection is working
        return Task.FromResult(new TestChannelConnectionResponse
        {
            Success = _connected,
            Error = _connected ? "" : "Not connected"
        });
    }

    public override Task<GetChannelHealthResponse> OnGetChannelHealthAsync(GetChannelHealthRequest request, CancellationToken ct = default)
    {
        return Task.FromResult(new GetChannelHealthResponse
        {
            Status = _connected ? 0 : 1 // 0 = Connected, 1 = Disconnected
        });
    }
}
