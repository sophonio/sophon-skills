using System.Collections.Concurrent;
using Sophon.Plugin.Abstractions;
using Sophon.Plugin.Abstractions.Grpc;
using Sophon.Plugin.Sdk;

/// <summary>
/// Example vault backend plugin for Sophon.
/// Implements the credential vault gRPC methods to integrate a custom secret store.
///
/// Real-world examples: CyberArk, 1Password Connect, custom HSM, Bitwarden.
///
/// To use this template:
/// 1. Rename the class and update the Manifest
/// 2. Implement the vault operations to call your secret store API
/// 3. Build and publish: dotnet publish -c Release
/// 4. Copy the publish output to ~/.sophon/skills/installed/my-vault-plugin/
/// </summary>
public sealed class MyVaultPlugin : PluginBase
{
    // In-memory store for demo purposes. Replace with your vault API client.
    private readonly ConcurrentDictionary<string, string> _store = new();

    public override PluginManifest Manifest => new()
    {
        Name = "my-vault-plugin",
        Version = "1.0.0",
        Description = "A custom vault backend plugin for Sophon.",
        Author = "Your Name",
        PluginInterface = PluginInterfaceType.VaultBackend
    };

    public override Task<VaultGetResponse> OnGetVaultValueAsync(VaultGetRequest request, CancellationToken ct = default)
    {
        Logger.LogDebug("Getting vault value for key: {Key}", request.Key);

        // TODO: Call your vault API to retrieve the secret
        if (_store.TryGetValue(request.Key, out var value))
        {
            return Task.FromResult(new VaultGetResponse { Found = true, Value = value });
        }

        return Task.FromResult(new VaultGetResponse { Found = false });
    }

    public override Task<VaultSetResponse> OnSetVaultValueAsync(VaultSetRequest request, CancellationToken ct = default)
    {
        Logger.LogDebug("Setting vault value for key: {Key}", request.Key);

        // TODO: Call your vault API to store the secret
        _store[request.Key] = request.Value;

        return Task.FromResult(new VaultSetResponse { Success = true });
    }

    public override Task<VaultDeleteResponse> OnDeleteVaultValueAsync(VaultDeleteRequest request, CancellationToken ct = default)
    {
        Logger.LogDebug("Deleting vault value for key: {Key}", request.Key);

        // TODO: Call your vault API to delete the secret
        var deleted = _store.TryRemove(request.Key, out _);

        return Task.FromResult(new VaultDeleteResponse { Deleted = deleted });
    }

    public override Task<VaultListResponse> OnListVaultKeysAsync(VaultListRequest request, CancellationToken ct = default)
    {
        Logger.LogDebug("Listing vault keys with prefix: {Prefix}", request.Prefix);

        // TODO: Call your vault API to list keys
        var keys = _store.Keys
            .Where(k => string.IsNullOrEmpty(request.Prefix) || k.StartsWith(request.Prefix))
            .ToList();

        var response = new VaultListResponse();
        response.Keys.AddRange(keys);
        return Task.FromResult(response);
    }
}
