using System.Text;
using Sophon.Plugin.Abstractions;
using Sophon.Plugin.Abstractions.Grpc;
using Sophon.Plugin.Sdk;

/// <summary>
/// Example document extractor plugin for Sophon.
/// Implements the document extraction gRPC methods to support custom file formats.
///
/// Real-world examples: CAD files, EPUB, proprietary document formats, OCR engines.
///
/// To use this template:
/// 1. Rename the class and update the Manifest (especially SupportedExtensions)
/// 2. Implement the extraction logic in OnExtractDocumentAsync
/// 3. Build and publish: dotnet publish -c Release
/// 4. Copy the publish output to ~/.sophon/skills/installed/my-doc-extractor/
/// </summary>
public sealed class MyDocumentExtractorPlugin : PluginBase
{
    public override PluginManifest Manifest => new()
    {
        Name = "my-document-extractor",
        Version = "1.0.0",
        Description = "A custom document extractor plugin for Sophon.",
        Author = "Your Name",
        PluginInterface = PluginInterfaceType.DocumentExtractor,
        SupportedExtensions = [".xyz", ".custom"]
    };

    public override Task<DocumentResponse> OnExtractDocumentAsync(DocumentRequest request, CancellationToken ct = default)
    {
        Logger.LogInformation("Extracting document: {FileName} ({Size} bytes)",
            request.FileName, request.FileContent.Length);

        try
        {
            // TODO: Implement your document extraction logic here
            // request.FileContent contains the raw file bytes
            // Return the extracted text, page count, and metadata

            // Demo: just decode as UTF-8 text
            var text = Encoding.UTF8.GetString(request.FileContent.ToByteArray());

            var response = new DocumentResponse
            {
                Success = true,
                Text = text,
                PageCount = 1
            };
            response.Metadata["format"] = Path.GetExtension(request.FileName);
            response.Metadata["extractedBy"] = Manifest.Name;

            return Task.FromResult(response);
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to extract document: {FileName}", request.FileName);
            return Task.FromResult(new DocumentResponse
            {
                Success = false,
                Error = ex.Message
            });
        }
    }
}
