using System.Text.Json;

namespace Tincar.Mobile.Services;

public sealed class EnvironmentConfigService : IEnvironmentConfigService
{
    private const string BaseUrlPreferenceKey = "tincar.api.baseurl";
    private string? _cachedBaseUrl;

    public string CurrentEnvironment
    {
        get
        {
#if DEBUG
            return "Development";
#else
            return "Production";
#endif
        }
    }

    public async Task<string> GetBaseUrlAsync()
    {
        if (!string.IsNullOrWhiteSpace(_cachedBaseUrl))
        {
            return _cachedBaseUrl;
        }

        var fromPrefs = Preferences.Get(BaseUrlPreferenceKey, string.Empty);
        if (!string.IsNullOrWhiteSpace(fromPrefs))
        {
            _cachedBaseUrl = NormalizeBaseUrl(fromPrefs);
            return _cachedBaseUrl;
        }

        var fromFile = await ReadBaseUrlFromEnvironmentFileAsync();
        _cachedBaseUrl = NormalizeBaseUrl(fromFile);
        return _cachedBaseUrl;
    }

    public Task SetBaseUrlAsync(string baseUrl)
    {
        _cachedBaseUrl = NormalizeBaseUrl(baseUrl);
        Preferences.Set(BaseUrlPreferenceKey, _cachedBaseUrl);
        return Task.CompletedTask;
    }

    private async Task<string> ReadBaseUrlFromEnvironmentFileAsync()
    {
        var fileName = CurrentEnvironment == "Development"
            ? "appsettings.Development.json"
            : "appsettings.Production.json";

        using var stream = await FileSystem.OpenAppPackageFileAsync(fileName);
        using var reader = new StreamReader(stream);
        var json = await reader.ReadToEndAsync();

        using var document = JsonDocument.Parse(json);
        if (document.RootElement.TryGetProperty("Api", out var api) &&
            api.TryGetProperty("BaseUrl", out var baseUrlElement))
        {
            return baseUrlElement.GetString() ?? "http://10.0.2.2:5000";
        }

        return "http://10.0.2.2:5000";
    }

    private static string NormalizeBaseUrl(string baseUrl)
    {
        var url = baseUrl.Trim();
        if (!url.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
            !url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            url = $"http://{url}";
        }

        return url.TrimEnd('/');
    }
}
