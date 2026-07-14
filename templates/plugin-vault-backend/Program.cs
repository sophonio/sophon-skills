using Sophon.Plugin.Sdk;

// Start the plugin gRPC server. The --port argument is passed by PluginHostService.
await PluginHostRunner.Run<MyVaultPlugin>(args);
