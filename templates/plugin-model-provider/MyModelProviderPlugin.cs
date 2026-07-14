using Sophon.Plugin.Abstractions;
using Sophon.Plugin.Abstractions.Grpc;
using Sophon.Plugin.Sdk;

/// <summary>
/// Example model provider plugin for Sophon.
/// Implements the LLM model provider gRPC methods to add a custom LLM backend.
///
/// To use this template:
/// 1. Rename the class and update the Manifest
/// 2. Implement the LLM API calls in CompletePrompt and StreamComplete
/// 3. Build and publish: dotnet publish -c Release
/// 4. Copy the publish output to ~/.sophon/skills/installed/my-model-provider/
/// </summary>
public sealed class MyModelProviderPlugin : PluginBase
{
    public override PluginManifest Manifest => new()
    {
        Name = "my-model-provider",
        Version = "1.0.0",
        Description = "A custom LLM model provider plugin for Sophon.",
        Author = "Your Name",
        PluginInterface = PluginInterfaceType.ModelProvider,
        ProviderType = "my-llm"
    };

    public override Task<PromptResponse> OnCompletePromptAsync(PromptRequest request, CancellationToken ct = default)
    {
        Logger.LogInformation("Completing prompt for model '{Model}' with {Count} messages.",
            request.ModelId, request.Messages.Count);

        // TODO: Call your LLM API here
        // Convert request.Messages to your API format
        // Return the completion response

        return Task.FromResult(new PromptResponse
        {
            Content = $"Hello from custom model provider! You sent {request.Messages.Count} messages.",
            ModelId = request.ModelId,
            Usage = new UsageInfoProto { InputTokens = 10, OutputTokens = 20 },
            FinishReason = "stop"
        });
    }

    public override async IAsyncEnumerable<PromptChunk> OnStreamCompleteAsync(
        PromptRequest request,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        Logger.LogInformation("Streaming completion for model '{Model}'.", request.ModelId);

        // TODO: Implement streaming from your LLM API
        // Yield PromptChunk objects as they arrive

        var words = new[] { "Hello ", "from ", "streaming ", "model ", "provider!" };
        foreach (var word in words)
        {
            if (ct.IsCancellationRequested) yield break;

            yield return new PromptChunk { Content = word, IsComplete = false };
            await Task.Delay(100, ct);
        }

        yield return new PromptChunk
        {
            Content = "",
            IsComplete = true,
            Usage = new UsageInfoProto { InputTokens = 10, OutputTokens = 5 },
            FinishReason = "stop"
        };
    }

    public override Task<CapabilitiesResponse> OnGetCapabilitiesAsync(CapabilitiesRequest request, CancellationToken ct = default)
    {
        return Task.FromResult(new CapabilitiesResponse
        {
            SupportsVision = false,
            SupportsFunctionCalling = true,
            SupportsStreaming = true,
            MaxContextTokens = 128000
        });
    }
}
