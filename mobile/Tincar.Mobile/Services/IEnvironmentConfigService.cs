namespace Tincar.Mobile.Services;

public interface IEnvironmentConfigService
{
    Task<string> GetBaseUrlAsync();
    Task SetBaseUrlAsync(string baseUrl);
    string CurrentEnvironment { get; }
}
