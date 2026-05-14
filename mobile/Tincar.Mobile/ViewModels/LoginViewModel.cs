using System.Windows.Input;
using Tincar.Mobile.Services;

namespace Tincar.Mobile.ViewModels;

public sealed class LoginViewModel : BaseViewModel
{
    private readonly ITincarApiClient _apiClient;
    private readonly IEnvironmentConfigService _environmentConfigService;

    private string _baseUrl = string.Empty;
    private string _email = string.Empty;
    private string _password = string.Empty;

    public LoginViewModel(ITincarApiClient apiClient, IEnvironmentConfigService environmentConfigService)
    {
        _apiClient = apiClient;
        _environmentConfigService = environmentConfigService;
        LoginCommand = new Command(async () => await LoginAsync(), () => !IsBusy);
        SaveBaseUrlCommand = new Command(async () => await SaveBaseUrlAsync(), () => !IsBusy);
    }

    public string EnvironmentName => _environmentConfigService.CurrentEnvironment;

    public string BaseUrl
    {
        get => _baseUrl;
        set => SetProperty(ref _baseUrl, value);
    }

    public string Email
    {
        get => _email;
        set => SetProperty(ref _email, value);
    }

    public string Password
    {
        get => _password;
        set => SetProperty(ref _password, value);
    }

    public ICommand LoginCommand { get; }
    public ICommand SaveBaseUrlCommand { get; }

    public async Task InitializeAsync()
    {
        BaseUrl = await _environmentConfigService.GetBaseUrlAsync();
        StatusMessage = "Configura URL y luego inicia sesión.";
    }

    private async Task SaveBaseUrlAsync()
    {
        if (string.IsNullOrWhiteSpace(BaseUrl))
        {
            StatusMessage = "La URL base no puede estar vacía.";
            return;
        }

        await _apiClient.SetBaseUrlAsync(BaseUrl);
        StatusMessage = "URL guardada.";
    }

    private async Task LoginAsync()
    {
        if (IsBusy)
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(Email) || string.IsNullOrWhiteSpace(Password))
        {
            StatusMessage = "Correo y contraseña son obligatorios.";
            return;
        }

        try
        {
            IsBusy = true;
            await SaveBaseUrlAsync();
            var authResult = await _apiClient.LoginAsync(Email.Trim(), Password);
            StatusMessage = authResult.Message;
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error de login: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }
}
